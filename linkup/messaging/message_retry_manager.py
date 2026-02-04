"""
Message Retry Manager for WhatsApp-like Messaging System

Handles HTTP fallback for failed WebSocket messages, exponential backoff retry logic,
retry queue processing on connectivity restoration, and comprehensive error handling.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Q, F
from channels.layers import get_channel_layer
import uuid

User = get_user_model()
logger = logging.getLogger(__name__)


class RetryStrategy:
    """Defines retry strategy constants and calculations."""
    
    # Retry limits
    MAX_WEBSOCKET_RETRIES = 3
    MAX_HTTP_RETRIES = 3
    MAX_TOTAL_RETRIES = 5
    
    # Timing constants
    INITIAL_RETRY_DELAY = 2  # seconds
    MAX_RETRY_DELAY = 300    # 5 minutes
    BACKOFF_MULTIPLIER = 2.0
    
    # Circuit breaker settings
    CIRCUIT_BREAKER_THRESHOLD = 10  # failures before opening circuit
    CIRCUIT_BREAKER_TIMEOUT = 60    # seconds before trying again
    
    @staticmethod
    def calculate_retry_delay(attempt_count: int) -> int:
        """Calculate exponential backoff delay."""
        delay = RetryStrategy.INITIAL_RETRY_DELAY * (RetryStrategy.BACKOFF_MULTIPLIER ** attempt_count)
        return min(delay, RetryStrategy.MAX_RETRY_DELAY)


class MessageRetryManager:
    """
    Manages message retry logic with HTTP fallback and exponential backoff.
    
    Features:
    - HTTP fallback for failed WebSocket messages
    - Exponential backoff retry logic with 3-attempt limit
    - Retry queue processing on connectivity restoration
    - Circuit breaker patterns for high load
    - Comprehensive error tracking and recovery
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.circuit_breaker_state = {}  # Track circuit breaker per endpoint
        self.retry_queue = {}  # In-memory retry queue for immediate retries
        self.batch_size = 20  # Messages to process per batch
    
    async def retry_failed_message(self, message_id: int, error_type: str = 'websocket_failed') -> bool:
        """
        Retry a failed message with exponential backoff.
        
        Args:
            message_id: ID of the message to retry
            error_type: Type of error that caused the retry
            
        Returns:
            bool: True if retry was successful, False otherwise
        """
        try:
            from .models import Message, QueuedMessage
            
            # Get the message
            message = await Message.objects.select_related('sender', 'recipient').aget(id=message_id)
            
            # Check if we've exceeded retry limits
            if message.retry_count >= RetryStrategy.MAX_TOTAL_RETRIES:
                logger.warning(f"Message {message_id} exceeded max retries ({message.retry_count})")
                await self._mark_message_failed(message, "Max retries exceeded")
                return False
            
            # Calculate retry delay
            retry_delay = RetryStrategy.calculate_retry_delay(message.retry_count)
            
            # Check circuit breaker
            endpoint_key = f"{message.sender_id}_{message.recipient_id}"
            if self._is_circuit_breaker_open(endpoint_key):
                logger.info(f"Circuit breaker open for {endpoint_key}, queuing message {message_id}")
                await self._queue_message_for_retry(message, retry_delay)
                return False
            
            # Increment retry count
            message.retry_count = F('retry_count') + 1
            message.last_error = f"{error_type} - attempt {message.retry_count + 1}"
            await message.asave(update_fields=['retry_count', 'last_error'])
            
            # Try WebSocket first, then HTTP fallback
            success = False
            
            if message.retry_count <= RetryStrategy.MAX_WEBSOCKET_RETRIES:
                success = await self._retry_via_websocket(message)
            
            if not success:
                success = await self._retry_via_http(message)
            
            if success:
                await self._mark_message_sent(message)
                self._reset_circuit_breaker(endpoint_key)
                logger.info(f"Message {message_id} retry successful")
                return True
            else:
                await self._handle_retry_failure(message, endpoint_key)
                return False
                
        except Exception as e:
            logger.error(f"Error retrying message {message_id}: {str(e)}")
            return False
    
    async def _retry_via_websocket(self, message) -> bool:
        """Attempt to retry message via WebSocket."""
        try:
            # Create room name for the conversation
            room_name = f"chat_{min(message.sender_id, message.recipient_id)}_{max(message.sender_id, message.recipient_id)}"
            
            # Prepare message data
            message_data = {
                'type': 'chat_message',
                'message_id': message.id,
                'message': message.content,
                'sender_id': message.sender_id,
                'sender_username': message.sender.username,
                'timestamp': message.created_at.isoformat(),
                'status': 'sent',
                'client_id': message.client_id or str(uuid.uuid4()),
                'is_retry': True
            }
            
            # Send via channel layer
            await self.channel_layer.group_send(room_name, message_data)
            
            logger.info(f"Message {message.id} retried via WebSocket")
            return True
            
        except Exception as e:
            logger.warning(f"WebSocket retry failed for message {message.id}: {str(e)}")
            return False
    
    async def _retry_via_http(self, message) -> bool:
        """Attempt to retry message via HTTP fallback."""
        try:
            from django.urls import reverse
            from django.test import AsyncClient
            
            # Use Django's async client for HTTP fallback
            client = AsyncClient()
            
            # Prepare POST data
            post_data = {
                'content': message.content,
                'recipient_id': message.recipient_id,
                'client_id': message.client_id or str(uuid.uuid4()),
                'is_retry': True,
                'original_message_id': message.id
            }
            
            # Make HTTP request to send message endpoint
            response = await client.post('/messaging/send/', post_data)
            
            if response.status_code == 200:
                logger.info(f"Message {message.id} retried via HTTP")
                return True
            else:
                logger.warning(f"HTTP retry failed for message {message.id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"HTTP retry failed for message {message.id}: {str(e)}")
            return False
    
    async def _mark_message_sent(self, message):
        """Mark message as successfully sent."""
        from .message_status_manager import MessageStatusManager
        
        status_manager = MessageStatusManager()
        await status_manager.mark_as_sent(message.id)
        
        # Clear any error state
        message.last_error = None
        await message.asave(update_fields=['last_error'])
    
    async def _mark_message_failed(self, message, error_reason: str):
        """Mark message as permanently failed."""
        from .message_status_manager import MessageStatusManager
        
        status_manager = MessageStatusManager()
        await status_manager.mark_as_failed(message.id, error_reason)
        
        message.last_error = error_reason
        await message.asave(update_fields=['last_error'])
    
    async def _queue_message_for_retry(self, message, delay_seconds: int):
        """Queue message for later retry."""
        from .models import QueuedMessage
        
        retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        
        await QueuedMessage.objects.acreate(
            message=message,
            recipient=message.recipient,
            queue_type='retry',
            retry_at=retry_at,
            retry_count=message.retry_count,
            error_message=message.last_error or "Queued for retry"
        )
        
        logger.info(f"Message {message.id} queued for retry at {retry_at}")
    
    def _is_circuit_breaker_open(self, endpoint_key: str) -> bool:
        """Check if circuit breaker is open for an endpoint."""
        if endpoint_key not in self.circuit_breaker_state:
            return False
        
        state = self.circuit_breaker_state[endpoint_key]
        
        # Check if circuit breaker should be reset
        if state['opened_at'] + timedelta(seconds=RetryStrategy.CIRCUIT_BREAKER_TIMEOUT) < timezone.now():
            self._reset_circuit_breaker(endpoint_key)
            return False
        
        return state['is_open']
    
    def _reset_circuit_breaker(self, endpoint_key: str):
        """Reset circuit breaker for an endpoint."""
        if endpoint_key in self.circuit_breaker_state:
            self.circuit_breaker_state[endpoint_key] = {
                'failure_count': 0,
                'is_open': False,
                'opened_at': None
            }
    
    async def _handle_retry_failure(self, message, endpoint_key: str):
        """Handle a retry failure and update circuit breaker."""
        # Update circuit breaker state
        if endpoint_key not in self.circuit_breaker_state:
            self.circuit_breaker_state[endpoint_key] = {
                'failure_count': 0,
                'is_open': False,
                'opened_at': None
            }
        
        state = self.circuit_breaker_state[endpoint_key]
        state['failure_count'] += 1
        
        # Open circuit breaker if threshold reached
        if state['failure_count'] >= RetryStrategy.CIRCUIT_BREAKER_THRESHOLD:
            state['is_open'] = True
            state['opened_at'] = timezone.now()
            logger.warning(f"Circuit breaker opened for {endpoint_key}")
        
        # Queue for later retry if not at max retries
        if message.retry_count < RetryStrategy.MAX_TOTAL_RETRIES:
            retry_delay = RetryStrategy.calculate_retry_delay(message.retry_count)
            await self._queue_message_for_retry(message, retry_delay)
        else:
            await self._mark_message_failed(message, "Max retries exceeded")
    
    async def process_retry_queue(self) -> int:
        """
        Process queued messages that are ready for retry.
        
        Returns:
            int: Number of messages processed
        """
        try:
            from .models import QueuedMessage
            
            # Get messages ready for retry
            ready_messages = QueuedMessage.objects.filter(
                queue_type='retry',
                retry_at__lte=timezone.now(),
                processed_at__isnull=True
            ).select_related('message', 'message__sender', 'message__recipient')[:self.batch_size]
            
            processed_count = 0
            
            async for queued_msg in ready_messages:
                try:
                    # Attempt retry
                    success = await self.retry_failed_message(
                        queued_msg.message.id, 
                        'queued_retry'
                    )
                    
                    # Mark as processed
                    queued_msg.processed_at = timezone.now()
                    queued_msg.success = success
                    await queued_msg.asave(update_fields=['processed_at', 'success'])
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing queued message {queued_msg.id}: {str(e)}")
                    
                    # Mark as processed with error
                    queued_msg.processed_at = timezone.now()
                    queued_msg.success = False
                    queued_msg.error_message = str(e)
                    await queued_msg.asave(update_fields=['processed_at', 'success', 'error_message'])
            
            if processed_count > 0:
                logger.info(f"Processed {processed_count} queued retry messages")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing retry queue: {str(e)}")
            return 0
    
    async def cleanup_old_retry_queue(self, days_old: int = 7):
        """Clean up old processed retry queue entries."""
        try:
            from .models import QueuedMessage
            
            cutoff_date = timezone.now() - timedelta(days=days_old)
            
            deleted_count = await QueuedMessage.objects.filter(
                queue_type='retry',
                processed_at__lt=cutoff_date
            ).adelete()
            
            if deleted_count[0] > 0:
                logger.info(f"Cleaned up {deleted_count[0]} old retry queue entries")
            
            return deleted_count[0]
            
        except Exception as e:
            logger.error(f"Error cleaning up retry queue: {str(e)}")
            return 0
    
    async def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry statistics for monitoring."""
        try:
            from .models import Message, QueuedMessage
            
            # Get retry statistics
            stats = {
                'messages_with_retries': await Message.objects.filter(retry_count__gt=0).acount(),
                'failed_messages': await Message.objects.filter(status='failed').acount(),
                'queued_retries': await QueuedMessage.objects.filter(
                    queue_type='retry',
                    processed_at__isnull=True
                ).acount(),
                'circuit_breakers_open': len([
                    k for k, v in self.circuit_breaker_state.items() 
                    if v.get('is_open', False)
                ]),
                'total_circuit_breakers': len(self.circuit_breaker_state)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting retry statistics: {str(e)}")
            return {}
    
    async def force_retry_failed_messages(self, user_id: Optional[int] = None) -> int:
        """
        Force retry all failed messages, optionally for a specific user.
        
        Args:
            user_id: Optional user ID to filter messages
            
        Returns:
            int: Number of messages queued for retry
        """
        try:
            from .models import Message
            
            # Build query
            query = Q(status='failed', retry_count__lt=RetryStrategy.MAX_TOTAL_RETRIES)
            if user_id:
                query &= Q(sender_id=user_id)
            
            failed_messages = Message.objects.filter(query)[:self.batch_size]
            
            retry_count = 0
            
            async for message in failed_messages:
                # Reset retry count and queue for immediate retry
                message.retry_count = 0
                message.status = 'pending'
                message.last_error = None
                await message.asave(update_fields=['retry_count', 'status', 'last_error'])
                
                # Queue for immediate retry
                await self._queue_message_for_retry(message, 0)
                retry_count += 1
            
            logger.info(f"Queued {retry_count} failed messages for retry")
            return retry_count
            
        except Exception as e:
            logger.error(f"Error force retrying failed messages: {str(e)}")
            return 0
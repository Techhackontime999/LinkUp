"""
Offline Message Queue Manager for WhatsApp-like Messaging System

Handles message queuing for offline recipients, chronological delivery when users
come online, 7-day message expiration, and local message queuing for offline senders.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Q, F
from channels.layers import get_channel_layer
import asyncio
import json

User = get_user_model()
logger = logging.getLogger(__name__)


class OfflineQueueManager:
    """
    Manages offline message queuing and delivery.
    
    Features:
    - Message queuing for offline recipients
    - Chronological delivery when users come online
    - 7-day message expiration
    - Local message queuing for offline senders
    - Priority-based message processing
    - Exponential backoff for failed deliveries
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.default_expiry_days = 7
        self.batch_size = 50  # Messages to process per batch
        self.max_delivery_attempts = 3
    
    def queue_message_for_offline_recipient(self, sender_id: int, recipient_id: int,
                                          content: str, priority: int = 2,
                                          client_id: str = None) -> Optional[int]:
        """
        Queue a message for an offline recipient.
        
        Args:
            sender_id: ID of the message sender
            recipient_id: ID of the offline recipient
            content: Message content
            priority: Message priority (1=high, 2=normal, 3=low)
            client_id: Optional client identifier for deduplication
            
        Returns:
            Queued message ID if successful, None otherwise
        """
        try:
            from .models import QueuedMessage
            
            with transaction.atomic():
                # Check for duplicate messages
                if client_id:
                    existing = QueuedMessage.objects.filter(
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        client_id=client_id,
                        is_processed=False
                    ).first()
                    
                    if existing:
                        logger.warning(f"Duplicate message with client_id {client_id}")
                        return existing.id
                
                # Create queued message
                queued_msg = QueuedMessage.objects.create(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    content=content,
                    queue_type='incoming',
                    priority=priority,
                    client_id=client_id or '',
                    expires_at=timezone.now() + timedelta(days=self.default_expiry_days)
                )
                
                logger.info(f"Queued message {queued_msg.id} for offline recipient {recipient_id}")
                return queued_msg.id
        
        except Exception as e:
            logger.error(f"Error queuing message for offline recipient: {e}")
            return None
    
    def queue_outgoing_message_for_offline_sender(self, sender_id: int, recipient_id: int,
                                                content: str, client_id: str = None) -> Optional[int]:
        """
        Queue an outgoing message when sender is offline.
        
        Args:
            sender_id: ID of the offline sender
            recipient_id: ID of the recipient
            content: Message content
            client_id: Optional client identifier
            
        Returns:
            Queued message ID if successful, None otherwise
        """
        try:
            from .models import QueuedMessage
            
            with transaction.atomic():
                # Check for duplicates
                if client_id:
                    existing = QueuedMessage.objects.filter(
                        sender_id=sender_id,
                        client_id=client_id,
                        is_processed=False
                    ).first()
                    
                    if existing:
                        logger.warning(f"Duplicate outgoing message with client_id {client_id}")
                        return existing.id
                
                # Create queued outgoing message
                queued_msg = QueuedMessage.objects.create(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    content=content,
                    queue_type='outgoing',
                    priority=2,  # Normal priority for outgoing
                    client_id=client_id or '',
                    expires_at=timezone.now() + timedelta(days=self.default_expiry_days)
                )
                
                logger.info(f"Queued outgoing message {queued_msg.id} for offline sender {sender_id}")
                return queued_msg.id
        
        except Exception as e:
            logger.error(f"Error queuing outgoing message: {e}")
            return None
    
    def queue_message_for_retry(self, original_message_id: int, sender_id: int,
                              recipient_id: int, content: str, error_message: str,
                              client_id: str = None) -> Optional[int]:
        """
        Queue a message for retry after delivery failure.
        
        Args:
            original_message_id: ID of the original message that failed
            sender_id: ID of the sender
            recipient_id: ID of the recipient
            content: Message content
            error_message: Error that caused the failure
            client_id: Optional client identifier
            
        Returns:
            Queued message ID if successful, None otherwise
        """
        try:
            from .models import QueuedMessage
            
            with transaction.atomic():
                # Create retry queue entry
                queued_msg = QueuedMessage.objects.create(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    content=content,
                    queue_type='retry',
                    priority=1,  # High priority for retries
                    client_id=client_id or '',
                    original_message_id=original_message_id,
                    last_error=error_message,
                    expires_at=timezone.now() + timedelta(days=1)  # Shorter expiry for retries
                )
                
                # Schedule first retry
                queued_msg.schedule_next_retry()
                
                logger.info(f"Queued message {queued_msg.id} for retry")
                return queued_msg.id
        
        except Exception as e:
            logger.error(f"Error queuing message for retry: {e}")
            return None
    
    async def deliver_queued_messages_for_user(self, user_id: int) -> Dict:
        """
        Deliver all queued messages for a user who just came online.
        
        Args:
            user_id: ID of the user who came online
            
        Returns:
            Dict with delivery results
        """
        try:
            from .models import QueuedMessage, Message
            
            # Get queued messages for this user in chronological order
            queued_messages = await self._get_queued_messages_for_user(user_id)
            
            if not queued_messages:
                return {
                    'user_id': user_id,
                    'delivered_count': 0,
                    'failed_count': 0,
                    'messages': []
                }
            
            delivered_count = 0
            failed_count = 0
            delivered_messages = []
            
            # Process messages in batches
            for i in range(0, len(queued_messages), self.batch_size):
                batch = queued_messages[i:i + self.batch_size]
                
                for queued_msg in batch:
                    try:
                        # Create actual message from queued message
                        message = await self._create_message_from_queued(queued_msg)
                        
                        if message:
                            # Deliver message via WebSocket
                            delivery_success = await self._deliver_message_via_websocket(
                                message, user_id
                            )
                            
                            if delivery_success:
                                # Mark queued message as processed
                                await self._mark_queued_message_processed(queued_msg.id)
                                delivered_count += 1
                                
                                delivered_messages.append({
                                    'id': message.id,
                                    'sender': message.sender.username,
                                    'content': message.content,
                                    'created_at': message.created_at.isoformat(),
                                    'client_id': queued_msg.client_id
                                })
                            else:
                                # Mark as failed for retry
                                await self._mark_queued_message_failed(
                                    queued_msg.id, "WebSocket delivery failed"
                                )
                                failed_count += 1
                        else:
                            failed_count += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing queued message {queued_msg.id}: {e}")
                        await self._mark_queued_message_failed(queued_msg.id, str(e))
                        failed_count += 1
            
            result = {
                'user_id': user_id,
                'delivered_count': delivered_count,
                'failed_count': failed_count,
                'total_processed': delivered_count + failed_count,
                'messages': delivered_messages,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Delivered queued messages for user {user_id}: "
                       f"{delivered_count} delivered, {failed_count} failed")
            
            return result
        
        except Exception as e:
            logger.error(f"Error delivering queued messages for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'delivered_count': 0,
                'failed_count': 0
            }
    
    async def _get_queued_messages_for_user(self, user_id: int) -> List:
        """Get queued messages for a user in chronological order."""
        from .models import QueuedMessage
        from django.db import sync_to_async
        
        @sync_to_async
        def get_messages():
            return list(
                QueuedMessage.objects.filter(
                    recipient_id=user_id,
                    is_processed=False,
                    expires_at__gt=timezone.now()
                ).select_related('sender', 'recipient')
                .order_by('priority', 'created_at')
            )
        
        return await get_messages()
    
    async def _create_message_from_queued(self, queued_msg) -> Optional:
        """Create a Message from a QueuedMessage."""
        from .models import Message
        from django.db import sync_to_async
        
        @sync_to_async
        def create_message():
            try:
                # Check if message already exists (prevent duplicates)
                existing = Message.objects.filter(
                    sender=queued_msg.sender,
                    recipient=queued_msg.recipient,
                    content=queued_msg.content,
                    client_id=queued_msg.client_id
                ).first()
                
                if existing:
                    return existing
                
                # Create new message
                message = Message.objects.create(
                    sender=queued_msg.sender,
                    recipient=queued_msg.recipient,
                    content=queued_msg.content,
                    client_id=queued_msg.client_id,
                    status='delivered',  # Mark as delivered since user is online
                    delivered_at=timezone.now()
                )
                
                return message
            
            except Exception as e:
                logger.error(f"Error creating message from queued: {e}")
                return None
        
        return await create_message()
    
    async def _deliver_message_via_websocket(self, message, user_id: int) -> bool:
        """Deliver message to user via WebSocket."""
        try:
            if not self.channel_layer:
                return False
            
            # Create message payload
            payload = {
                'type': 'chat_message',
                'message': {
                    'type': 'message',
                    'id': message.id,
                    'sender': message.sender.username,
                    'recipient': message.recipient.username,
                    'content': message.content,
                    'status': message.status,
                    'client_id': message.client_id,
                    'created_at': message.created_at.isoformat(),
                    'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
                    'is_read': message.is_read,
                    'status_icon': message.get_status_icon()
                }
            }
            
            # Send to user's group
            user_group = f'user_{user_id}'
            await self.channel_layer.group_send(user_group, payload)
            
            return True
        
        except Exception as e:
            logger.error(f"Error delivering message via WebSocket: {e}")
            return False
    
    async def _mark_queued_message_processed(self, queued_msg_id: int) -> bool:
        """Mark a queued message as processed."""
        from .models import QueuedMessage
        from django.db import sync_to_async
        
        @sync_to_async
        def mark_processed():
            try:
                queued_msg = QueuedMessage.objects.get(id=queued_msg_id)
                queued_msg.mark_processed(success=True)
                return True
            except QueuedMessage.DoesNotExist:
                return False
            except Exception as e:
                logger.error(f"Error marking queued message as processed: {e}")
                return False
        
        return await mark_processed()
    
    async def _mark_queued_message_failed(self, queued_msg_id: int, error_message: str) -> bool:
        """Mark a queued message as failed."""
        from .models import QueuedMessage
        from django.db import sync_to_async
        
        @sync_to_async
        def mark_failed():
            try:
                queued_msg = QueuedMessage.objects.get(id=queued_msg_id)
                queued_msg.mark_failed(error_message)
                return True
            except QueuedMessage.DoesNotExist:
                return False
            except Exception as e:
                logger.error(f"Error marking queued message as failed: {e}")
                return False
        
        return await mark_failed()
    
    async def process_retry_queue(self) -> Dict:
        """
        Process messages that are ready for retry.
        
        Returns:
            Dict with processing results
        """
        try:
            from .models import QueuedMessage
            from django.db import sync_to_async
            
            @sync_to_async
            def get_retry_messages():
                return list(
                    QueuedMessage.get_pending_retries()[:self.batch_size]
                )
            
            retry_messages = await get_retry_messages()
            
            if not retry_messages:
                return {
                    'processed_count': 0,
                    'failed_count': 0,
                    'messages': []
                }
            
            processed_count = 0
            failed_count = 0
            
            for queued_msg in retry_messages:
                try:
                    # Attempt to deliver the message
                    if queued_msg.queue_type == 'outgoing':
                        success = await self._retry_outgoing_message(queued_msg)
                    elif queued_msg.queue_type == 'incoming':
                        success = await self._retry_incoming_message(queued_msg)
                    else:  # retry type
                        success = await self._retry_failed_message(queued_msg)
                    
                    if success:
                        await self._mark_queued_message_processed(queued_msg.id)
                        processed_count += 1
                    else:
                        await self._mark_queued_message_failed(
                            queued_msg.id, "Retry attempt failed"
                        )
                        failed_count += 1
                
                except Exception as e:
                    logger.error(f"Error retrying queued message {queued_msg.id}: {e}")
                    await self._mark_queued_message_failed(queued_msg.id, str(e))
                    failed_count += 1
            
            result = {
                'processed_count': processed_count,
                'failed_count': failed_count,
                'total_processed': processed_count + failed_count,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Processed retry queue: {processed_count} succeeded, {failed_count} failed")
            return result
        
        except Exception as e:
            logger.error(f"Error processing retry queue: {e}")
            return {
                'error': str(e),
                'processed_count': 0,
                'failed_count': 0
            }
    
    async def _retry_outgoing_message(self, queued_msg) -> bool:
        """Retry sending an outgoing message."""
        try:
            # Check if recipient is now online
            from .presence_manager import presence_manager
            recipient_presence = presence_manager.get_user_presence(queued_msg.recipient)
            
            if recipient_presence.get('is_online'):
                # Create and deliver message
                message = await self._create_message_from_queued(queued_msg)
                if message:
                    return await self._deliver_message_via_websocket(
                        message, queued_msg.recipient_id
                    )
            
            return False
        
        except Exception as e:
            logger.error(f"Error retrying outgoing message: {e}")
            return False
    
    async def _retry_incoming_message(self, queued_msg) -> bool:
        """Retry delivering an incoming message."""
        try:
            # Check if recipient is online
            from .presence_manager import presence_manager
            recipient_presence = presence_manager.get_user_presence(queued_msg.recipient)
            
            if recipient_presence.get('is_online'):
                # Deliver the queued message
                message = await self._create_message_from_queued(queued_msg)
                if message:
                    return await self._deliver_message_via_websocket(
                        message, queued_msg.recipient_id
                    )
            
            return False
        
        except Exception as e:
            logger.error(f"Error retrying incoming message: {e}")
            return False
    
    async def _retry_failed_message(self, queued_msg) -> bool:
        """Retry a previously failed message."""
        try:
            # Attempt delivery based on queue type
            if queued_msg.original_message_id:
                # Try to update original message status
                from .models import Message
                from django.db import sync_to_async
                
                @sync_to_async
                def update_original():
                    try:
                        original = Message.objects.get(id=queued_msg.original_message_id)
                        original.status = 'sent'
                        original.sent_at = timezone.now()
                        original.save(update_fields=['status', 'sent_at'])
                        return original
                    except Message.DoesNotExist:
                        return None
                
                original_message = await update_original()
                if original_message:
                    return await self._deliver_message_via_websocket(
                        original_message, queued_msg.recipient_id
                    )
            
            return False
        
        except Exception as e:
            logger.error(f"Error retrying failed message: {e}")
            return False
    
    def cleanup_expired_messages(self) -> int:
        """
        Clean up expired messages (older than 7 days).
        
        Returns:
            Number of messages cleaned up
        """
        try:
            from .models import QueuedMessage
            
            expired_count = QueuedMessage.cleanup_expired_messages()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired queued messages")
            
            return expired_count
        
        except Exception as e:
            logger.error(f"Error cleaning up expired messages: {e}")
            return 0
    
    def get_queue_statistics(self, user_id: int = None) -> Dict:
        """
        Get queue statistics for monitoring.
        
        Args:
            user_id: Optional user ID to filter statistics
            
        Returns:
            Dict with queue statistics
        """
        try:
            from .models import QueuedMessage
            
            base_query = QueuedMessage.objects.all()
            if user_id:
                base_query = base_query.filter(
                    Q(sender_id=user_id) | Q(recipient_id=user_id)
                )
            
            stats = {
                'total_queued': base_query.filter(is_processed=False).count(),
                'total_processed': base_query.filter(is_processed=True).count(),
                'by_queue_type': {},
                'by_priority': {},
                'pending_retries': QueuedMessage.get_pending_retries().count(),
                'expired_messages': base_query.filter(
                    expires_at__lt=timezone.now()
                ).count(),
                'timestamp': timezone.now().isoformat()
            }
            
            # Statistics by queue type
            for queue_type, _ in QueuedMessage.QUEUE_TYPES:
                stats['by_queue_type'][queue_type] = base_query.filter(
                    queue_type=queue_type,
                    is_processed=False
                ).count()
            
            # Statistics by priority
            for priority, _ in QueuedMessage.PRIORITY_LEVELS:
                stats['by_priority'][str(priority)] = base_query.filter(
                    priority=priority,
                    is_processed=False
                ).count()
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting queue statistics: {e}")
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }


# Global instance
offline_queue_manager = OfflineQueueManager()
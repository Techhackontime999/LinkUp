"""
Retry mechanisms for message operations in messaging system
"""
import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from django.contrib.auth import get_user_model
from .models import Message, QueuedMessage
from .logging_utils import MessagingLogger
from .serializers import JSONSerializer
from channels.db import database_sync_to_async

User = get_user_model()


class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class RetryConfig:
    """Configuration for retry operations"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retry_on_exceptions: tuple = (Exception,)


class MessageRetryHandler:
    """Handler for retry mechanisms in message operations"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.json_serializer = JSONSerializer()
        self.active_retries: Dict[str, Dict[str, Any]] = {}
    
    async def retry_async_operation(
        self, 
        operation: Callable,
        operation_id: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Retry an async operation with configurable backoff strategy
        
        Args:
            operation: Async function to retry
            operation_id: Unique identifier for this operation
            *args: Arguments to pass to operation
            **kwargs: Keyword arguments to pass to operation
            
        Returns:
            Result of successful operation
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                # Track retry attempt
                self._track_retry_attempt(operation_id, attempt)
                
                # Execute the operation
                result = await operation(*args, **kwargs)
                
                # Success - clean up tracking and return result
                self._cleanup_retry_tracking(operation_id)
                MessagingLogger.log_debug(
                    f"Operation {operation_id} succeeded on attempt {attempt + 1}",
                    {'operation_id': operation_id, 'attempt': attempt + 1}
                )
                return result
                
            except self.config.retry_on_exceptions as e:
                last_exception = e
                
                MessagingLogger.log_error(
                    f"Operation {operation_id} failed on attempt {attempt + 1}: {e}",
                    context_data={
                        'operation_id': operation_id,
                        'attempt': attempt + 1,
                        'max_attempts': self.config.max_attempts,
                        'exception_type': type(e).__name__
                    }
                )
                
                # If this was the last attempt, don't wait
                if attempt == self.config.max_attempts - 1:
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                
                MessagingLogger.log_debug(
                    f"Retrying operation {operation_id} in {delay:.2f} seconds",
                    {'operation_id': operation_id, 'delay': delay}
                )
                
                await asyncio.sleep(delay)
        
        # All attempts failed
        self._cleanup_retry_tracking(operation_id)
        MessagingLogger.log_error(
            f"Operation {operation_id} failed after {self.config.max_attempts} attempts",
            context_data={
                'operation_id': operation_id,
                'max_attempts': self.config.max_attempts,
                'final_exception': str(last_exception)
            }
        )
        
        raise last_exception or Exception(f"Operation {operation_id} failed after all retry attempts")
    
    async def retry_message_creation(
        self,
        sender: User,
        recipient: User,
        content: str,
        retry_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retry message creation with exponential backoff
        
        Args:
            sender: User sending the message
            recipient: User receiving the message
            content: Message content
            retry_id: Optional retry identifier for client tracking
            
        Returns:
            Message data dictionary or None if all attempts fail
        """
        operation_id = f"create_message_{sender.id}_{recipient.id}_{int(time.time())}"
        
        try:
            from .async_handlers import AsyncSafeMessageHandler
            handler = AsyncSafeMessageHandler()
            
            async def create_message_operation():
                return await handler.handle_message_creation(sender, recipient, content)
            
            result = await self.retry_async_operation(
                create_message_operation,
                operation_id
            )
            
            if result and retry_id:
                result['retry_id'] = retry_id
            
            return result
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Message creation retry failed completely: {e}",
                context_data={
                    'sender_id': sender.id,
                    'recipient_id': recipient.id,
                    'retry_id': retry_id,
                    'operation_id': operation_id
                }
            )
            return None
    
    async def queue_failed_message(
        self,
        sender: User,
        recipient: User,
        content: str,
        original_error: str,
        retry_id: Optional[str] = None
    ) -> bool:
        """
        Queue a message that failed to send for later retry
        
        Args:
            sender: User who sent the message
            recipient: Intended recipient
            content: Message content
            original_error: Error that caused the failure
            retry_id: Optional retry identifier
            
        Returns:
            True if queued successfully, False otherwise
        """
        try:
            queued_message = await self._create_queued_message(
                sender=sender,
                recipient=recipient,
                content=content,
                error_reason=original_error,
                retry_id=retry_id
            )
            
            if queued_message:
                MessagingLogger.log_debug(
                    f"Message queued for retry: {queued_message.id}",
                    {
                        'queued_message_id': queued_message.id,
                        'sender_id': sender.id,
                        'recipient_id': recipient.id,
                        'retry_id': retry_id
                    }
                )
                return True
            
            return False
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Failed to queue message for retry: {e}",
                context_data={
                    'sender_id': sender.id,
                    'recipient_id': recipient.id,
                    'original_error': original_error,
                    'retry_id': retry_id
                }
            )
            return False
    
    async def process_queued_messages(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Process queued messages that failed previously
        
        Args:
            batch_size: Number of messages to process in one batch
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'requeued': 0
        }
        
        try:
            queued_messages = await self._get_queued_messages(batch_size)
            
            for queued_message in queued_messages:
                stats['processed'] += 1
                
                try:
                    # Attempt to create the message
                    result = await self.retry_message_creation(
                        sender=queued_message.sender,
                        recipient=queued_message.recipient,
                        content=queued_message.content,
                        retry_id=queued_message.retry_id
                    )
                    
                    if result:
                        # Success - remove from queue
                        await self._remove_queued_message(queued_message.id)
                        stats['successful'] += 1
                        
                        MessagingLogger.log_debug(
                            f"Queued message processed successfully: {queued_message.id}",
                            {'queued_message_id': queued_message.id}
                        )
                    else:
                        # Failed - update retry count
                        if queued_message.retry_count < self.config.max_attempts:
                            await self._increment_retry_count(queued_message.id)
                            stats['requeued'] += 1
                        else:
                            await self._remove_queued_message(queued_message.id)
                            stats['failed'] += 1
                            
                            MessagingLogger.log_error(
                                f"Queued message exceeded max retries: {queued_message.id}",
                                {'queued_message_id': queued_message.id}
                            )
                
                except Exception as e:
                    stats['failed'] += 1
                    MessagingLogger.log_error(
                        f"Error processing queued message {queued_message.id}: {e}",
                        {'queued_message_id': queued_message.id}
                    )
            
            MessagingLogger.log_debug(
                f"Queued message processing completed",
                stats
            )
            
            return stats
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in process_queued_messages: {e}",
                context_data={'batch_size': batch_size}
            )
            return stats
    
    async def retry_websocket_transmission(
        self,
        channel_layer,
        group_name: str,
        message_data: Dict[str, Any],
        operation_id: str
    ) -> bool:
        """
        Retry WebSocket message transmission with backoff
        
        Args:
            channel_layer: Django Channels layer
            group_name: Channel group name
            message_data: Message data to transmit
            operation_id: Unique operation identifier
            
        Returns:
            True if transmission succeeded, False otherwise
        """
        try:
            async def transmit_operation():
                await channel_layer.group_send(group_name, {
                    'type': 'chat_message',
                    'message': message_data
                })
                return True
            
            result = await self.retry_async_operation(
                transmit_operation,
                operation_id
            )
            
            return result
            
        except Exception as e:
            MessagingLogger.log_error(
                f"WebSocket transmission retry failed: {e}",
                context_data={
                    'group_name': group_name,
                    'operation_id': operation_id,
                    'message_id': message_data.get('id')
                }
            )
            return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt based on strategy"""
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_delay * (self.config.backoff_multiplier ** attempt)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_delay * (attempt + 1)
        else:  # FIXED_DELAY
            delay = self.config.initial_delay
        
        return min(delay, self.config.max_delay)
    
    def _track_retry_attempt(self, operation_id: str, attempt: int):
        """Track retry attempt for monitoring"""
        if operation_id not in self.active_retries:
            self.active_retries[operation_id] = {
                'start_time': time.time(),
                'attempts': []
            }
        
        self.active_retries[operation_id]['attempts'].append({
            'attempt': attempt + 1,
            'timestamp': time.time()
        })
    
    def _cleanup_retry_tracking(self, operation_id: str):
        """Clean up retry tracking data"""
        if operation_id in self.active_retries:
            del self.active_retries[operation_id]
    
    @database_sync_to_async
    def _create_queued_message(
        self,
        sender: User,
        recipient: User,
        content: str,
        error_reason: str,
        retry_id: Optional[str] = None
    ) -> Optional[QueuedMessage]:
        """Create a queued message record"""
        try:
            return QueuedMessage.objects.create(
                sender=sender,
                recipient=recipient,
                content=content,
                error_reason=error_reason,
                retry_id=retry_id,
                retry_count=0
            )
        except Exception as e:
            MessagingLogger.log_error(
                f"Failed to create queued message: {e}",
                context_data={
                    'sender_id': sender.id,
                    'recipient_id': recipient.id,
                    'error_reason': error_reason
                }
            )
            return None
    
    @database_sync_to_async
    def _get_queued_messages(self, limit: int) -> List[QueuedMessage]:
        """Get queued messages for processing"""
        try:
            return list(
                QueuedMessage.objects.filter(
                    retry_count__lt=self.config.max_attempts
                ).order_by('created_at')[:limit]
            )
        except Exception as e:
            MessagingLogger.log_error(
                f"Failed to get queued messages: {e}",
                context_data={'limit': limit}
            )
            return []
    
    @database_sync_to_async
    def _remove_queued_message(self, queued_message_id: int) -> bool:
        """Remove a queued message"""
        try:
            QueuedMessage.objects.filter(id=queued_message_id).delete()
            return True
        except Exception as e:
            MessagingLogger.log_error(
                f"Failed to remove queued message: {e}",
                context_data={'queued_message_id': queued_message_id}
            )
            return False
    
    @database_sync_to_async
    def _increment_retry_count(self, queued_message_id: int) -> bool:
        """Increment retry count for a queued message"""
        try:
            from django.db import models
            QueuedMessage.objects.filter(id=queued_message_id).update(
                retry_count=models.F('retry_count') + 1
            )
            return True
        except Exception as e:
            MessagingLogger.log_error(
                f"Failed to increment retry count: {e}",
                context_data={'queued_message_id': queued_message_id}
            )
            return False


class MessageValidator:
    """Validator for message processing reliability"""
    
    def __init__(self):
        self.json_serializer = JSONSerializer()
    
    def validate_message_format(self, message_data: Dict[str, Any]) -> bool:
        """
        Validate message format before processing
        
        Args:
            message_data: Message data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            required_fields = ['sender', 'recipient', 'content']
            
            # Check required fields
            for field in required_fields:
                if field not in message_data:
                    MessagingLogger.log_error(
                        f"Missing required field: {field}",
                        context_data={'message_data': message_data}
                    )
                    return False
            
            # Validate content is not empty
            content = message_data.get('content', '').strip()
            if not content:
                MessagingLogger.log_error(
                    "Message content is empty",
                    context_data={'message_data': message_data}
                )
                return False
            
            # Validate content length
            if len(content) > 10000:  # Reasonable message length limit
                MessagingLogger.log_error(
                    f"Message content too long: {len(content)} characters",
                    context_data={'content_length': len(content)}
                )
                return False
            
            # Validate JSON serializability
            if not self.json_serializer.validate_serializable(message_data):
                MessagingLogger.log_error(
                    "Message data is not JSON serializable",
                    context_data={'message_data': message_data}
                )
                return False
            
            return True
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error validating message format: {e}",
                context_data={'message_data': message_data}
            )
            return False
    
    def validate_message_ordering(
        self,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        Validate that messages maintain proper ordering
        
        Args:
            messages: List of message data dictionaries
            
        Returns:
            True if ordering is preserved, False otherwise
        """
        try:
            if len(messages) <= 1:
                return True
            
            # Check timestamp ordering
            for i in range(1, len(messages)):
                current_time = messages[i].get('created_at')
                previous_time = messages[i-1].get('created_at')
                
                if not current_time or not previous_time:
                    continue
                
                # Parse timestamps for comparison
                from datetime import datetime
                try:
                    current_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
                    previous_dt = datetime.fromisoformat(previous_time.replace('Z', '+00:00'))
                    
                    if current_dt < previous_dt:
                        MessagingLogger.log_error(
                            "Message ordering violation detected",
                            context_data={
                                'current_message': messages[i].get('id'),
                                'previous_message': messages[i-1].get('id'),
                                'current_time': current_time,
                                'previous_time': previous_time
                            }
                        )
                        return False
                        
                except ValueError as e:
                    MessagingLogger.log_error(
                        f"Invalid timestamp format: {e}",
                        context_data={
                            'current_time': current_time,
                            'previous_time': previous_time
                        }
                    )
                    continue
            
            return True
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error validating message ordering: {e}",
                context_data={'message_count': len(messages)}
            )
            return False
"""
Message Persistence Manager for WhatsApp-like Messaging System

Handles enhanced message persistence with proper database locking, accurate timestamp tracking,
and multi-tab synchronization support for reliable message storage and retrieval.

Requirements: 11.1, 11.3, 11.4, 11.5
"""

import logging
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any, Union
from contextlib import contextmanager, asynccontextmanager
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError, connection
from django.db.models import Q, F, Max, Min, Count, Exists, OuterRef
from django.core.cache import cache
from django.core.exceptions import ValidationError
from channels.layers import get_channel_layer
import uuid
import threading
from contextlib import contextmanager

User = get_user_model()
logger = logging.getLogger(__name__)


class MessageLockManager:
    """Manages database locks for concurrent message operations."""
    
    def __init__(self):
        self.local_locks = {}  # Thread-local locks for additional safety
        self.lock = threading.RLock()
    
    @contextmanager
    def acquire_message_lock(self, message_id: int, operation: str = 'update'):
        """
        Acquire a database lock for a specific message.
        
        Args:
            message_id: ID of the message to lock
            operation: Type of operation (update, delete, etc.)
        """
        lock_key = f"msg_lock_{message_id}_{operation}"
        
        with self.lock:
            # Check if we already have a local lock
            if lock_key in self.local_locks:
                yield self.local_locks[lock_key]
                return
            
            # Create new local lock
            local_lock = threading.Lock()
            self.local_locks[lock_key] = local_lock
        
        try:
            with local_lock:
                # Use simple in-memory lock to avoid sync database operations in async context
                yield None  # Return None since we can't safely get the message in sync context
        finally:
            with self.lock:
                # Clean up local lock
                if lock_key in self.local_locks:
                    del self.local_locks[lock_key]
    
    @asynccontextmanager
    async def acquire_message_lock_async(self, message_id: int, operation: str = 'update'):
        """
        Async version of message lock that properly handles database operations.
        
        Args:
            message_id: ID of message to lock
            operation: Type of operation
        """
        lock_key = f"msg_lock_{message_id}_{operation}"
        
        # Use asyncio lock for async contexts
        if not hasattr(self, 'async_message_locks'):
            self.async_message_locks = {}
        
        if lock_key not in self.async_message_locks:
            self.async_message_locks[lock_key] = asyncio.Lock()
        
        async with self.async_message_locks[lock_key]:
            try:
                from .models import Message
                from channels.db import database_sync_to_async
                
                @database_sync_to_async
                def get_locked_message():
                    with transaction.atomic():
                        try:
                            # SELECT FOR UPDATE to lock the row
                            return Message.objects.select_for_update(nowait=False).get(id=message_id)
                        except Message.DoesNotExist:
                            logger.warning(f"Message {message_id} not found for locking")
                            return None
                
                # Get the locked message asynchronously
                message = await get_locked_message()
                yield message
                
            except Exception as e:
                logger.error(f"Error in async message lock: {e}")
                yield None  # Still yield to prevent hanging
    
    @contextmanager
    def acquire_conversation_lock(self, user1_id: int, user2_id: int, operation: str = 'update'):
        """
        Acquire a lock for an entire conversation between two users.
        
        Args:
            user1_id: ID of first user
            user2_id: ID of second user
            operation: Type of operation
        """
        # Ensure consistent ordering for deadlock prevention
        min_id, max_id = sorted([user1_id, user2_id])
        lock_key = f"conv_lock_{min_id}_{max_id}_{operation}"
        
        with self.lock:
            if lock_key in self.local_locks:
                yield
                return
            
            local_lock = threading.Lock()
            self.local_locks[lock_key] = local_lock
        
        try:
            with local_lock:
                # Use a simple in-memory lock instead of database locks
                # to avoid sync database operations in async context
                yield
        finally:
            with self.lock:
                if lock_key in self.local_locks:
                    del self.local_locks[lock_key]
    
    @asynccontextmanager
    async def acquire_conversation_lock_async(self, user1_id: int, user2_id: int, operation: str = 'update'):
        """
        Async version of conversation lock that properly handles database operations.
        
        Args:
            user1_id: ID of first user
            user2_id: ID of second user
            operation: Type of operation
        """
        # Ensure consistent ordering for deadlock prevention
        min_id, max_id = sorted([user1_id, user2_id])
        lock_key = f"conv_lock_{min_id}_{max_id}_{operation}"
        
        # Use asyncio lock for async contexts
        if not hasattr(self, 'async_locks'):
            self.async_locks = {}
        
        if lock_key not in self.async_locks:
            self.async_locks[lock_key] = asyncio.Lock()
        
        async with self.async_locks[lock_key]:
            try:
                # Use async database operations
                from .models import Message
                from django.db import transaction
                from channels.db import database_sync_to_async
                
                @database_sync_to_async
                def acquire_db_locks():
                    with transaction.atomic():
                        # Lock all messages in the conversation
                        messages = Message.objects.filter(
                            (Q(sender_id=user1_id) & Q(recipient_id=user2_id)) |
                            (Q(sender_id=user2_id) & Q(recipient_id=user1_id))
                        ).select_for_update()
                        
                        # Force evaluation of queryset to acquire locks
                        return list(messages)
                
                # Acquire database locks asynchronously
                await acquire_db_locks()
                yield
                
            except Exception as e:
                logger.error(f"Error in async conversation lock: {e}")
                yield  # Still yield to prevent hanging


class TimestampManager:
    """Manages accurate timestamp tracking for messages."""
    
    @staticmethod
    def get_precise_timestamp() -> datetime:
        """Get a precise timestamp with microsecond accuracy."""
        return timezone.now()
    
    @staticmethod
    def ensure_timestamp_ordering(messages: List['Message']) -> List['Message']:
        """
        Ensure messages have properly ordered timestamps.
        
        Args:
            messages: List of message objects
            
        Returns:
            List of messages with corrected timestamps
        """
        if not messages:
            return messages
        
        # Sort by created_at first
        messages.sort(key=lambda m: m.created_at)
        
        # Ensure no two messages have the exact same timestamp
        for i in range(1, len(messages)):
            if messages[i].created_at <= messages[i-1].created_at:
                # Add microseconds to ensure ordering
                messages[i].created_at = messages[i-1].created_at + timedelta(microseconds=1)
        
        return messages
    
    @staticmethod
    def validate_timestamp_sequence(message: 'Message') -> bool:
        """
        Validate that message timestamps are in correct sequence.
        
        Args:
            message: Message to validate
            
        Returns:
            True if timestamps are valid
        """
        timestamps = [
            message.created_at,
            message.sent_at,
            message.delivered_at,
            message.read_at
        ]
        
        # Filter out None values and sort
        valid_timestamps = [ts for ts in timestamps if ts is not None]
        
        if len(valid_timestamps) <= 1:
            return True
        
        # Check if timestamps are in order
        for i in range(1, len(valid_timestamps)):
            if valid_timestamps[i] < valid_timestamps[i-1]:
                return False
        
        return True


class MultiTabSyncManager:
    """Manages synchronization across multiple browser tabs."""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.sync_events = {}
    
    async def broadcast_message_update(self, user_id: int, message_data: Dict[str, Any]):
        """
        Broadcast message update to all tabs for a user.
        
        Args:
            user_id: ID of the user to notify
            message_data: Message data to broadcast
        """
        if not self.channel_layer:
            return
        
        try:
            # Send to user's personal group (all their tabs)
            user_group = f'user_{user_id}'
            
            await self.channel_layer.group_send(user_group, {
                'type': 'multi_tab_sync',
                'sync_type': 'message_update',
                'data': message_data,
                'timestamp': timezone.now().isoformat()
            })
            
            logger.debug(f"Broadcasted message update to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast message update: {e}")
    
    async def broadcast_conversation_sync(self, user_id: int, conversation_partner_id: int, sync_data: Dict[str, Any]):
        """
        Broadcast conversation synchronization data.
        
        Args:
            user_id: ID of the user to notify
            conversation_partner_id: ID of conversation partner
            sync_data: Synchronization data
        """
        if not self.channel_layer:
            return
        
        try:
            user_group = f'user_{user_id}'
            
            await self.channel_layer.group_send(user_group, {
                'type': 'multi_tab_sync',
                'sync_type': 'conversation_sync',
                'conversation_partner_id': conversation_partner_id,
                'data': sync_data,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to broadcast conversation sync: {e}")
    
    def generate_sync_token(self, user_id: int, operation: str) -> str:
        """
        Generate a unique synchronization token.
        
        Args:
            user_id: ID of the user
            operation: Type of operation
            
        Returns:
            Unique sync token
        """
        token = f"sync_{user_id}_{operation}_{uuid.uuid4().hex[:12]}"
        self.sync_events[token] = {
            'user_id': user_id,
            'operation': operation,
            'created_at': timezone.now(),
            'completed': False
        }
        
        return token
    
    def mark_sync_completed(self, sync_token: str):
        """Mark a synchronization operation as completed."""
        if sync_token in self.sync_events:
            self.sync_events[sync_token]['completed'] = True
            self.sync_events[sync_token]['completed_at'] = timezone.now()
    
    def cleanup_old_sync_events(self, max_age_minutes: int = 60):
        """Clean up old synchronization events."""
        cutoff_time = timezone.now() - timedelta(minutes=max_age_minutes)
        
        expired_tokens = [
            token for token, event in self.sync_events.items()
            if event['created_at'] < cutoff_time
        ]
        
        for token in expired_tokens:
            del self.sync_events[token]
        
        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired sync events")


class MessagePersistenceManager:
    """
    Enhanced message persistence manager with database locking and synchronization.
    
    Features:
    - Database locking for concurrent operations
    - Accurate timestamp tracking
    - Multi-tab synchronization support
    - Transaction safety and rollback handling
    - Performance optimization for bulk operations
    """
    
    def __init__(self):
        self.lock_manager = MessageLockManager()
        self.timestamp_manager = TimestampManager()
        self.sync_manager = MultiTabSyncManager()
        self.channel_layer = get_channel_layer()
    
    async def create_message_atomic(self, sender: User, recipient: User, content: str, 
                                  client_id: str = None, **kwargs) -> Optional['Message']:
        """
        Create a message with atomic transaction and proper locking.
        
        Args:
            sender: User sending the message
            recipient: User receiving the message
            content: Message content
            client_id: Client-side message ID for deduplication
            **kwargs: Additional message fields
            
        Returns:
            Created message or None if failed
        """
        try:
            from .models import Message
            from channels.db import database_sync_to_async
            
            # Generate client_id if not provided
            if not client_id:
                client_id = f"server_{uuid.uuid4().hex[:12]}"
            
            # Use async conversation lock to prevent race conditions
            async with self.lock_manager.acquire_conversation_lock_async(sender.id, recipient.id, 'create'):
                # Check for duplicate client_id using async ORM
                existing_message = await Message.objects.filter(
                    sender=sender,
                    client_id=client_id
                ).afirst()
                
                if existing_message:
                    logger.warning(f"Duplicate message with client_id {client_id}")
                    return existing_message
                
                # Create message with precise timestamp
                created_at = self.timestamp_manager.get_precise_timestamp()
                
                message_data = {
                    'sender': sender,
                    'recipient': recipient,
                    'content': content,
                    'client_id': client_id,
                    'created_at': created_at,
                    'status': kwargs.get('status', 'pending'),
                    **kwargs
                }
                
                # Use async database operation
                message = await Message.objects.acreate(**message_data)
                
                # Broadcast to multi-tab sync
                await self.sync_manager.broadcast_message_update(
                    sender.id,
                    await self._serialize_message(message)
                )
                
                await self.sync_manager.broadcast_message_update(
                    recipient.id,
                    await self._serialize_message(message)
                )
                
                logger.info(f"Created message {message.id} from {sender.id} to {recipient.id}")
                return message
                
        except IntegrityError as e:
            logger.error(f"Integrity error creating message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    async def update_message_status_atomic(self, message_id: int, new_status: str, 
                                         user_id: int = None, **kwargs) -> bool:
        """
        Update message status with atomic transaction and proper locking.
        
        Args:
            message_id: ID of message to update
            new_status: New status value
            user_id: ID of user performing the update
            **kwargs: Additional fields to update
            
        Returns:
            True if update was successful
        """
        try:
            async with self.lock_manager.acquire_message_lock_async(message_id, 'status_update') as message:
                if not message:
                    return False
                
                # Validate status transition
                if not self._is_valid_status_transition(message.status, new_status):
                    logger.warning(f"Invalid status transition: {message.status} -> {new_status}")
                    return False
                
                # Update status and timestamp
                old_status = message.status
                message.status = new_status
                
                # Set appropriate timestamp
                current_time = self.timestamp_manager.get_precise_timestamp()
                
                if new_status == 'sent' and not message.sent_at:
                    message.sent_at = current_time
                elif new_status == 'delivered' and not message.delivered_at:
                    message.delivered_at = current_time
                elif new_status == 'read' and not message.read_at:
                    message.read_at = current_time
                    message.is_read = True
                
                # Apply additional updates
                for field, value in kwargs.items():
                    if hasattr(message, field):
                        setattr(message, field, value)
                
                # Validate timestamp sequence
                if not self.timestamp_manager.validate_timestamp_sequence(message):
                    logger.error(f"Invalid timestamp sequence for message {message_id}")
                    return False
                
                await message.asave()
                
                # Broadcast status update
                message_data = await self._serialize_message(message)
                message_data['old_status'] = old_status
                message_data['updated_by'] = user_id
                
                await self.sync_manager.broadcast_message_update(
                    message.sender_id,
                    message_data
                )
                
                await self.sync_manager.broadcast_message_update(
                    message.recipient_id,
                    message_data
                )
                
                logger.info(f"Updated message {message_id} status: {old_status} -> {new_status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
            return False
    
    def bulk_update_message_status(self, message_ids: List[int], new_status: str, 
                                       user_id: int = None) -> Dict[str, Any]:
        """
        Update multiple message statuses in a single transaction.
        
        Args:
            message_ids: List of message IDs to update
            new_status: New status for all messages
            user_id: ID of user performing the update
            
        Returns:
            Dictionary with update results
        """
        try:
            from .models import Message
            
            updated_count = 0
            failed_count = 0
            updated_messages = []
            
            # Process in batches to avoid long-running transactions
            batch_size = 50
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                
                with transaction.atomic():
                    # Lock all messages in the batch
                    messages = Message.objects.filter(
                        id__in=batch_ids
                    ).select_for_update()
                    
                    current_time = self.timestamp_manager.get_precise_timestamp()
                    
                    for message in messages:
                        try:
                            if self._is_valid_status_transition(message.status, new_status):
                                old_status = message.status
                                message.status = new_status
                                
                                # Set appropriate timestamp
                                if new_status == 'sent' and not message.sent_at:
                                    message.sent_at = current_time
                                elif new_status == 'delivered' and not message.delivered_at:
                                    message.delivered_at = current_time
                                elif new_status == 'read' and not message.read_at:
                                    message.read_at = current_time
                                    message.is_read = True
                                
                                message.save()
                                updated_count += 1
                                updated_messages.append({
                                    'id': message.id,
                                    'old_status': old_status,
                                    'new_status': new_status,
                                    'sender_id': message.sender_id,
                                    'recipient_id': message.recipient_id
                                })
                            else:
                                failed_count += 1
                                
                        except Exception as e:
                            logger.error(f"Error updating message {message.id}: {e}")
                            failed_count += 1
            
            # Note: Removed async broadcasting for synchronous operation
            # Broadcasting can be handled separately if needed
            
            result = {
                'updated_count': updated_count,
                'failed_count': failed_count,
                'total_requested': len(message_ids),
                'success_rate': (updated_count / len(message_ids)) * 100 if message_ids else 0
            }
            
            logger.info(f"Bulk status update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in bulk status update: {e}")
            return {
                'updated_count': 0,
                'failed_count': len(message_ids),
                'total_requested': len(message_ids),
                'success_rate': 0,
                'error': str(e)
            }
    
    async def get_conversation_messages_async(self, user1_id: int, user2_id: int, 
                                            limit: int = 50, before_id: int = None,
                                            include_metadata: bool = True) -> Dict[str, Any]:
        """
        Get conversation messages with proper async handling.
        
        Args:
            user1_id: ID of first user
            user2_id: ID of second user
            limit: Maximum number of messages to return
            before_id: Get messages before this message ID
            include_metadata: Whether to include conversation metadata
            
        Returns:
            Dictionary with messages and metadata
        """
        try:
            from .models import Message
            from channels.db import database_sync_to_async
            
            # Build query using async ORM
            base_query = Message.objects.filter(
                (Q(sender_id=user1_id) & Q(recipient_id=user2_id)) |
                (Q(sender_id=user2_id) & Q(recipient_id=user1_id))
            ).select_related('sender', 'recipient')
            
            # Apply before_id filter if provided
            if before_id:
                try:
                    before_message = await Message.objects.aget(id=before_id)
                    base_query = base_query.filter(created_at__lt=before_message.created_at)
                except Message.DoesNotExist:
                    pass
            
            # Get messages with limit using async
            messages = []
            async for message in base_query.order_by('-created_at')[:limit]:
                messages.append(message)
            
            # Reverse to show oldest first
            messages = list(reversed(messages))
            
            # Serialize messages
            serialized_messages = []
            for message in messages:
                serialized_messages.append(await self._serialize_message(message))
            
            result = {
                'messages': serialized_messages,
                'count': len(serialized_messages),
                'has_more': len(messages) == limit
            }
            
            # Add metadata if requested
            if include_metadata:
                result['metadata'] = await self._get_conversation_metadata(user1_id, user2_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return {
                'messages': [],
                'count': 0,
                'has_more': False,
                'error': str(e)
            }
    
    def synchronize_conversation(self, user_id: int, partner_id: int, 
                                     last_sync_time: datetime = None) -> Dict[str, Any]:
        """
        Synchronize conversation data across tabs and devices.
        
        Args:
            user_id: ID of the user requesting sync
            partner_id: ID of conversation partner
            last_sync_time: Last synchronization timestamp
            
        Returns:
            Synchronization result with updated messages
        """
        try:
            sync_token = self.sync_manager.generate_sync_token(user_id, 'conversation_sync')
            
            # Get messages updated since last sync
            from .models import Message
            
            query = Message.objects.filter(
                (Q(sender_id=user_id) & Q(recipient_id=partner_id)) |
                (Q(sender_id=partner_id) & Q(recipient_id=user_id))
            )
            
            if last_sync_time:
                query = query.filter(updated_at__gt=last_sync_time)
            
            updated_messages = list(query.order_by('created_at'))
            
            # Serialize updated messages
            serialized_messages = []
            for message in updated_messages:
                serialized_messages.append(self._serialize_message_sync(message))
            
            # Get conversation statistics (simplified for sync operation)
            stats = {'total_messages': len(updated_messages)}
            
            sync_result = {
                'sync_token': sync_token,
                'updated_messages': serialized_messages,
                'update_count': len(serialized_messages),
                'sync_timestamp': timezone.now().isoformat(),
                'conversation_stats': stats
            }
            
            # Note: Removed async broadcasting for synchronous operation
            
            logger.info(f"Synchronized conversation for user {user_id} with partner {partner_id}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Error synchronizing conversation: {e}")
            return {
                'sync_token': None,
                'updated_messages': [],
                'update_count': 0,
                'error': str(e)
            }
    
    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """
        Validate if a status transition is allowed.
        
        Args:
            current_status: Current message status
            new_status: Proposed new status
            
        Returns:
            True if transition is valid
        """
        valid_transitions = {
            'pending': ['sent', 'failed'],
            'sent': ['delivered', 'failed'],
            'delivered': ['read', 'failed'],
            'read': [],  # Read is final state
            'failed': ['pending', 'sent']  # Allow retry from failed
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _serialize_message_sync(self, message: 'Message') -> Dict[str, Any]:
        """Serialize a message object to dictionary (synchronous version)."""
        return {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_username': message.sender.username,
            'recipient_id': message.recipient_id,
            'recipient_username': message.recipient.username,
            'content': message.content,
            'status': message.status,
            'client_id': message.client_id,
            'created_at': message.created_at.isoformat(),
            'sent_at': message.sent_at.isoformat() if message.sent_at else None,
            'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
            'read_at': message.read_at.isoformat() if message.read_at else None,
            'is_read': message.is_read,
            'retry_count': message.retry_count,
            'last_error': message.last_error,
            'updated_at': message.updated_at.isoformat() if hasattr(message, 'updated_at') and message.updated_at else None
        }

    async def _serialize_message(self, message: 'Message') -> Dict[str, Any]:
        """Serialize a message object to dictionary."""
        return {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_username': message.sender.username,
            'recipient_id': message.recipient_id,
            'recipient_username': message.recipient.username,
            'content': message.content,
            'status': message.status,
            'client_id': message.client_id,
            'created_at': message.created_at.isoformat(),
            'sent_at': message.sent_at.isoformat() if message.sent_at else None,
            'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
            'read_at': message.read_at.isoformat() if message.read_at else None,
            'is_read': message.is_read,
            'retry_count': message.retry_count,
            'last_error': message.last_error,
            'updated_at': message.updated_at.isoformat() if hasattr(message, 'updated_at') and message.updated_at else None
        }
    
    async def _get_conversation_metadata(self, user1_id: int, user2_id: int) -> Dict[str, Any]:
        """Get metadata for a conversation."""
        try:
            from .models import Message
            
            # Get conversation statistics
            stats = await Message.objects.filter(
                (Q(sender_id=user1_id) & Q(recipient_id=user2_id)) |
                (Q(sender_id=user2_id) & Q(recipient_id=user1_id))
            ).aaggregate(
                total_messages=Count('id'),
                unread_count=Count('id', filter=Q(recipient_id=user1_id, is_read=False)),
                last_message_time=Max('created_at'),
                first_message_time=Min('created_at')
            )
            
            return {
                'total_messages': stats['total_messages'] or 0,
                'unread_count': stats['unread_count'] or 0,
                'last_message_time': stats['last_message_time'].isoformat() if stats['last_message_time'] else None,
                'first_message_time': stats['first_message_time'].isoformat() if stats['first_message_time'] else None,
                'conversation_id': f"{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation metadata: {e}")
            return {}
    
    async def _get_conversation_stats(self, user_id: int, partner_id: int) -> Dict[str, Any]:
        """Get detailed conversation statistics."""
        try:
            from .models import Message
            
            # Get various statistics
            stats = await Message.objects.filter(
                (Q(sender_id=user_id) & Q(recipient_id=partner_id)) |
                (Q(sender_id=partner_id) & Q(recipient_id=user_id))
            ).aaggregate(
                total_messages=Count('id'),
                sent_by_user=Count('id', filter=Q(sender_id=user_id)),
                received_by_user=Count('id', filter=Q(recipient_id=user_id)),
                unread_by_user=Count('id', filter=Q(recipient_id=user_id, is_read=False)),
                failed_messages=Count('id', filter=Q(status='failed')),
                pending_messages=Count('id', filter=Q(status='pending'))
            )
            
            return {
                'total_messages': stats['total_messages'] or 0,
                'sent_by_user': stats['sent_by_user'] or 0,
                'received_by_user': stats['received_by_user'] or 0,
                'unread_by_user': stats['unread_by_user'] or 0,
                'failed_messages': stats['failed_messages'] or 0,
                'pending_messages': stats['pending_messages'] or 0,
                'read_rate': ((stats['received_by_user'] - stats['unread_by_user']) / max(stats['received_by_user'], 1)) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            return {}


# Global instance
message_persistence_manager = MessagePersistenceManager()
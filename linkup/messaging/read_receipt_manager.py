"""
Read Receipt Manager for WhatsApp-like Messaging System

Handles automatic read receipt generation, bulk read receipt processing,
read receipt deduplication, and real-time status updates to senders.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Q, F
from channels.layers import get_channel_layer
import asyncio
import json

User = get_user_model()
logger = logging.getLogger(__name__)


class ReadReceiptManager:
    """
    Manages read receipts for messages with deduplication and bulk processing.
    
    Features:
    - Automatic read receipt generation on message view
    - Bulk read receipt processing for multiple messages
    - Read receipt deduplication to prevent duplicates
    - Real-time status updates to message senders
    - Batch processing for performance optimization
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.batch_size = 20  # Messages to process per batch
        self.deduplication_cache = {}  # In-memory cache for recent receipts
        self.cache_ttl_minutes = 5  # Cache TTL for deduplication
    
    async def mark_message_as_read(self, message_id: int, reader_user_id: int,
                                 read_timestamp: datetime = None) -> bool:
        """
        Mark a single message as read and send read receipt.
        
        Args:
            message_id: ID of the message being read
            reader_user_id: ID of the user who read the message
            read_timestamp: When the message was read (defaults to now)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from .models import Message
            from channels.db import database_sync_to_async
            
            if read_timestamp is None:
                read_timestamp = timezone.now()
            
            # Check deduplication cache
            cache_key = f"{message_id}_{reader_user_id}"
            if self._is_recently_processed(cache_key):
                logger.debug(f"Read receipt for message {message_id} already processed recently")
                return True
            
            @database_sync_to_async
            def mark_read():
                try:
                    with transaction.atomic():
                        # Get the message and verify recipient
                        message = Message.objects.select_for_update().get(
                            id=message_id,
                            recipient_id=reader_user_id
                        )
                        
                        # Skip if already read
                        if message.is_read:
                            return message, False
                        
                        # Use message status manager for integrated read receipt handling
                        from .message_status_manager import message_status_manager
                        success = message_status_manager.update_message_to_read_with_receipt(
                            message, read_timestamp
                        )
                        
                        return message, success
                
                except Message.DoesNotExist:
                    logger.warning(f"Message {message_id} not found or not for user {reader_user_id}")
                    return None, False
                except Exception as e:
                    logger.error(f"Error marking message {message_id} as read: {e}")
                    return None, False
            
            message, was_updated = await mark_read()
            
            if message and was_updated:
                # Add to deduplication cache
                self._add_to_cache(cache_key)
                
                # Send read receipt to sender
                await self._send_read_receipt_to_sender(message, read_timestamp)
                
                logger.info(f"Marked message {message_id} as read by user {reader_user_id}")
                return True
            
            return message is not None
        
        except Exception as e:
            logger.error(f"Error in mark_message_as_read: {e}")
            return False
    
    async def mark_multiple_messages_as_read(self, message_ids: List[int], 
                                           reader_user_id: int,
                                           read_timestamp: datetime = None) -> Dict:
        """
        Mark multiple messages as read in bulk (e.g., when user views chat).
        
        Args:
            message_ids: List of message IDs to mark as read
            reader_user_id: ID of the user who read the messages
            read_timestamp: When the messages were read (defaults to now)
            
        Returns:
            Dict with processing results
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            if read_timestamp is None:
                read_timestamp = timezone.now()
            
            if not message_ids:
                return {
                    'processed_count': 0,
                    'failed_count': 0,
                    'already_read_count': 0,
                    'message_ids': []
                }
            
            # Filter out recently processed messages
            filtered_ids = []
            for msg_id in message_ids:
                cache_key = f"{msg_id}_{reader_user_id}"
                if not self._is_recently_processed(cache_key):
                    filtered_ids.append(msg_id)
            
            if not filtered_ids:
                return {
                    'processed_count': 0,
                    'failed_count': 0,
                    'already_read_count': len(message_ids),
                    'message_ids': []
                }
            
            @sync_to_async
            def bulk_mark_read():
                try:
                    with transaction.atomic():
                        # Get unread messages for this user
                        messages = Message.objects.select_for_update().filter(
                            id__in=filtered_ids,
                            recipient_id=reader_user_id,
                            is_read=False
                        )
                        
                        updated_messages = []
                        from .message_status_manager import message_status_manager
                        
                        for message in messages:
                            # Use message status manager for integrated handling
                            success = message_status_manager.update_message_to_read_with_receipt(
                                message, read_timestamp
                            )
                            if success:
                                updated_messages.append(message)
                        
                        return updated_messages
                
                except Exception as e:
                    logger.error(f"Error in bulk mark read: {e}")
                    return []
            
            updated_messages = await bulk_mark_read()
            
            # Process results
            processed_count = len(updated_messages)
            already_read_count = len(message_ids) - len(filtered_ids)
            failed_count = len(filtered_ids) - processed_count
            
            # Add to deduplication cache
            for message in updated_messages:
                cache_key = f"{message.id}_{reader_user_id}"
                self._add_to_cache(cache_key)
            
            # Send read receipts to senders
            await self._send_bulk_read_receipts(updated_messages, read_timestamp)
            
            result = {
                'processed_count': processed_count,
                'failed_count': failed_count,
                'already_read_count': already_read_count,
                'message_ids': [msg.id for msg in updated_messages],
                'timestamp': read_timestamp.isoformat()
            }
            
            logger.info(f"Bulk marked {processed_count} messages as read for user {reader_user_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error in mark_multiple_messages_as_read: {e}")
            return {
                'error': str(e),
                'processed_count': 0,
                'failed_count': len(message_ids),
                'already_read_count': 0
            }
    
    async def mark_visible_messages_as_read(self, user_id: int, chat_partner_id: int,
                                          visible_message_ids: List[int] = None) -> Dict:
        """
        Mark all visible messages in a chat as read (when user opens/views chat).
        
        Args:
            user_id: ID of the user viewing the chat
            chat_partner_id: ID of the chat partner
            visible_message_ids: Optional list of specific message IDs visible
            
        Returns:
            Dict with processing results
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            @sync_to_async
            def get_unread_messages():
                query = Message.objects.filter(
                    recipient_id=user_id,
                    sender_id=chat_partner_id,
                    is_read=False
                )
                
                # If specific visible messages provided, filter to those
                if visible_message_ids:
                    query = query.filter(id__in=visible_message_ids)
                
                return list(query.values_list('id', flat=True))
            
            unread_message_ids = await get_unread_messages()
            
            if not unread_message_ids:
                return {
                    'processed_count': 0,
                    'failed_count': 0,
                    'already_read_count': 0,
                    'message_ids': []
                }
            
            # Use bulk processing
            result = await self.mark_multiple_messages_as_read(
                message_ids=unread_message_ids,
                reader_user_id=user_id
            )
            
            logger.info(f"Marked visible messages as read for user {user_id} in chat with {chat_partner_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error marking visible messages as read: {e}")
            return {
                'error': str(e),
                'processed_count': 0,
                'failed_count': 0
            }
    
    async def _send_read_receipt_to_sender(self, message, read_timestamp: datetime) -> bool:
        """Send read receipt notification to message sender."""
        try:
            if not self.channel_layer:
                return False
            
            # Create read receipt payload
            receipt_payload = {
                'type': 'read_receipt_update',
                'message': {
                    'type': 'read_receipt',
                    'message_id': message.id,
                    'client_id': message.client_id,
                    'read_by': message.recipient.username,
                    'read_by_id': message.recipient.id,
                    'read_at': read_timestamp.isoformat(),
                    'status': 'read',
                    'status_icon': message.get_status_icon()
                }
            }
            
            # Send to sender's user group
            sender_group = f'user_{message.sender.id}'
            await self.channel_layer.group_send(sender_group, receipt_payload)
            
            # Also send to the chat room for real-time updates
            a, b = sorted([message.sender.id, message.recipient.id])
            chat_room = f'chat_{a}_{b}'
            await self.channel_layer.group_send(chat_room, receipt_payload)
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending read receipt to sender: {e}")
            return False
    
    async def _send_bulk_read_receipts(self, messages: List, read_timestamp: datetime) -> int:
        """Send read receipts for multiple messages, grouped by sender."""
        try:
            if not self.channel_layer or not messages:
                return 0
            
            # Group messages by sender
            messages_by_sender = {}
            for message in messages:
                sender_id = message.sender.id
                if sender_id not in messages_by_sender:
                    messages_by_sender[sender_id] = []
                messages_by_sender[sender_id].append(message)
            
            sent_count = 0
            
            # Send bulk receipts to each sender
            for sender_id, sender_messages in messages_by_sender.items():
                try:
                    # Create bulk receipt payload
                    receipt_payload = {
                        'type': 'bulk_read_receipts',
                        'message': {
                            'type': 'bulk_read_receipts',
                            'read_by': sender_messages[0].recipient.username,
                            'read_by_id': sender_messages[0].recipient.id,
                            'read_at': read_timestamp.isoformat(),
                            'message_count': len(sender_messages),
                            'messages': [
                                {
                                    'message_id': msg.id,
                                    'client_id': msg.client_id,
                                    'status': 'read',
                                    'status_icon': msg.get_status_icon()
                                }
                                for msg in sender_messages
                            ]
                        }
                    }
                    
                    # Send to sender's user group
                    sender_group = f'user_{sender_id}'
                    await self.channel_layer.group_send(sender_group, receipt_payload)
                    
                    # Send to chat rooms
                    for message in sender_messages:
                        a, b = sorted([message.sender.id, message.recipient.id])
                        chat_room = f'chat_{a}_{b}'
                        await self.channel_layer.group_send(chat_room, {
                            'type': 'read_receipt_update',
                            'message': {
                                'type': 'read_receipt',
                                'message_id': message.id,
                                'client_id': message.client_id,
                                'read_by': message.recipient.username,
                                'read_by_id': message.recipient.id,
                                'read_at': read_timestamp.isoformat(),
                                'status': 'read',
                                'status_icon': message.get_status_icon()
                            }
                        })
                    
                    sent_count += len(sender_messages)
                
                except Exception as e:
                    logger.error(f"Error sending bulk receipts to sender {sender_id}: {e}")
            
            return sent_count
        
        except Exception as e:
            logger.error(f"Error sending bulk read receipts: {e}")
            return 0
    
    def _is_recently_processed(self, cache_key: str) -> bool:
        """Check if a read receipt was recently processed (deduplication)."""
        try:
            if cache_key in self.deduplication_cache:
                cached_time = self.deduplication_cache[cache_key]
                if timezone.now() - cached_time < timedelta(minutes=self.cache_ttl_minutes):
                    return True
                else:
                    # Remove expired entry
                    del self.deduplication_cache[cache_key]
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking deduplication cache: {e}")
            return False
    
    def _add_to_cache(self, cache_key: str) -> None:
        """Add entry to deduplication cache."""
        try:
            self.deduplication_cache[cache_key] = timezone.now()
            
            # Clean up old entries periodically
            if len(self.deduplication_cache) > 1000:
                self._cleanup_cache()
        
        except Exception as e:
            logger.error(f"Error adding to deduplication cache: {e}")
    
    def _cleanup_cache(self) -> None:
        """Clean up expired entries from deduplication cache."""
        try:
            cutoff_time = timezone.now() - timedelta(minutes=self.cache_ttl_minutes)
            expired_keys = [
                key for key, timestamp in self.deduplication_cache.items()
                if timestamp < cutoff_time
            ]
            
            for key in expired_keys:
                del self.deduplication_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    async def get_read_receipt_statistics(self, user_id: int = None) -> Dict:
        """
        Get read receipt statistics for monitoring.
        
        Args:
            user_id: Optional user ID to filter statistics
            
        Returns:
            Dict with read receipt statistics
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            @sync_to_async
            def get_stats():
                base_query = Message.objects.all()
                if user_id:
                    base_query = base_query.filter(
                        Q(sender_id=user_id) | Q(recipient_id=user_id)
                    )
                
                stats = {
                    'total_messages': base_query.count(),
                    'read_messages': base_query.filter(is_read=True).count(),
                    'unread_messages': base_query.filter(is_read=False).count(),
                    'messages_with_read_receipts': base_query.filter(
                        is_read=True,
                        read_at__isnull=False
                    ).count(),
                    'cache_size': len(self.deduplication_cache),
                    'timestamp': timezone.now().isoformat()
                }
                
                # Calculate read rate
                if stats['total_messages'] > 0:
                    stats['read_rate'] = stats['read_messages'] / stats['total_messages']
                else:
                    stats['read_rate'] = 0.0
                
                return stats
            
            return await get_stats()
        
        except Exception as e:
            logger.error(f"Error getting read receipt statistics: {e}")
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    async def process_delayed_read_receipts(self) -> Dict:
        """
        Process any delayed read receipts (cleanup/recovery operation).
        
        Returns:
            Dict with processing results
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            @sync_to_async
            def get_delayed_receipts():
                # Find messages that should have read receipts but don't
                # (messages marked as read but without read_at timestamp)
                return list(
                    Message.objects.filter(
                        is_read=True,
                        read_at__isnull=True
                    ).select_related('sender', 'recipient')[:self.batch_size]
                )
            
            delayed_messages = await get_delayed_receipts()
            
            if not delayed_messages:
                return {
                    'processed_count': 0,
                    'message': 'No delayed read receipts found'
                }
            
            processed_count = 0
            
            for message in delayed_messages:
                try:
                    # Set read timestamp to now
                    read_timestamp = timezone.now()
                    
                    # Update message
                    from django.db import sync_to_async
                    
                    @sync_to_async
                    def update_message():
                        message.read_at = read_timestamp
                        message.save(update_fields=['read_at'])
                    
                    await update_message()
                    
                    # Send read receipt
                    await self._send_read_receipt_to_sender(message, read_timestamp)
                    
                    processed_count += 1
                
                except Exception as e:
                    logger.error(f"Error processing delayed receipt for message {message.id}: {e}")
            
            result = {
                'processed_count': processed_count,
                'total_found': len(delayed_messages),
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Processed {processed_count} delayed read receipts")
            return result
        
        except Exception as e:
            logger.error(f"Error processing delayed read receipts: {e}")
            return {
                'error': str(e),
                'processed_count': 0
            }


# Global instance
read_receipt_manager = ReadReceiptManager()
"""
Message Synchronization Manager for WhatsApp-like Messaging System

Handles message synchronization on reconnection, missed message detection,
chronological message ordering, and queue processing for offline messages.

Requirements: 6.3, 6.4
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

User = get_user_model()
logger = logging.getLogger(__name__)


class MessageSyncManager:
    """
    Manages message synchronization when connections are restored.
    
    Features:
    - Missed message detection and retrieval
    - Chronological message ordering
    - Queue processing for offline messages
    - Duplicate message prevention
    - Status synchronization
    """
    
    def __init__(self):
        self.sync_batch_size = 50  # Messages to sync per batch
        self.max_sync_age_days = 7  # Maximum age of messages to sync
    
    async def synchronize_messages_on_reconnection(self, user_id: int, 
                                                 last_disconnect_time: datetime,
                                                 connection_id: str) -> Dict:
        """
        Synchronize messages when a user reconnects.
        
        Args:
            user_id: User ID who reconnected
            last_disconnect_time: When the user was last disconnected
            connection_id: Connection identifier for status updates
            
        Returns:
            Dict with synchronization results
        """
        try:
            logger.info(f"Starting message sync for user {user_id} from {last_disconnect_time}")
            
            # Get missed incoming messages
            missed_incoming = await self._get_missed_incoming_messages(
                user_id, last_disconnect_time
            )
            
            # Get pending outgoing messages
            pending_outgoing = await self._get_pending_outgoing_messages(user_id)
            
            # Get status updates for existing messages
            status_updates = await self._get_message_status_updates(
                user_id, last_disconnect_time
            )
            
            # Order all messages chronologically
            ordered_messages = self._order_messages_chronologically(
                missed_incoming, pending_outgoing, status_updates
            )
            
            # Prepare sync payload
            sync_result = {
                'connection_id': connection_id,
                'user_id': user_id,
                'sync_timestamp': timezone.now().isoformat(),
                'missed_incoming_count': len(missed_incoming),
                'pending_outgoing_count': len(pending_outgoing),
                'status_updates_count': len(status_updates),
                'total_messages': len(ordered_messages),
                'messages': ordered_messages[:self.sync_batch_size],  # First batch
                'has_more': len(ordered_messages) > self.sync_batch_size,
                'next_batch_offset': self.sync_batch_size if len(ordered_messages) > self.sync_batch_size else None
            }
            
            logger.info(f"Message sync completed for user {user_id}: "
                       f"{len(missed_incoming)} missed, {len(pending_outgoing)} pending, "
                       f"{len(status_updates)} status updates")
            
            return sync_result
            
        except Exception as e:
            logger.error(f"Error synchronizing messages for user {user_id}: {e}")
            return {
                'connection_id': connection_id,
                'user_id': user_id,
                'error': str(e),
                'sync_timestamp': timezone.now().isoformat(),
                'messages': []
            }
    
    async def _get_missed_incoming_messages(self, user_id: int, 
                                          since_time: datetime) -> List[Dict]:
        """
        Get messages that were received while user was offline.
        
        Args:
            user_id: User ID
            since_time: Time since when to get messages
            
        Returns:
            List of missed message dictionaries
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            # Get messages received while offline
            @sync_to_async
            def get_messages():
                cutoff_time = timezone.now() - timedelta(days=self.max_sync_age_days)
                effective_since = max(since_time, cutoff_time)
                
                messages = Message.objects.filter(
                    recipient_id=user_id,
                    created_at__gte=effective_since
                ).select_related('sender').order_by('created_at')
                
                return list(messages)
            
            messages = await get_messages()
            
            # Convert to sync format
            missed_messages = []
            for msg in messages:
                missed_messages.append({
                    'type': 'incoming_message',
                    'id': msg.id,
                    'sender': msg.sender.username,
                    'sender_id': msg.sender.id,
                    'recipient': msg.recipient.username,
                    'recipient_id': msg.recipient.id,
                    'content': msg.content,
                    'status': msg.status,
                    'client_id': msg.client_id,
                    'created_at': msg.created_at.isoformat(),
                    'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
                    'delivered_at': msg.delivered_at.isoformat() if msg.delivered_at else None,
                    'read_at': msg.read_at.isoformat() if msg.read_at else None,
                    'is_read': msg.is_read,
                    'status_icon': msg.get_status_icon(),
                    'sync_priority': 1  # High priority for incoming messages
                })
            
            return missed_messages
            
        except Exception as e:
            logger.error(f"Error getting missed incoming messages: {e}")
            return []
    
    async def _get_pending_outgoing_messages(self, user_id: int) -> List[Dict]:
        """
        Get outgoing messages that need to be sent or retried.
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending outgoing message dictionaries
        """
        try:
            from .models import QueuedMessage
            from django.db import sync_to_async
            
            @sync_to_async
            def get_queued_messages():
                # Get messages that are queued for sending or retry
                messages = QueuedMessage.objects.filter(
                    sender_id=user_id,
                    is_processed=False,
                    queue_type__in=['outgoing', 'retry']
                ).select_related('recipient').order_by('created_at')
                
                return list(messages)
            
            queued_messages = await get_queued_messages()
            
            # Convert to sync format
            pending_messages = []
            for msg in queued_messages:
                pending_messages.append({
                    'type': 'outgoing_message',
                    'id': msg.id,
                    'sender': msg.sender.username,
                    'sender_id': msg.sender.id,
                    'recipient': msg.recipient.username,
                    'recipient_id': msg.recipient.id,
                    'content': msg.content,
                    'queue_type': msg.queue_type,
                    'retry_count': msg.retry_count,
                    'max_retries': msg.max_retries,
                    'created_at': msg.created_at.isoformat(),
                    'next_retry_at': msg.next_retry_at.isoformat() if msg.next_retry_at else None,
                    'last_error': msg.last_error,
                    'sync_priority': 2  # Medium priority for outgoing messages
                })
            
            return pending_messages
            
        except Exception as e:
            logger.error(f"Error getting pending outgoing messages: {e}")
            return []
    
    async def _get_message_status_updates(self, user_id: int, 
                                        since_time: datetime) -> List[Dict]:
        """
        Get status updates for messages that occurred while offline.
        
        Args:
            user_id: User ID
            since_time: Time since when to get status updates
            
        Returns:
            List of status update dictionaries
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            @sync_to_async
            def get_status_updates():
                # Get messages sent by user that had status changes
                cutoff_time = timezone.now() - timedelta(days=self.max_sync_age_days)
                effective_since = max(since_time, cutoff_time)
                
                messages = Message.objects.filter(
                    sender_id=user_id
                ).filter(
                    Q(delivered_at__gte=effective_since) | Q(read_at__gte=effective_since)
                ).select_related('recipient').order_by('created_at')
                
                return list(messages)
            
            messages = await get_status_updates()
            
            # Convert to sync format
            status_updates = []
            for msg in messages:
                # Determine what status updates occurred
                updates = []
                
                if msg.delivered_at and msg.delivered_at >= since_time:
                    updates.append({
                        'status': 'delivered',
                        'timestamp': msg.delivered_at.isoformat()
                    })
                
                if msg.read_at and msg.read_at >= since_time:
                    updates.append({
                        'status': 'read',
                        'timestamp': msg.read_at.isoformat()
                    })
                
                if updates:
                    status_updates.append({
                        'type': 'status_update',
                        'message_id': msg.id,
                        'client_id': msg.client_id,
                        'recipient': msg.recipient.username,
                        'recipient_id': msg.recipient.id,
                        'current_status': msg.status,
                        'status_icon': msg.get_status_icon(),
                        'updates': updates,
                        'sync_priority': 3  # Lower priority for status updates
                    })
            
            return status_updates
            
        except Exception as e:
            logger.error(f"Error getting message status updates: {e}")
            return []
    
    def _order_messages_chronologically(self, missed_incoming: List[Dict],
                                      pending_outgoing: List[Dict],
                                      status_updates: List[Dict]) -> List[Dict]:
        """
        Order all messages and updates chronologically.
        
        Args:
            missed_incoming: List of missed incoming messages
            pending_outgoing: List of pending outgoing messages
            status_updates: List of status updates
            
        Returns:
            List of all messages ordered chronologically
        """
        all_messages = []
        
        # Add all messages with their timestamps
        for msg in missed_incoming:
            msg['sort_timestamp'] = msg['created_at']
            all_messages.append(msg)
        
        for msg in pending_outgoing:
            msg['sort_timestamp'] = msg['created_at']
            all_messages.append(msg)
        
        for update in status_updates:
            # Use the earliest update timestamp for sorting
            if update['updates']:
                earliest_update = min(update['updates'], key=lambda x: x['timestamp'])
                update['sort_timestamp'] = earliest_update['timestamp']
                all_messages.append(update)
        
        # Sort by timestamp, then by priority
        all_messages.sort(key=lambda x: (x['sort_timestamp'], x.get('sync_priority', 999)))
        
        return all_messages
    
    async def get_next_sync_batch(self, user_id: int, offset: int, 
                                batch_size: int = None) -> Dict:
        """
        Get the next batch of messages for synchronization.
        
        Args:
            user_id: User ID
            offset: Offset for pagination
            batch_size: Number of messages to return
            
        Returns:
            Dict with batch of messages
        """
        if batch_size is None:
            batch_size = self.sync_batch_size
        
        try:
            # This would typically be cached from the initial sync
            # For now, we'll return an empty batch
            return {
                'user_id': user_id,
                'offset': offset,
                'batch_size': batch_size,
                'messages': [],
                'has_more': False,
                'next_batch_offset': None
            }
            
        except Exception as e:
            logger.error(f"Error getting next sync batch: {e}")
            return {
                'user_id': user_id,
                'offset': offset,
                'error': str(e),
                'messages': []
            }
    
    async def mark_messages_as_synchronized(self, user_id: int, 
                                          message_ids: List[int]) -> bool:
        """
        Mark messages as synchronized to prevent duplicate delivery.
        
        Args:
            user_id: User ID
            message_ids: List of message IDs that were synchronized
            
        Returns:
            bool: True if successful
        """
        try:
            from .models import Message
            from django.db import sync_to_async
            
            @sync_to_async
            def mark_synchronized():
                with transaction.atomic():
                    # Update messages to mark them as synchronized
                    Message.objects.filter(
                        id__in=message_ids
                    ).filter(
                        Q(sender_id=user_id) | Q(recipient_id=user_id)
                    ).update(
                        # Add a synchronized timestamp if the model supports it
                        # For now, we'll just ensure they're marked as delivered
                        delivered_at=timezone.now()
                    )
                    return True
            
            success = await mark_synchronized()
            
            if success:
                logger.info(f"Marked {len(message_ids)} messages as synchronized for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error marking messages as synchronized: {e}")
            return False
    
    async def process_offline_message_queue(self, user_id: int) -> Dict:
        """
        Process messages that were queued while user was offline.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with processing results
        """
        try:
            from .models import QueuedMessage
            from django.db import sync_to_async
            
            @sync_to_async
            def get_and_process_queue():
                with transaction.atomic():
                    # Get queued messages for this user
                    queued_messages = QueuedMessage.objects.filter(
                        Q(sender_id=user_id) | Q(recipient_id=user_id),
                        is_processed=False,
                        queue_type='incoming'
                    ).order_by('created_at')
                    
                    processed_count = 0
                    failed_count = 0
                    
                    for queued_msg in queued_messages:
                        try:
                            # Create actual message from queued message
                            from .models import Message
                            
                            # Check if message already exists (prevent duplicates)
                            existing = Message.objects.filter(
                                sender=queued_msg.sender,
                                recipient=queued_msg.recipient,
                                content=queued_msg.content,
                                created_at=queued_msg.created_at
                            ).first()
                            
                            if not existing:
                                Message.objects.create(
                                    sender=queued_msg.sender,
                                    recipient=queued_msg.recipient,
                                    content=queued_msg.content,
                                    status='delivered',  # Mark as delivered since user is now online
                                    delivered_at=timezone.now()
                                )
                            
                            # Mark queued message as processed
                            queued_msg.is_processed = True
                            queued_msg.save()
                            
                            processed_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing queued message {queued_msg.id}: {e}")
                            failed_count += 1
                    
                    return processed_count, failed_count
            
            processed, failed = await get_and_process_queue()
            
            result = {
                'user_id': user_id,
                'processed_count': processed,
                'failed_count': failed,
                'total_count': processed + failed,
                'success': failed == 0,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Processed offline queue for user {user_id}: "
                       f"{processed} processed, {failed} failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing offline message queue: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'processed_count': 0,
                'failed_count': 0
            }
    
    async def cleanup_old_sync_data(self, days_old: int = 7) -> int:
        """
        Clean up old synchronization data.
        
        Args:
            days_old: Age in days of data to clean up
            
        Returns:
            Number of records cleaned up
        """
        try:
            from .models import QueuedMessage
            from django.db import sync_to_async
            
            @sync_to_async
            def cleanup():
                cutoff_date = timezone.now() - timedelta(days=days_old)
                
                # Clean up old processed queued messages
                deleted_count, _ = QueuedMessage.objects.filter(
                    is_processed=True,
                    created_at__lt=cutoff_date
                ).delete()
                
                return deleted_count
            
            cleaned_count = await cleanup()
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old sync records")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old sync data: {e}")
            return 0


# Global instance
message_sync_manager = MessageSyncManager()
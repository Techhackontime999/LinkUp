"""
Message Status Manager for WhatsApp-like messaging system.
Handles message status tracking, broadcasting, and icon generation.
"""

import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Message

logger = logging.getLogger(__name__)


class MessageStatusManager:
    """Manages message status transitions and real-time broadcasting."""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def update_message_status(self, message: Message, new_status: str, 
                            error_message: Optional[str] = None,
                            read_timestamp: Optional[Any] = None) -> bool:
        """
        Update message status and broadcast to relevant users.
        Enhanced to work with read receipt system.
        
        Args:
            message: Message instance to update
            new_status: New status ('sent', 'delivered', 'read', 'failed')
            error_message: Optional error message for failed status
            read_timestamp: Optional timestamp for read status
            
        Returns:
            bool: True if status was updated successfully
        """
        try:
            with transaction.atomic():
                old_status = message.status
                
                # Update status based on new_status
                if new_status == 'sent':
                    message.mark_as_sent()
                elif new_status == 'delivered':
                    message.mark_as_delivered()
                elif new_status == 'read':
                    if read_timestamp:
                        message.mark_as_read(read_timestamp)
                    else:
                        message.mark_as_read()
                elif new_status == 'failed':
                    message.mark_as_failed(error_message)
                else:
                    logger.warning(f"Invalid status transition: {old_status} -> {new_status}")
                    return False
                
                # Broadcast status update if status actually changed
                if old_status != message.status:
                    self._broadcast_status_update(message, old_status)
                    logger.info(f"Message {message.id} status updated: {old_status} -> {message.status}")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update message {message.id} status: {e}")
            return False
    
    def update_message_to_read_with_receipt(self, message: Message, 
                                          read_timestamp: Optional[Any] = None) -> bool:
        """
        Update message to read status with proper read receipt integration.
        
        Args:
            message: Message instance to mark as read
            read_timestamp: When the message was read
            
        Returns:
            bool: True if successful
        """
        try:
            with transaction.atomic():
                old_status = message.status
                
                # Only update if not already read
                if message.is_read:
                    return True
                
                # Mark as read with timestamp
                if read_timestamp:
                    message.mark_as_read(read_timestamp)
                else:
                    message.mark_as_read()
                
                # Broadcast read receipt update
                self._broadcast_read_receipt_update(message, read_timestamp or timezone.now())
                
                logger.info(f"Message {message.id} marked as read with receipt")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update message {message.id} to read with receipt: {e}")
            return False
    
    def _broadcast_read_receipt_update(self, message: Message, read_timestamp: Any):
        """Broadcast read receipt update specifically."""
        if not self.channel_layer:
            return
        
        try:
            # Create read receipt payload
            receipt_payload = {
                'type': 'read_receipt_update',
                'message': {
                    'type': 'read_receipt',
                    'message_id': message.id,
                    'client_id': message.client_id,
                    'read_by': message.recipient.username,
                    'read_by_id': message.recipient.id,
                    'read_at': read_timestamp.isoformat() if hasattr(read_timestamp, 'isoformat') else str(read_timestamp),
                    'status': 'read',
                    'status_icon': message.get_status_icon(),
                    'sender': message.sender.username,
                    'recipient': message.recipient.username
                }
            }
            
            # Send to sender for read receipt notification
            sender_group = f'user_{message.sender.id}'
            async_to_sync(self.channel_layer.group_send)(sender_group, receipt_payload)
            
            # Send to chat room for real-time updates
            a, b = sorted([message.sender.id, message.recipient.id])
            chat_room = f'chat_{a}_{b}'
            async_to_sync(self.channel_layer.group_send)(chat_room, receipt_payload)
            
            logger.debug(f"Broadcasted read receipt for message {message.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast read receipt for message {message.id}: {e}")
    
    def _broadcast_status_update(self, message: Message, old_status: str):
        """Broadcast message status update to relevant users via WebSocket."""
        if not self.channel_layer:
            logger.warning("Channel layer not available for status broadcasting")
            return
        
        try:
            # Create status update payload
            status_payload = {
                'type': 'message_status_update',
                'message_id': message.id,
                'old_status': old_status,
                'new_status': message.status,
                'status_icon': message.get_status_icon(),
                'timestamp': timezone.now().isoformat(),
                'sender': message.sender.username,
                'recipient': message.recipient.username
            }
            
            # Add relevant timestamps
            if message.status == 'sent' and message.sent_at:
                status_payload['sent_at'] = message.sent_at.isoformat()
            elif message.status == 'delivered' and message.delivered_at:
                status_payload['delivered_at'] = message.delivered_at.isoformat()
            elif message.status == 'read' and message.read_at:
                status_payload['read_at'] = message.read_at.isoformat()
            elif message.status == 'failed':
                status_payload['error_message'] = message.last_error
                status_payload['retry_count'] = message.retry_count
            
            # Broadcast to sender (for delivery/read receipts)
            sender_group = f'user_{message.sender.id}'
            async_to_sync(self.channel_layer.group_send)(
                sender_group,
                {
                    'type': 'message_status_update',
                    'message': status_payload
                }
            )
            
            # Broadcast to recipient (for message updates)
            recipient_group = f'user_{message.recipient.id}'
            async_to_sync(self.channel_layer.group_send)(
                recipient_group,
                {
                    'type': 'message_status_update', 
                    'message': status_payload
                }
            )
            
            logger.debug(f"Broadcasted status update for message {message.id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast status update for message {message.id}: {e}")
    
    def get_status_icon_html(self, message: Message) -> str:
        """
        Generate HTML for message status icon (WhatsApp-style checkmarks).
        
        Args:
            message: Message instance
            
        Returns:
            str: HTML string for status icon
        """
        icon_templates = {
            'pending': '''
                <svg class="w-4 h-4 text-gray-400 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                </svg>
            ''',
            'sent': '''
                <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                </svg>
            ''',
            'delivered': '''
                <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                    <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                </svg>
            ''',
            'read': '''
                <svg class="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M0 11l2-2 5 5L18 3l2 2L7 18z"/>
                    <path d="M7 11l2-2 5 5L18 3l2 2L7 18z" transform="translate(3, 0)"/>
                </svg>
            ''',
            'failed': '''
                <svg class="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
            '''
        }
        
        return icon_templates.get(message.status, icon_templates['pending']).strip()
    
    def bulk_update_status(self, message_ids: list, new_status: str) -> Dict[str, Any]:
        """
        Bulk update status for multiple messages.
        
        Args:
            message_ids: List of message IDs to update
            new_status: New status to apply
            
        Returns:
            dict: Results with success count and errors
        """
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        try:
            messages = Message.objects.filter(id__in=message_ids)
            
            for message in messages:
                try:
                    if self.update_message_status(message, new_status):
                        results['success_count'] += 1
                    else:
                        results['error_count'] += 1
                        results['errors'].append(f"Failed to update message {message.id}")
                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append(f"Error updating message {message.id}: {str(e)}")
            
            logger.info(f"Bulk status update completed: {results['success_count']} success, {results['error_count']} errors")
            
        except Exception as e:
            logger.error(f"Bulk status update failed: {e}")
            results['error_count'] = len(message_ids)
            results['errors'].append(f"Bulk operation failed: {str(e)}")
        
        return results
    
    def get_conversation_status_summary(self, user1_id: int, user2_id: int) -> Dict[str, Any]:
        """
        Get status summary for a conversation between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            dict: Status summary with counts and latest message info
        """
        try:
            from django.db.models import Q, Count
            
            # Get all messages in the conversation
            messages = Message.objects.filter(
                (Q(sender_id=user1_id) & Q(recipient_id=user2_id)) |
                (Q(sender_id=user2_id) & Q(recipient_id=user1_id))
            )
            
            # Count messages by status
            status_counts = messages.values('status').annotate(count=Count('id'))
            status_summary = {item['status']: item['count'] for item in status_counts}
            
            # Get latest message
            latest_message = messages.order_by('-created_at').first()
            
            # Count unread messages for each user
            unread_for_user1 = messages.filter(
                recipient_id=user1_id, 
                is_read=False
            ).count()
            
            unread_for_user2 = messages.filter(
                recipient_id=user2_id,
                is_read=False
            ).count()
            
            return {
                'total_messages': messages.count(),
                'status_counts': status_summary,
                'latest_message': {
                    'id': latest_message.id if latest_message else None,
                    'status': latest_message.status if latest_message else None,
                    'created_at': latest_message.created_at.isoformat() if latest_message else None
                },
                'unread_counts': {
                    user1_id: unread_for_user1,
                    user2_id: unread_for_user2
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation status summary: {e}")
            return {
                'total_messages': 0,
                'status_counts': {},
                'latest_message': None,
                'unread_counts': {user1_id: 0, user2_id: 0},
                'error': str(e)
            }
    
    def cleanup_failed_messages(self, max_age_hours: int = 24) -> int:
        """
        Clean up old failed messages that exceed retry limits.
        
        Args:
            max_age_hours: Maximum age in hours for failed messages
            
        Returns:
            int: Number of messages cleaned up
        """
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
            
            # Find failed messages that are old and have exceeded retry limits
            failed_messages = Message.objects.filter(
                status='failed',
                failed_at__lt=cutoff_time,
                retry_count__gte=3  # Max retries exceeded
            )
            
            count = failed_messages.count()
            
            # Log the failed messages before deletion (for debugging)
            for msg in failed_messages[:10]:  # Log first 10 for debugging
                logger.warning(f"Cleaning up failed message {msg.id}: {msg.last_error}")
            
            # Delete the failed messages
            failed_messages.delete()
            
            logger.info(f"Cleaned up {count} failed messages older than {max_age_hours} hours")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup failed messages: {e}")
            return 0


# Global instance
message_status_manager = MessageStatusManager()
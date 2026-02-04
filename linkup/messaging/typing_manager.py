"""
Typing Status Manager for real-time typing indicators.
Handles typing status tracking, debouncing, and cleanup.
"""

import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import TypingStatus
from datetime import timedelta

logger = logging.getLogger(__name__)


class TypingManager:
    """Manages typing indicators with debouncing and cleanup."""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def update_typing_status(self, user, chat_partner, is_typing: bool) -> bool:
        """
        Update typing status for a user in a specific chat.
        
        Args:
            user: User who is typing
            chat_partner: User they are chatting with
            is_typing: Whether user is currently typing
            
        Returns:
            bool: True if status was updated successfully
        """
        try:
            with transaction.atomic():
                typing_status, created = TypingStatus.objects.get_or_create(
                    user=user,
                    chat_partner=chat_partner,
                    defaults={'is_typing': is_typing}
                )
                
                # Only update if status actually changed
                if typing_status.is_typing != is_typing:
                    typing_status.is_typing = is_typing
                    typing_status.last_updated = timezone.now()
                    typing_status.save(update_fields=['is_typing', 'last_updated'])
                    
                    # Broadcast typing status update
                    self._broadcast_typing_status(user, chat_partner, is_typing)
                    
                    logger.debug(f"Updated typing status: {user.username} -> {chat_partner.username}: {is_typing}")
                    return True
                else:
                    # Status unchanged, just update timestamp for debouncing
                    typing_status.last_updated = timezone.now()
                    typing_status.save(update_fields=['last_updated'])
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update typing status: {e}")
            return False
    
    def _broadcast_typing_status(self, user, chat_partner, is_typing: bool):
        """Broadcast typing status update via WebSocket."""
        if not self.channel_layer:
            logger.warning("Channel layer not available for typing status broadcasting")
            return
        
        try:
            # Create room name (same logic as ChatConsumer)
            a, b = sorted([user.id, chat_partner.id])
            room_group_name = f'chat_{a}_{b}'
            
            # Create typing status payload
            typing_payload = {
                'type': 'typing_indicator',
                'username': user.username,
                'is_typing': is_typing,
                'timestamp': timezone.now().isoformat()
            }
            
            # Broadcast to chat room
            async_to_sync(self.channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': user.username,
                    'is_typing': is_typing
                }
            )
            
            logger.debug(f"Broadcasted typing status: {user.username} -> {is_typing}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast typing status: {e}")
    
    def get_typing_users_for_chat(self, user, chat_partner) -> list:
        """
        Get list of users currently typing in a chat.
        
        Args:
            user: Current user
            chat_partner: Their chat partner
            
        Returns:
            list: List of usernames currently typing
        """
        try:
            # Clean up stale statuses first
            self.cleanup_stale_typing_statuses()
            
            # Get active typing statuses for this chat
            typing_statuses = TypingStatus.objects.filter(
                chat_partner=user,  # People typing TO the current user
                is_typing=True
            ).select_related('user')
            
            typing_users = [status.user.username for status in typing_statuses]
            
            return typing_users
            
        except Exception as e:
            logger.error(f"Failed to get typing users: {e}")
            return []
    
    def cleanup_stale_typing_statuses(self, timeout_seconds: int = 5) -> int:
        """
        Clean up stale typing indicators.
        
        Args:
            timeout_seconds: Timeout for considering status stale
            
        Returns:
            int: Number of stale statuses cleaned up
        """
        try:
            cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)
            
            # Find stale typing statuses
            stale_statuses = TypingStatus.objects.filter(
                is_typing=True,
                last_updated__lt=cutoff_time
            ).select_related('user', 'chat_partner')
            
            # Broadcast stop typing for each stale status
            for status in stale_statuses:
                self._broadcast_typing_status(
                    status.user, 
                    status.chat_partner, 
                    False
                )
            
            # Update stale statuses to not typing
            count = stale_statuses.update(is_typing=False)
            
            if count > 0:
                logger.info(f"Cleaned up {count} stale typing statuses")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale typing statuses: {e}")
            return 0
    
    def stop_all_typing_for_user(self, user) -> int:
        """
        Stop all typing indicators for a user (e.g., when they disconnect).
        
        Args:
            user: User to stop typing for
            
        Returns:
            int: Number of typing statuses stopped
        """
        try:
            # Get all active typing statuses for this user
            active_statuses = TypingStatus.objects.filter(
                user=user,
                is_typing=True
            ).select_related('chat_partner')
            
            # Broadcast stop typing for each
            for status in active_statuses:
                self._broadcast_typing_status(
                    status.user,
                    status.chat_partner,
                    False
                )
            
            # Update all to not typing
            count = active_statuses.update(is_typing=False)
            
            if count > 0:
                logger.info(f"Stopped {count} typing indicators for user {user.username}")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to stop typing for user {user.username}: {e}")
            return 0
    
    def get_typing_summary_for_user(self, user) -> Dict[str, Any]:
        """
        Get comprehensive typing status summary for a user.
        
        Args:
            user: User to get summary for
            
        Returns:
            dict: Summary with typing counts and active chats
        """
        try:
            # Clean up stale statuses first
            self.cleanup_stale_typing_statuses()
            
            # Get users typing TO this user
            incoming_typing = TypingStatus.objects.filter(
                chat_partner=user,
                is_typing=True
            ).select_related('user')
            
            # Get users this user is typing TO
            outgoing_typing = TypingStatus.objects.filter(
                user=user,
                is_typing=True
            ).select_related('chat_partner')
            
            summary = {
                'incoming_typing': [
                    {
                        'username': status.user.username,
                        'started_at': status.started_at.isoformat(),
                        'last_updated': status.last_updated.isoformat()
                    }
                    for status in incoming_typing
                ],
                'outgoing_typing': [
                    {
                        'username': status.chat_partner.username,
                        'started_at': status.started_at.isoformat(),
                        'last_updated': status.last_updated.isoformat()
                    }
                    for status in outgoing_typing
                ],
                'total_incoming': incoming_typing.count(),
                'total_outgoing': outgoing_typing.count()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get typing summary for user {user.username}: {e}")
            return {
                'incoming_typing': [],
                'outgoing_typing': [],
                'total_incoming': 0,
                'total_outgoing': 0,
                'error': str(e)
            }
    
    def debounce_typing_stop(self, user, chat_partner, delay_seconds: int = 1):
        """
        Schedule automatic typing stop after delay (debouncing).
        This would typically be implemented with Celery or similar task queue.
        For now, we rely on frontend timeout and cleanup.
        
        Args:
            user: User who is typing
            chat_partner: User they are chatting with
            delay_seconds: Delay before auto-stop
        """
        # This is a placeholder for future implementation with task queue
        # For now, we rely on:
        # 1. Frontend sending stop typing after timeout
        # 2. Periodic cleanup of stale statuses
        # 3. WebSocket disconnect handling
        
        logger.debug(f"Typing debounce scheduled for {user.username} -> {chat_partner.username}")
        pass


# Global instance
typing_manager = TypingManager()
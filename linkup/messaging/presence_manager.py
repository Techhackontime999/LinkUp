"""
User Presence Manager for real-time online/offline status tracking.
Handles connection tracking, heartbeat monitoring, and status broadcasting.
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserStatus
from datetime import timedelta

logger = logging.getLogger(__name__)


class PresenceManager:
    """Manages user presence with connection tracking and heartbeat monitoring."""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def user_connected(self, user, connection_info: Optional[Dict] = None) -> str:
        """
        Handle user connection event.
        
        Args:
            user: User who connected
            connection_info: Optional connection metadata
            
        Returns:
            str: Connection ID for tracking
        """
        try:
            connection_id = f"conn_{user.id}_{uuid.uuid4().hex[:8]}"
            
            with transaction.atomic():
                status, created = UserStatus.objects.get_or_create(
                    user=user,
                    defaults={
                        'is_online': True,
                        'active_connections': 1,
                        'connection_id': connection_id,
                        'device_info': connection_info or {}
                    }
                )
                
                if not created:
                    # Update existing status
                    was_offline = not status.is_online
                    status.increment_connections(connection_id)
                    
                    # Broadcast status change if user was offline
                    if was_offline:
                        self._broadcast_presence_update(user, True)
                        logger.info(f"User {user.username} came online")
                else:
                    # New user status created
                    self._broadcast_presence_update(user, True)
                    logger.info(f"User {user.username} connected for first time")
                
                return connection_id
                
        except Exception as e:
            logger.error(f"Failed to handle user connection for {user.username}: {e}")
            return f"conn_{user.id}_{uuid.uuid4().hex[:8]}"  # Return fallback ID
    
    def user_disconnected(self, user, connection_id: Optional[str] = None):
        """
        Handle user disconnection event.
        
        Args:
            user: User who disconnected
            connection_id: Connection ID that was disconnected
        """
        try:
            with transaction.atomic():
                try:
                    status = UserStatus.objects.get(user=user)
                    was_online = status.is_online
                    
                    status.decrement_connections()
                    
                    # Broadcast status change if user went offline
                    if was_online and not status.is_online:
                        self._broadcast_presence_update(user, False)
                        logger.info(f"User {user.username} went offline")
                        
                except UserStatus.DoesNotExist:
                    logger.warning(f"UserStatus not found for disconnecting user {user.username}")
                    
        except Exception as e:
            logger.error(f"Failed to handle user disconnection for {user.username}: {e}")
    
    def update_heartbeat(self, user, connection_id: Optional[str] = None) -> bool:
        """
        Update user heartbeat timestamp.
        
        Args:
            user: User sending heartbeat
            connection_id: Connection ID sending heartbeat
            
        Returns:
            bool: True if heartbeat was updated successfully
        """
        try:
            status, created = UserStatus.objects.get_or_create(
                user=user,
                defaults={
                    'is_online': True,
                    'active_connections': 1,
                    'connection_id': connection_id
                }
            )
            
            status.update_ping()
            
            # Ensure user is marked online if sending heartbeat
            if not status.is_online:
                status.is_online = True
                status.save(update_fields=['is_online'])
                self._broadcast_presence_update(user, True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {user.username}: {e}")
            return False
    
    def _broadcast_presence_update(self, user, is_online: bool):
        """Broadcast presence update to relevant users."""
        if not self.channel_layer:
            logger.warning("Channel layer not available for presence broadcasting")
            return
        
        try:
            # Create presence payload
            presence_payload = {
                'type': 'user_status',
                'user_id': user.id,
                'username': user.username,
                'is_online': is_online,
                'timestamp': timezone.now().isoformat()
            }
            
            # Broadcast to all users who might be interested
            # This could be optimized to only broadcast to users with active conversations
            async_to_sync(self.channel_layer.group_send)(
                f'user_{user.id}',
                {
                    'type': 'user_status',
                    'user_id': user.id,
                    'username': user.username,
                    'is_online': is_online
                }
            )
            
            logger.debug(f"Broadcasted presence update: {user.username} -> {is_online}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast presence update: {e}")
    
    def get_user_presence(self, user) -> Dict[str, Any]:
        """
        Get comprehensive presence information for a user.
        
        Args:
            user: User to get presence for
            
        Returns:
            dict: Presence information
        """
        try:
            status = UserStatus.objects.get(user=user)
            
            return {
                'user_id': user.id,
                'username': user.username,
                'is_online': status.is_online,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None,
                'last_seen_display': status.get_last_seen_display(),
                'active_connections': status.active_connections,
                'last_ping': status.last_ping.isoformat() if status.last_ping else None,
                'connection_stale': status.is_connection_stale(),
                'device_info': status.device_info
            }
            
        except UserStatus.DoesNotExist:
            return {
                'user_id': user.id,
                'username': user.username,
                'is_online': False,
                'last_seen': None,
                'last_seen_display': 'Never',
                'active_connections': 0,
                'last_ping': None,
                'connection_stale': True,
                'device_info': {}
            }
        except Exception as e:
            logger.error(f"Failed to get presence for {user.username}: {e}")
            return {
                'user_id': user.id,
                'username': user.username,
                'is_online': False,
                'last_seen': None,
                'last_seen_display': 'Unknown',
                'active_connections': 0,
                'last_ping': None,
                'connection_stale': True,
                'device_info': {},
                'error': str(e)
            }
    
    def get_online_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of currently online users.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            list: List of online user information
        """
        try:
            online_statuses = UserStatus.objects.filter(
                is_online=True
            ).select_related('user').order_by('-last_ping')[:limit]
            
            online_users = []
            for status in online_statuses:
                online_users.append({
                    'user_id': status.user.id,
                    'username': status.user.username,
                    'active_connections': status.active_connections,
                    'last_ping': status.last_ping.isoformat() if status.last_ping else None,
                    'device_info': status.device_info
                })
            
            return online_users
            
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return []
    
    def cleanup_stale_connections(self, timeout_seconds: int = 30) -> int:
        """
        Clean up stale connections and update presence status.
        
        Args:
            timeout_seconds: Timeout for considering connection stale
            
        Returns:
            int: Number of stale connections cleaned up
        """
        try:
            count = UserStatus.cleanup_stale_connections(timeout_seconds)
            
            if count > 0:
                logger.info(f"Cleaned up {count} stale connections")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale connections: {e}")
            return 0
    
    def force_user_offline(self, user) -> bool:
        """
        Force a user offline (e.g., for admin purposes).
        
        Args:
            user: User to force offline
            
        Returns:
            bool: True if user was forced offline successfully
        """
        try:
            with transaction.atomic():
                status = UserStatus.objects.get(user=user)
                
                if status.is_online:
                    status.is_online = False
                    status.active_connections = 0
                    status.connection_id = None
                    status.save(update_fields=['is_online', 'active_connections', 'connection_id'])
                    
                    # Broadcast offline status
                    self._broadcast_presence_update(user, False)
                    
                    logger.info(f"Forced user {user.username} offline")
                    return True
                
                return False
                
        except UserStatus.DoesNotExist:
            logger.warning(f"Cannot force offline - UserStatus not found for {user.username}")
            return False
        except Exception as e:
            logger.error(f"Failed to force user {user.username} offline: {e}")
            return False
    
    def get_presence_summary(self) -> Dict[str, Any]:
        """
        Get overall presence statistics.
        
        Returns:
            dict: Presence summary statistics
        """
        try:
            from django.db.models import Count, Avg
            
            # Get basic counts
            total_users = UserStatus.objects.count()
            online_users = UserStatus.objects.filter(is_online=True).count()
            
            # Get connection statistics
            total_connections = UserStatus.objects.aggregate(
                total=models.Sum('active_connections')
            )['total'] or 0
            
            avg_connections = UserStatus.objects.filter(
                is_online=True
            ).aggregate(
                avg=Avg('active_connections')
            )['avg'] or 0
            
            # Get recent activity
            recent_cutoff = timezone.now() - timedelta(minutes=5)
            recent_activity = UserStatus.objects.filter(
                last_ping__gte=recent_cutoff
            ).count()
            
            return {
                'total_users': total_users,
                'online_users': online_users,
                'offline_users': total_users - online_users,
                'online_percentage': (online_users / total_users * 100) if total_users > 0 else 0,
                'total_connections': total_connections,
                'avg_connections_per_online_user': round(avg_connections, 2),
                'recent_activity_count': recent_activity,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get presence summary: {e}")
            return {
                'total_users': 0,
                'online_users': 0,
                'offline_users': 0,
                'online_percentage': 0,
                'total_connections': 0,
                'avg_connections_per_online_user': 0,
                'recent_activity_count': 0,
                'timestamp': timezone.now().isoformat(),
                'error': str(e)
            }
    
    def get_user_conversations_with_presence(self, user) -> List[Dict[str, Any]]:
        """
        Get user's conversations with presence information.
        
        Args:
            user: User to get conversations for
            
        Returns:
            list: Conversations with presence data
        """
        try:
            from django.db.models import Q
            from .models import Message
            
            # Get unique users the current user has conversed with
            conversations = []
            seen_users = set()
            
            messages = Message.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).select_related('sender', 'recipient').order_by('-created_at')
            
            for msg in messages:
                other_user = msg.recipient if msg.sender == user else msg.sender
                if other_user.id not in seen_users:
                    seen_users.add(other_user.id)
                    
                    # Get presence information
                    presence = self.get_user_presence(other_user)
                    
                    # Get unread count
                    unread_count = Message.objects.filter(
                        sender=other_user,
                        recipient=user,
                        is_read=False
                    ).count()
                    
                    conversations.append({
                        'user': {
                            'id': other_user.id,
                            'username': other_user.username,
                            'full_name': other_user.get_full_name() if hasattr(other_user, 'get_full_name') else other_user.username
                        },
                        'presence': presence,
                        'last_message': {
                            'id': msg.id,
                            'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                            'created_at': msg.created_at.isoformat(),
                            'sender': msg.sender.username
                        },
                        'unread_count': unread_count
                    })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversations with presence: {e}")
            return []


# Global instance
presence_manager = PresenceManager()
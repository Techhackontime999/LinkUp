"""
Notification Service for handling real-time notifications across the platform
"""
import json
import logging
from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """Service for creating and delivering notifications"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def create_and_send_notification(self, 
                                   recipient: User,
                                   notification_type: str,
                                   title: str,
                                   message: str,
                                   sender: Optional[User] = None,
                                   content_object: Optional[Any] = None,
                                   priority: str = 'normal',
                                   action_url: Optional[str] = None,
                                   group_key: Optional[str] = None,
                                   extra_data: Optional[Dict] = None) -> Notification:
        """
        Create a notification and send it via appropriate channels
        """
        try:
            # Check user preferences
            preference = NotificationPreference.get_user_preference(recipient, notification_type)
            
            if not preference.is_enabled:
                logger.info(f"Notification {notification_type} disabled for user {recipient.id}")
                return None
            
            # Check quiet hours
            if preference.is_in_quiet_hours() and priority not in ['high', 'urgent']:
                logger.info(f"Notification {notification_type} skipped due to quiet hours for user {recipient.id}")
                return None
            
            # Create notification
            notification = Notification.create_notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                sender=sender,
                content_object=content_object,
                priority=priority,
                action_url=action_url,
                group_key=group_key
            )
            
            # Send via real-time WebSocket if enabled
            if preference.delivery_method in ['realtime', 'push']:
                self._send_realtime_notification(notification, extra_data)
            
            # Mark as delivered
            notification.mark_as_delivered()
            
            logger.info(f"Notification {notification.id} created and sent to user {recipient.id}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    def _send_realtime_notification(self, notification: Notification, extra_data: Optional[Dict] = None):
        """Send notification via WebSocket"""
        try:
            payload = {
                'type': 'notification',
                'notification': {
                    'id': notification.id,
                    'notification_type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'sender': notification.sender.username if notification.sender else None,
                    'sender_avatar': notification.sender.profile.avatar.url if notification.sender and notification.sender.profile.avatar else None,
                    'created_at': notification.created_at.isoformat(),
                    'action_url': notification.action_url,
                    'is_grouped': notification.is_grouped,
                    'group_count': notification.group_count,
                    'unread_count': self.get_unread_count(notification.recipient)
                }
            }
            
            # Add extra data if provided
            if extra_data:
                payload['notification'].update(extra_data)
            
            # Send to user's notification channel
            if self.channel_layer:
                async_to_sync(self.channel_layer.group_send)(
                    f'user_{notification.recipient.id}',
                    {
                        'type': 'notification_message',
                        'message': payload
                    }
                )
                logger.debug(f"Real-time notification sent to user {notification.recipient.id}")
            
        except Exception as e:
            logger.error(f"Error sending real-time notification: {e}")
    
    def get_unread_count(self, user: User) -> int:
        """Get total unread notification count for user"""
        try:
            return Notification.objects.filter(recipient=user, is_read=False).count()
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def mark_notification_read(self, notification_id: int, user: User) -> bool:
        """Mark a notification as read and send real-time update"""
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.mark_as_read()
            
            # Send real-time update for badge count
            self._send_badge_update(user)
            
            logger.info(f"Notification {notification_id} marked as read for user {user.id}")
            return True
            
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {user.id}")
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    def mark_all_read(self, user: User, notification_type: Optional[str] = None) -> int:
        """Mark all notifications as read for a user"""
        try:
            query = Notification.objects.filter(recipient=user, is_read=False)
            if notification_type:
                query = query.filter(notification_type=notification_type)
            
            count = 0
            for notification in query:
                notification.mark_as_read()
                count += 1
            
            # Send real-time update for badge count
            self._send_badge_update(user)
            
            logger.info(f"Marked {count} notifications as read for user {user.id}")
            return count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return 0
    
    def _send_badge_update(self, user: User):
        """Send real-time badge count update"""
        try:
            unread_count = self.get_unread_count(user)
            
            if self.channel_layer:
                async_to_sync(self.channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'badge_update',
                        'message': {
                            'type': 'badge_update',
                            'unread_count': unread_count
                        }
                    }
                )
                logger.debug(f"Badge update sent to user {user.id}: {unread_count} unread")
            
        except Exception as e:
            logger.error(f"Error sending badge update: {e}")
    
    def get_notifications(self, user: User, limit: int = 20, offset: int = 0, 
                         notification_type: Optional[str] = None, 
                         unread_only: bool = False) -> List[Dict]:
        """Get notifications for a user with pagination"""
        try:
            query = Notification.objects.filter(recipient=user)
            
            if notification_type:
                query = query.filter(notification_type=notification_type)
            
            if unread_only:
                query = query.filter(is_read=False)
            
            notifications = query.select_related('sender').order_by('-created_at')[offset:offset+limit]
            
            result = []
            for notification in notifications:
                result.append({
                    'id': notification.id,
                    'notification_type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'sender': notification.sender.username if notification.sender else None,
                    'sender_avatar': notification.sender.profile.avatar.url if notification.sender and notification.sender.profile.avatar else None,
                    'is_read': notification.is_read,
                    'read_at': notification.read_at.isoformat() if notification.read_at else None,
                    'created_at': notification.created_at.isoformat(),
                    'action_url': notification.action_url,
                    'is_grouped': notification.is_grouped,
                    'group_count': notification.group_count,
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []


# Convenience functions for specific notification types

def notify_connection_request(sender: User, recipient: User, connection_obj):
    """Send notification for new connection request"""
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=recipient,
        notification_type='connection_request',
        title='New Connection Request',
        message=f'{sender.get_full_name() or sender.username} wants to connect with you',
        sender=sender,
        content_object=connection_obj,
        action_url=reverse('network:connections'),
        group_key=f'connection_requests_{recipient.id}'
    )


def notify_connection_accepted(sender: User, recipient: User, connection_obj):
    """Send notification when connection is accepted"""
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=recipient,
        notification_type='connection_accepted',
        title='Connection Accepted',
        message=f'{sender.get_full_name() or sender.username} accepted your connection request',
        sender=sender,
        content_object=connection_obj,
        action_url=reverse('users:profile', args=[sender.username])
    )


def notify_new_message(sender: User, recipient: User, message_obj):
    """Send notification for new message"""
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=recipient,
        notification_type='new_message',
        title='New Message',
        message=f'{sender.get_full_name() or sender.username}: {message_obj.content[:100]}...' if len(message_obj.content) > 100 else f'{sender.get_full_name() or sender.username}: {message_obj.content}',
        sender=sender,
        content_object=message_obj,
        action_url=reverse('messaging:chat_view', args=[sender.username]),
        group_key=f'messages_{sender.id}_{recipient.id}'
    )


def notify_job_application(applicant: User, job_poster: User, application_obj):
    """Send notification for new job application"""
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=job_poster,
        notification_type='job_application',
        title='New Job Application',
        message=f'{applicant.get_full_name() or applicant.username} applied for {application_obj.job.title}',
        sender=applicant,
        content_object=application_obj,
        action_url=reverse('jobs:job_detail', args=[application_obj.job.id]),
        group_key=f'job_applications_{application_obj.job.id}'
    )


def notify_post_liked(liker: User, post_owner: User, post_obj):
    """Send notification when post is liked"""
    if liker == post_owner:  # Don't notify self-likes
        return None
    
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=post_owner,
        notification_type='post_liked',
        title='Post Liked',
        message=f'{liker.get_full_name() or liker.username} liked your post',
        sender=liker,
        content_object=post_obj,
        action_url=reverse('feed:post_detail', args=[post_obj.id]) if hasattr(post_obj, 'id') else None,
        group_key=f'post_likes_{post_obj.id}'
    )


def notify_new_follower(follower: User, followed: User, follow_obj):
    """Send notification for new follower"""
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=followed,
        notification_type='new_follower',
        title='New Follower',
        message=f'{follower.get_full_name() or follower.username} started following you',
        sender=follower,
        content_object=follow_obj,
        action_url=reverse('users:profile', args=[follower.username]),
        group_key=f'followers_{followed.id}'
    )


def notify_mention(mentioner: User, mentioned: User, post_obj):
    """Send notification when user is mentioned in a post"""
    service = NotificationService()
    return service.create_and_send_notification(
        recipient=mentioned,
        notification_type='mention',
        title='You were mentioned',
        message=f'{mentioner.get_full_name() or mentioner.username} mentioned you in a post',
        sender=mentioner,
        content_object=post_obj,
        priority='high',  # Mentions are high priority
        action_url=reverse('feed:post_detail', args=[post_obj.id]) if hasattr(post_obj, 'id') else None
    )
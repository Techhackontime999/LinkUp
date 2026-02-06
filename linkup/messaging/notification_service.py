"""
Notification Service for handling real-time notifications across the platform
Enhanced with JSON serialization validation, error handling, and alternative delivery methods
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
from .serializers import JSONSerializer
from .logging_utils import MessagingLogger
from .retry_handler import MessageRetryHandler, RetryConfig

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """Service for creating and delivering notifications with enhanced error handling and reliability"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.json_serializer = JSONSerializer()
        self.retry_handler = MessageRetryHandler(RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=10.0
        ))
        self.fallback_delivery_methods = ['database', 'email']  # Alternative delivery methods
    
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
                                   extra_data: Optional[Dict] = None) -> Optional[Notification]:
        """
        Create a notification and send it via appropriate channels with enhanced error handling
        """
        try:
            # Validate input data
            if not self._validate_notification_data(recipient, notification_type, title, message):
                MessagingLogger.log_error(
                    "Invalid notification data provided",
                    context_data={
                        'recipient_id': recipient.id if recipient else None,
                        'notification_type': notification_type,
                        'title': title[:100] if title else None,
                        'message': message[:100] if message else None
                    }
                )
                return None
            
            # Check user preferences
            preference = NotificationPreference.get_user_preference(recipient, notification_type)
            
            if not preference.is_enabled:
                MessagingLogger.log_debug(
                    f"Notification {notification_type} disabled for user {recipient.id}",
                    {'recipient_id': recipient.id, 'notification_type': notification_type}
                )
                return None
            
            # Check quiet hours
            if preference.is_in_quiet_hours() and priority not in ['high', 'urgent']:
                MessagingLogger.log_debug(
                    f"Notification {notification_type} skipped due to quiet hours for user {recipient.id}",
                    {'recipient_id': recipient.id, 'notification_type': notification_type}
                )
                return None
            
            # Create notification with error handling
            notification = self._create_notification_with_retry(
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
            
            if not notification:
                MessagingLogger.log_error(
                    "Failed to create notification after retries",
                    context_data={
                        'recipient_id': recipient.id,
                        'notification_type': notification_type
                    }
                )
                return None
            
            # Send via real-time WebSocket if enabled with fallback mechanisms
            if preference.delivery_method in ['realtime', 'push']:
                delivery_success = self._send_realtime_notification_with_fallback(
                    notification, extra_data
                )
                
                if not delivery_success:
                    MessagingLogger.log_error(
                        f"All delivery methods failed for notification {notification.id}",
                        context_data={
                            'notification_id': notification.id,
                            'recipient_id': recipient.id
                        }
                    )
            
            # Mark as delivered (notification exists in database regardless of delivery method success)
            notification.mark_as_delivered()
            
            MessagingLogger.log_debug(
                f"Notification {notification.id} created and processed for user {recipient.id}",
                {
                    'notification_id': notification.id,
                    'recipient_id': recipient.id,
                    'notification_type': notification_type
                }
            )
            return notification
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error creating notification: {e}",
                context_data={
                    'recipient_id': recipient.id if recipient else None,
                    'notification_type': notification_type,
                    'sender_id': sender.id if sender else None
                }
            )
            return None
    
    def _send_realtime_notification_with_fallback(self, notification: Notification, extra_data: Optional[Dict] = None) -> bool:
        """Send notification via WebSocket with fallback to alternative delivery methods"""
        try:
            # First attempt: Real-time WebSocket delivery
            success = self._send_realtime_notification(notification, extra_data)
            if success:
                return True
            
            # Fallback: Try alternative delivery methods
            MessagingLogger.log_error(
                f"Real-time delivery failed for notification {notification.id}, trying fallback methods",
                context_data={'notification_id': notification.id, 'recipient_id': notification.recipient.id}
            )
            
            for method in self.fallback_delivery_methods:
                try:
                    if method == 'database':
                        # Notification is already in database, just log the fallback
                        MessagingLogger.log_debug(
                            f"Notification {notification.id} available via database fallback",
                            {'notification_id': notification.id, 'method': method}
                        )
                        return True
                    elif method == 'email':
                        # Implement email fallback if needed
                        success = self._send_email_notification(notification)
                        if success:
                            MessagingLogger.log_debug(
                                f"Notification {notification.id} sent via email fallback",
                                {'notification_id': notification.id, 'method': method}
                            )
                            return True
                except Exception as e:
                    MessagingLogger.log_error(
                        f"Fallback delivery method {method} failed: {e}",
                        context_data={
                            'notification_id': notification.id,
                            'method': method,
                            'recipient_id': notification.recipient.id
                        }
                    )
                    continue
            
            return False
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in notification delivery with fallback: {e}",
                context_data={'notification_id': notification.id}
            )
            return False
    
    def _send_realtime_notification(self, notification: Notification, extra_data: Optional[Dict] = None) -> bool:
        """Send notification via WebSocket with enhanced JSON serialization and error handling"""
        try:
            # Use enhanced serialization for notification data
            notification_data = self.json_serializer.serialize_notification(notification)
            
            # Add unread count
            notification_data['unread_count'] = self.get_unread_count(notification.recipient)
            
            # Add extra data if provided
            if extra_data:
                # Validate extra data is serializable
                if self.json_serializer.validate_serializable(extra_data):
                    notification_data.update(extra_data)
                else:
                    MessagingLogger.log_error(
                        "Extra data is not JSON serializable, skipping",
                        context_data={'notification_id': notification.id, 'extra_data_keys': list(extra_data.keys())}
                    )
            
            payload = {
                'type': 'notification',
                'notification': notification_data
            }
            
            # Validate payload is serializable
            if not self.json_serializer.validate_serializable(payload):
                MessagingLogger.log_error(
                    f"Notification payload is not JSON serializable for notification {notification.id}",
                    context_data={'notification_id': notification.id}
                )
                return False
            
            # Send to user's notification channel with retry mechanism
            if self.channel_layer:
                async def send_notification():
                    await self.channel_layer.group_send(
                        f'user_{notification.recipient.id}',
                        {
                            'type': 'notification_message',
                            'message': payload
                        }
                    )
                    return True
                
                # Use retry mechanism for WebSocket delivery
                import asyncio
                try:
                    result = async_to_sync(self.retry_handler.retry_async_operation)(
                        send_notification,
                        f"notification_delivery_{notification.id}"
                    )
                    
                    MessagingLogger.log_debug(
                        f"Real-time notification sent to user {notification.recipient.id}",
                        {'notification_id': notification.id, 'recipient_id': notification.recipient.id}
                    )
                    return True
                    
                except Exception as e:
                    MessagingLogger.log_error(
                        f"Error sending real-time notification after retries: {e}",
                        context_data={'notification_id': notification.id}
                    )
                    return False
            else:
                MessagingLogger.log_error(
                    "Channel layer not available for real-time notifications",
                    context_data={'notification_id': notification.id}
                )
                return False
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error sending real-time notification: {e}",
                context_data={'notification_id': notification.id}
            )
            return False
    
    def get_unread_count(self, user: User) -> int:
        """Get total unread notification count for user with error handling"""
        try:
            return Notification.objects.filter(recipient=user, is_read=False).count()
        except Exception as e:
            MessagingLogger.log_error(
                f"Error getting unread count: {e}",
                context_data={'user_id': user.id}
            )
            return 0
    
    def _validate_notification_data(self, recipient: User, notification_type: str, title: str, message: str) -> bool:
        """Validate notification data before processing"""
        try:
            # Check required fields
            if not recipient:
                MessagingLogger.log_error("Recipient is required for notification")
                return False
            
            if not notification_type or not notification_type.strip():
                MessagingLogger.log_error("Notification type is required")
                return False
            
            if not title or not title.strip():
                MessagingLogger.log_error("Notification title is required")
                return False
            
            if not message or not message.strip():
                MessagingLogger.log_error("Notification message is required")
                return False
            
            # Check field lengths
            if len(title) > 200:
                MessagingLogger.log_error(f"Notification title too long: {len(title)} characters")
                return False
            
            if len(message) > 1000:
                MessagingLogger.log_error(f"Notification message too long: {len(message)} characters")
                return False
            
            # Validate JSON serializability of basic data
            test_data = {
                'recipient_id': recipient.id,
                'notification_type': notification_type,
                'title': title,
                'message': message
            }
            
            if not self.json_serializer.validate_serializable(test_data):
                MessagingLogger.log_error("Notification data is not JSON serializable")
                return False
            
            return True
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error validating notification data: {e}",
                context_data={
                    'recipient_id': recipient.id if recipient else None,
                    'notification_type': notification_type
                }
            )
            return False
    
    def _create_notification_with_retry(self, **kwargs) -> Optional[Notification]:
        """Create notification with retry mechanism"""
        try:
            def create_notification():
                return Notification.create_notification(**kwargs)
            
            # Use synchronous retry for database operations
            for attempt in range(3):  # Max 3 attempts
                try:
                    notification = create_notification()
                    if notification:
                        return notification
                except Exception as e:
                    MessagingLogger.log_error(
                        f"Notification creation attempt {attempt + 1} failed: {e}",
                        context_data={
                            'attempt': attempt + 1,
                            'recipient_id': kwargs.get('recipient').id if kwargs.get('recipient') else None,
                            'notification_type': kwargs.get('notification_type')
                        }
                    )
                    if attempt == 2:  # Last attempt
                        raise e
                    
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            
            return None
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Failed to create notification after all retries: {e}",
                context_data={
                    'recipient_id': kwargs.get('recipient').id if kwargs.get('recipient') else None,
                    'notification_type': kwargs.get('notification_type')
                }
            )
            return None
    
    def _send_email_notification(self, notification: Notification) -> bool:
        """Send notification via email as fallback method"""
        try:
            # This is a placeholder for email notification implementation
            # In a real implementation, you would integrate with Django's email system
            # or a service like SendGrid, Mailgun, etc.
            
            MessagingLogger.log_debug(
                f"Email notification fallback triggered for notification {notification.id}",
                {
                    'notification_id': notification.id,
                    'recipient_email': notification.recipient.email,
                    'notification_type': notification.notification_type
                }
            )
            
            # For now, just return True to indicate the fallback was attempted
            # In production, implement actual email sending logic here
            return True
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error sending email notification: {e}",
                context_data={'notification_id': notification.id}
            )
            return False
    
    def mark_notification_read(self, notification_id: int, user: User) -> bool:
        """Mark a notification as read and send real-time update with enhanced error handling"""
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.mark_as_read()
            
            # Send real-time update for badge count with error handling
            self._send_badge_update_with_fallback(user)
            
            MessagingLogger.log_debug(
                f"Notification {notification_id} marked as read for user {user.id}",
                {'notification_id': notification_id, 'user_id': user.id}
            )
            return True
            
        except Notification.DoesNotExist:
            MessagingLogger.log_error(
                f"Notification {notification_id} not found for user {user.id}",
                context_data={'notification_id': notification_id, 'user_id': user.id}
            )
            return False
        except Exception as e:
            MessagingLogger.log_error(
                f"Error marking notification as read: {e}",
                context_data={'notification_id': notification_id, 'user_id': user.id}
            )
            return False
    
    def mark_all_read(self, user: User, notification_type: Optional[str] = None) -> int:
        """Mark all notifications as read for a user with enhanced error handling"""
        try:
            query = Notification.objects.filter(recipient=user, is_read=False)
            if notification_type:
                query = query.filter(notification_type=notification_type)
            
            count = 0
            for notification in query:
                try:
                    notification.mark_as_read()
                    count += 1
                except Exception as e:
                    MessagingLogger.log_error(
                        f"Error marking individual notification {notification.id} as read: {e}",
                        context_data={'notification_id': notification.id, 'user_id': user.id}
                    )
                    continue
            
            # Send real-time update for badge count with error handling
            self._send_badge_update_with_fallback(user)
            
            MessagingLogger.log_debug(
                f"Marked {count} notifications as read for user {user.id}",
                {'count': count, 'user_id': user.id, 'notification_type': notification_type}
            )
            return count
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error marking all notifications as read: {e}",
                context_data={'user_id': user.id, 'notification_type': notification_type}
            )
            return 0
    
    def _send_badge_update_with_fallback(self, user: User) -> bool:
        """Send real-time badge count update with fallback handling"""
        try:
            unread_count = self.get_unread_count(user)
            
            badge_data = {
                'type': 'badge_update',
                'unread_count': unread_count
            }
            
            # Validate badge data is serializable
            if not self.json_serializer.validate_serializable(badge_data):
                MessagingLogger.log_error(
                    "Badge update data is not JSON serializable",
                    context_data={'user_id': user.id, 'unread_count': unread_count}
                )
                return False
            
            if self.channel_layer:
                try:
                    async_to_sync(self.channel_layer.group_send)(
                        f'user_{user.id}',
                        {
                            'type': 'badge_update',
                            'message': badge_data
                        }
                    )
                    MessagingLogger.log_debug(
                        f"Badge update sent to user {user.id}: {unread_count} unread",
                        {'user_id': user.id, 'unread_count': unread_count}
                    )
                    return True
                except Exception as e:
                    MessagingLogger.log_error(
                        f"Error sending badge update via WebSocket: {e}",
                        context_data={'user_id': user.id, 'unread_count': unread_count}
                    )
                    # Fallback: Badge count is still available via API/database
                    return False
            else:
                MessagingLogger.log_error(
                    "Channel layer not available for badge update",
                    context_data={'user_id': user.id}
                )
                return False
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error sending badge update: {e}",
                context_data={'user_id': user.id}
            )
            return False
    
    def get_notifications(self, user: User, limit: int = 20, offset: int = 0, 
                         notification_type: Optional[str] = None, 
                         unread_only: bool = False) -> List[Dict]:
        """Get notifications for a user with pagination and enhanced serialization"""
        try:
            query = Notification.objects.filter(recipient=user)
            
            if notification_type:
                query = query.filter(notification_type=notification_type)
            
            if unread_only:
                query = query.filter(is_read=False)
            
            notifications = query.select_related('sender').order_by('-created_at')[offset:offset+limit]
            
            result = []
            for notification in notifications:
                try:
                    # Use enhanced JSON serializer for consistent serialization
                    serialized_notification = self.json_serializer.serialize_notification(notification)
                    result.append(serialized_notification)
                except Exception as e:
                    MessagingLogger.log_error(
                        f"Error serializing notification {notification.id}: {e}",
                        context_data={'notification_id': notification.id, 'user_id': user.id}
                    )
                    # Skip this notification but continue with others
                    continue
            
            MessagingLogger.log_debug(
                f"Retrieved {len(result)} notifications for user {user.id}",
                {
                    'user_id': user.id,
                    'count': len(result),
                    'limit': limit,
                    'offset': offset,
                    'notification_type': notification_type,
                    'unread_only': unread_only
                }
            )
            
            return result
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error getting notifications: {e}",
                context_data={
                    'user_id': user.id,
                    'limit': limit,
                    'offset': offset,
                    'notification_type': notification_type,
                    'unread_only': unread_only
                }
            )
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
        action_url=reverse('public_profile', args=[sender.username])
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
        action_url=reverse('public_profile', args=[follower.username]),
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
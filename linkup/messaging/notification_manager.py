"""
Advanced notification grouping and management utilities
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max
from django.utils import timezone
from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationGroupingManager:
    """Advanced notification grouping and management"""
    
    def __init__(self):
        self.grouping_rules = {
            'connection_request': {
                'time_window': timedelta(hours=24),
                'max_group_size': 10,
                'group_template': '{count} new connection requests'
            },
            'post_liked': {
                'time_window': timedelta(hours=6),
                'max_group_size': 20,
                'group_template': '{count} people liked your post'
            },
            'new_follower': {
                'time_window': timedelta(hours=12),
                'max_group_size': 15,
                'group_template': '{count} new followers'
            },
            'job_application': {
                'time_window': timedelta(hours=48),
                'max_group_size': 5,
                'group_template': '{count} new job applications'
            },
            'new_message': {
                'time_window': timedelta(hours=1),
                'max_group_size': 5,
                'group_template': '{count} new messages from {sender}'
            }
        }
    
    def should_group_notification(self, notification_type: str, recipient: User, 
                                group_key: str = None) -> Tuple[bool, Optional[Notification]]:
        """
        Determine if a notification should be grouped with existing notifications
        Returns (should_group, existing_group_notification)
        """
        if notification_type not in self.grouping_rules:
            return False, None
        
        rules = self.grouping_rules[notification_type]
        time_threshold = timezone.now() - rules['time_window']
        
        # Look for existing group
        query = Q(
            recipient=recipient,
            notification_type=notification_type,
            created_at__gte=time_threshold,
            is_grouped=True
        )
        
        if group_key:
            query &= Q(group_key=group_key)
        
        existing_group = Notification.objects.filter(query).first()
        
        if existing_group and existing_group.group_count < rules['max_group_size']:
            return True, existing_group
        
        return False, None
    
    def create_or_update_group(self, notification_type: str, recipient: User,
                             title: str, message: str, sender: User = None,
                             content_object=None, priority: str = 'normal',
                             group_key: str = None) -> Notification:
        """
        Create a new grouped notification or update an existing group
        """
        should_group, existing_group = self.should_group_notification(
            notification_type, recipient, group_key
        )
        
        if should_group and existing_group:
            # Update existing group
            existing_group.group_count += 1
            existing_group.created_at = timezone.now()  # Update timestamp
            existing_group.is_read = False  # Mark as unread
            existing_group.read_at = None
            
            # Update message with group template
            rules = self.grouping_rules[notification_type]
            if 'group_template' in rules:
                template = rules['group_template']
                if '{sender}' in template and sender:
                    existing_group.message = template.format(
                        count=existing_group.group_count,
                        sender=sender.get_full_name() or sender.username
                    )
                else:
                    existing_group.message = template.format(
                        count=existing_group.group_count
                    )
            
            existing_group.save()
            return existing_group
        else:
            # Create new notification (potentially grouped)
            group_key = group_key or self.generate_group_key(
                notification_type, recipient, sender, content_object
            )
            
            notification = Notification.objects.create(
                recipient=recipient,
                sender=sender,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                group_key=group_key,
                is_grouped=notification_type in self.grouping_rules,
                group_count=1
            )
            
            if content_object:
                notification.content_object = content_object
                notification.save()
            
            return notification
    
    def generate_group_key(self, notification_type: str, recipient: User,
                          sender: User = None, content_object=None) -> str:
        """Generate a group key for notifications"""
        base_key = f"{notification_type}_{recipient.id}"
        
        if notification_type == 'new_message' and sender:
            return f"{base_key}_{sender.id}"
        elif notification_type in ['post_liked', 'post_commented'] and content_object:
            return f"{base_key}_{content_object.id}"
        elif notification_type == 'job_application' and content_object:
            # Group by job
            job_id = getattr(content_object, 'job_id', None) or getattr(content_object, 'id', None)
            return f"{base_key}_{job_id}"
        else:
            return base_key
    
    def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """Clean up old read notifications"""
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        old_notifications = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_read=True
        )
        
        count = old_notifications.count()
        old_notifications.delete()
        
        logger.info(f"Cleaned up {count} old notifications")
        return count
    
    def get_notification_summary(self, user: User) -> Dict:
        """Get a summary of user's notifications"""
        total_count = Notification.objects.filter(recipient=user).count()
        unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
        
        # Count by type
        type_counts = Notification.objects.filter(recipient=user, is_read=False).values(
            'notification_type'
        ).annotate(count=Count('id'))
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = Notification.objects.filter(
            recipient=user,
            created_at__gte=week_ago
        ).count()
        
        return {
            'total_notifications': total_count,
            'unread_notifications': unread_count,
            'recent_notifications': recent_count,
            'notifications_by_type': {item['notification_type']: item['count'] for item in type_counts},
            'last_notification': Notification.objects.filter(recipient=user).first()
        }
    
    def bulk_mark_read(self, user: User, notification_ids: List[int] = None,
                      notification_type: str = None) -> int:
        """Bulk mark notifications as read"""
        query = Notification.objects.filter(recipient=user, is_read=False)
        
        if notification_ids:
            query = query.filter(id__in=notification_ids)
        
        if notification_type:
            query = query.filter(notification_type=notification_type)
        
        count = 0
        for notification in query:
            notification.mark_as_read()
            count += 1
        
        return count
    
    def get_grouped_notifications(self, user: User, limit: int = 20) -> List[Dict]:
        """Get notifications with proper grouping display"""
        notifications = Notification.objects.filter(
            recipient=user
        ).select_related('sender').order_by('-created_at')[:limit]
        
        result = []
        for notification in notifications:
            notification_data = {
                'id': notification.id,
                'notification_type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'priority': notification.priority,
                'sender': notification.sender.username if notification.sender else None,
                'sender_name': notification.sender.get_full_name() if notification.sender else None,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'action_url': notification.action_url,
                'is_grouped': notification.is_grouped,
                'group_count': notification.group_count,
            }
            
            # Add grouped notification details
            if notification.is_grouped and notification.group_count > 1:
                notification_data['grouped_details'] = self.get_group_details(notification)
            
            result.append(notification_data)
        
        return result
    
    def get_group_details(self, group_notification: Notification) -> Dict:
        """Get details about a grouped notification"""
        if not group_notification.group_key:
            return {}
        
        # Get all notifications in the group
        group_notifications = Notification.objects.filter(
            recipient=group_notification.recipient,
            group_key=group_notification.group_key
        ).select_related('sender').order_by('-created_at')
        
        senders = []
        for notif in group_notifications:
            if notif.sender and notif.sender not in senders:
                senders.append(notif.sender)
        
        return {
            'total_count': group_notifications.count(),
            'senders': [
                {
                    'username': sender.username,
                    'full_name': sender.get_full_name(),
                    'avatar_url': sender.profile.avatar.url if hasattr(sender, 'profile') and sender.profile.avatar else None
                }
                for sender in senders[:5]  # Limit to 5 senders
            ],
            'latest_timestamp': group_notifications.first().created_at.isoformat(),
            'oldest_timestamp': group_notifications.last().created_at.isoformat()
        }
    
    def optimize_notification_delivery(self, user: User) -> Dict:
        """Optimize notification delivery based on user behavior"""
        # Analyze user's notification interaction patterns
        week_ago = timezone.now() - timedelta(days=7)
        
        # Get user's notification preferences
        preferences = NotificationPreference.objects.filter(user=user)
        
        # Analyze read patterns
        notifications = Notification.objects.filter(
            recipient=user,
            created_at__gte=week_ago
        )
        
        total_notifications = notifications.count()
        read_notifications = notifications.filter(is_read=True).count()
        read_rate = (read_notifications / total_notifications) if total_notifications > 0 else 0
        
        # Analyze response time
        read_times = []
        for notif in notifications.filter(is_read=True, read_at__isnull=False):
            if notif.read_at and notif.created_at:
                response_time = (notif.read_at - notif.created_at).total_seconds()
                read_times.append(response_time)
        
        avg_response_time = sum(read_times) / len(read_times) if read_times else 0
        
        # Generate recommendations
        recommendations = []
        
        if read_rate < 0.3:
            recommendations.append("Consider reducing notification frequency")
        
        if avg_response_time > 3600:  # More than 1 hour
            recommendations.append("Consider enabling quiet hours during inactive periods")
        
        # Analyze notification types
        type_stats = notifications.values('notification_type').annotate(
            total=Count('id'),
            read=Count('id', filter=Q(is_read=True))
        )
        
        for stat in type_stats:
            type_read_rate = stat['read'] / stat['total'] if stat['total'] > 0 else 0
            if type_read_rate < 0.2:
                recommendations.append(
                    f"Consider disabling {stat['notification_type']} notifications"
                )
        
        return {
            'total_notifications': total_notifications,
            'read_rate': read_rate,
            'average_response_time_seconds': avg_response_time,
            'recommendations': recommendations,
            'notification_type_stats': list(type_stats)
        }


class NotificationBatchProcessor:
    """Process notifications in batches for performance"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.grouping_manager = NotificationGroupingManager()
    
    def process_pending_notifications(self) -> int:
        """Process any pending notification operations"""
        # This could be used for delayed notification processing
        # For now, we'll implement a cleanup operation
        return self.grouping_manager.cleanup_old_notifications()
    
    def send_digest_notifications(self, frequency: str = 'daily') -> int:
        """Send digest notifications to users who prefer them"""
        # Get users who prefer digest notifications
        digest_preferences = NotificationPreference.objects.filter(
            delivery_method='email',
            is_enabled=True
        )
        
        sent_count = 0
        
        for pref in digest_preferences:
            user = pref.user
            
            # Determine time range based on frequency
            if frequency == 'daily':
                since = timezone.now() - timedelta(days=1)
            elif frequency == 'weekly':
                since = timezone.now() - timedelta(days=7)
            else:
                continue
            
            # Get unread notifications for this user
            unread_notifications = Notification.objects.filter(
                recipient=user,
                is_read=False,
                created_at__gte=since,
                notification_type=pref.notification_type
            )
            
            if unread_notifications.exists():
                # Create digest notification
                count = unread_notifications.count()
                digest_notification = Notification.objects.create(
                    recipient=user,
                    notification_type='system_announcement',
                    title=f'{frequency.title()} Digest',
                    message=f'You have {count} unread notifications',
                    priority='low'
                )
                
                sent_count += 1
                logger.info(f"Sent {frequency} digest to user {user.username}")
        
        return sent_count
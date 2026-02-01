"""
Management command to test the notification system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from messaging.notification_service import NotificationService
from messaging.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the notification system by creating sample notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to send test notifications to',
            required=True
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test notifications to create'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=[choice[0] for choice in Notification.NOTIFICATION_TYPES],
            help='Specific notification type to test'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up test notifications after creating them'
        )
    
    def handle(self, *args, **options):
        username = options['user']
        count = options['count']
        notification_type = options['type']
        cleanup = options['cleanup']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" not found')
            )
            return
        
        service = NotificationService()
        created_notifications = []
        
        # Test notification types
        test_notifications = [
            {
                'type': 'connection_request',
                'title': 'New Connection Request',
                'message': 'John Doe wants to connect with you',
                'priority': 'normal'
            },
            {
                'type': 'new_message',
                'title': 'New Message',
                'message': 'You have a new message from Jane Smith',
                'priority': 'normal'
            },
            {
                'type': 'job_application',
                'title': 'New Job Application',
                'message': 'Someone applied for your Software Engineer position',
                'priority': 'high'
            },
            {
                'type': 'post_liked',
                'title': 'Post Liked',
                'message': 'Your post received 5 new likes',
                'priority': 'low',
                'group_key': f'post_likes_123'
            },
            {
                'type': 'mention',
                'title': 'You were mentioned',
                'message': 'Alex mentioned you in a post about Python development',
                'priority': 'high'
            },
            {
                'type': 'system_announcement',
                'title': 'System Maintenance',
                'message': 'Scheduled maintenance will occur tonight from 2-4 AM',
                'priority': 'urgent'
            }
        ]
        
        # Filter by type if specified
        if notification_type:
            test_notifications = [n for n in test_notifications if n['type'] == notification_type]
        
        # Create notifications
        for i in range(count):
            for test_notif in test_notifications:
                try:
                    notification = service.create_and_send_notification(
                        recipient=user,
                        notification_type=test_notif['type'],
                        title=f"{test_notif['title']} #{i+1}",
                        message=test_notif['message'],
                        priority=test_notif['priority'],
                        group_key=test_notif.get('group_key')
                    )
                    
                    if notification:
                        created_notifications.append(notification)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created {test_notif["type"]} notification: {notification.id}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Failed to create {test_notif["type"]} notification (may be disabled)'
                            )
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error creating {test_notif["type"]} notification: {e}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Created {len(created_notifications)} test notifications for user {username}'
            )
        )
        
        # Show current unread count
        unread_count = service.get_unread_count(user)
        self.stdout.write(
            self.style.SUCCESS(
                f'User {username} now has {unread_count} unread notifications'
            )
        )
        
        # Cleanup if requested
        if cleanup:
            self.stdout.write('Cleaning up test notifications...')
            
            for notification in created_notifications:
                try:
                    notification.delete()
                    self.stdout.write(f'Deleted notification {notification.id}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error deleting notification {notification.id}: {e}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS('Cleanup completed')
            )
        
        # Show available notification types
        if not notification_type:
            self.stdout.write('\nAvailable notification types:')
            for choice in Notification.NOTIFICATION_TYPES:
                self.stdout.write(f'  - {choice[0]}: {choice[1]}')
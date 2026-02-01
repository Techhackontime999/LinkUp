"""
Management command for notification system maintenance and management
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from datetime import timedelta
from messaging.notification_manager import NotificationGroupingManager, NotificationBatchProcessor
from messaging.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage notifications: cleanup, statistics, and maintenance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old read notifications'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days old for cleanup (default: 30)'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show notification statistics'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Show statistics for specific user'
        )
        parser.add_argument(
            '--digest',
            choices=['daily', 'weekly'],
            help='Send digest notifications'
        )
        parser.add_argument(
            '--optimize',
            type=str,
            help='Optimize notification delivery for specific user'
        )
        parser.add_argument(
            '--regroup',
            action='store_true',
            help='Reprocess notification grouping'
        )
    
    def handle(self, *args, **options):
        manager = NotificationGroupingManager()
        processor = NotificationBatchProcessor()
        
        if options['cleanup']:
            days = options['days']
            self.stdout.write(f'Cleaning up notifications older than {days} days...')
            
            count = manager.cleanup_old_notifications(days)
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {count} old notifications')
            )
        
        if options['stats']:
            if options['user']:
                try:
                    user = User.objects.get(username=options['user'])
                    self.show_user_stats(manager, user)
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'User "{options["user"]}" not found')
                    )
            else:
                self.show_global_stats()
        
        if options['digest']:
            frequency = options['digest']
            self.stdout.write(f'Sending {frequency} digest notifications...')
            
            count = processor.send_digest_notifications(frequency)
            self.stdout.write(
                self.style.SUCCESS(f'Sent {count} digest notifications')
            )
        
        if options['optimize']:
            try:
                user = User.objects.get(username=options['optimize'])
                self.show_optimization_recommendations(manager, user)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{options["optimize"]}" not found')
                )
        
        if options['regroup']:
            self.stdout.write('Reprocessing notification grouping...')
            count = self.reprocess_grouping(manager)
            self.stdout.write(
                self.style.SUCCESS(f'Reprocessed {count} notifications')
            )
    
    def show_user_stats(self, manager, user):
        """Show statistics for a specific user"""
        self.stdout.write(f'\nNotification Statistics for {user.username}:')
        self.stdout.write('=' * 50)
        
        summary = manager.get_notification_summary(user)
        
        self.stdout.write(f'Total notifications: {summary["total_notifications"]}')
        self.stdout.write(f'Unread notifications: {summary["unread_notifications"]}')
        self.stdout.write(f'Recent notifications (7 days): {summary["recent_notifications"]}')
        
        if summary['notifications_by_type']:
            self.stdout.write('\nUnread notifications by type:')
            for notif_type, count in summary['notifications_by_type'].items():
                self.stdout.write(f'  {notif_type}: {count}')
        
        if summary['last_notification']:
            last_notif = summary['last_notification']
            self.stdout.write(f'\nLast notification: {last_notif.title}')
            self.stdout.write(f'Created: {last_notif.created_at}')
            self.stdout.write(f'Read: {"Yes" if last_notif.is_read else "No"}')
    
    def show_global_stats(self):
        """Show global notification statistics"""
        self.stdout.write('\nGlobal Notification Statistics:')
        self.stdout.write('=' * 40)
        
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        grouped_notifications = Notification.objects.filter(is_grouped=True).count()
        
        self.stdout.write(f'Total notifications: {total_notifications}')
        self.stdout.write(f'Unread notifications: {unread_notifications}')
        self.stdout.write(f'Grouped notifications: {grouped_notifications}')
        
        # Top notification types
        from django.db.models import Count
        top_types = Notification.objects.values('notification_type').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        self.stdout.write('\nTop notification types:')
        for item in top_types:
            self.stdout.write(f'  {item["notification_type"]}: {item["count"]}')
        
        # Users with most unread notifications
        from django.db.models import Count
        top_unread_users = User.objects.annotate(
            unread_count=Count('notifications', filter=models.Q(notifications__is_read=False))
        ).filter(unread_count__gt=0).order_by('-unread_count')[:10]
        
        self.stdout.write('\nUsers with most unread notifications:')
        for user in top_unread_users:
            self.stdout.write(f'  {user.username}: {user.unread_count}')
    
    def show_optimization_recommendations(self, manager, user):
        """Show optimization recommendations for a user"""
        self.stdout.write(f'\nOptimization Analysis for {user.username}:')
        self.stdout.write('=' * 50)
        
        analysis = manager.optimize_notification_delivery(user)
        
        self.stdout.write(f'Total notifications (7 days): {analysis["total_notifications"]}')
        self.stdout.write(f'Read rate: {analysis["read_rate"]:.2%}')
        self.stdout.write(f'Average response time: {analysis["average_response_time_seconds"]:.0f} seconds')
        
        if analysis['recommendations']:
            self.stdout.write('\nRecommendations:')
            for rec in analysis['recommendations']:
                self.stdout.write(f'  • {rec}')
        else:
            self.stdout.write('\n✓ No optimization recommendations at this time')
        
        if analysis['notification_type_stats']:
            self.stdout.write('\nNotification type performance:')
            for stat in analysis['notification_type_stats']:
                read_rate = stat['read'] / stat['total'] if stat['total'] > 0 else 0
                self.stdout.write(
                    f'  {stat["notification_type"]}: {read_rate:.1%} read rate '
                    f'({stat["read"]}/{stat["total"]})'
                )
    
    def reprocess_grouping(self, manager):
        """Reprocess notification grouping"""
        # This is a simplified version - in practice, you'd want to be more careful
        # about preserving existing groups and user read states
        
        notifications = Notification.objects.filter(
            is_grouped=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('created_at')
        
        count = 0
        for notification in notifications:
            # Check if this notification should be grouped
            should_group, existing_group = manager.should_group_notification(
                notification.notification_type,
                notification.recipient,
                notification.group_key
            )
            
            if should_group and existing_group:
                # Move this notification to the group
                notification.delete()  # Remove individual notification
                existing_group.group_count += 1
                existing_group.save()
                count += 1
        
        return count
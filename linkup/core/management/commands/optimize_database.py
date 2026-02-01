"""
Management command to optimize database performance by creating indexes
and analyzing query patterns.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimize database performance with indexes and query analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze queries without creating indexes',
        )
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create performance indexes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting database optimization...')
        )

        if options['analyze_only']:
            self.analyze_queries()
        elif options['create_indexes']:
            self.create_performance_indexes()
        else:
            self.analyze_queries()
            self.create_performance_indexes()

        self.stdout.write(
            self.style.SUCCESS('Database optimization completed!')
        )

    def analyze_queries(self):
        """Analyze query patterns for optimization opportunities."""
        self.stdout.write('Analyzing query patterns...')
        
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    'Query analysis requires DEBUG=True. '
                    'Enable debug mode to see detailed query analysis.'
                )
            )
            return

        from core.performance import DatabaseOptimizer
        
        # Reset query log
        connection.queries_log.clear()
        
        # Simulate some common queries to analyze
        self._simulate_common_queries()
        
        # Analyze the queries
        analysis = DatabaseOptimizer.analyze_queries()
        
        self.stdout.write(f"Total queries executed: {analysis['total_queries']}")
        self.stdout.write(f"Slow queries (>0.1s): {analysis['slow_queries']}")
        self.stdout.write(f"Duplicate queries: {analysis['duplicate_queries']}")
        
        if analysis['slowest_query']:
            self.stdout.write(
                f"Slowest query time: {analysis['slowest_query']['time']}s"
            )
        
        if analysis['duplicates']:
            self.stdout.write(
                self.style.WARNING('Found duplicate queries:')
            )
            for sql, count in list(analysis['duplicates'].items())[:5]:
                self.stdout.write(f"  {count}x: {sql[:100]}...")

    def create_performance_indexes(self):
        """Create database indexes for better performance."""
        self.stdout.write('Creating performance indexes...')
        
        with connection.cursor() as cursor:
            # Indexes for messaging performance
            indexes = [
                # Message indexes
                "CREATE INDEX IF NOT EXISTS idx_message_recipient_created ON messaging_message(recipient_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_message_sender_created ON messaging_message(sender_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_message_conversation ON messaging_message(sender_id, recipient_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_message_unread ON messaging_message(recipient_id, is_read, created_at DESC);",
                
                # Notification indexes
                "CREATE INDEX IF NOT EXISTS idx_notification_recipient_created ON messaging_notification(recipient_id, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_notification_unread ON messaging_notification(recipient_id, is_read);",
                "CREATE INDEX IF NOT EXISTS idx_notification_type ON messaging_notification(recipient_id, notification_type);",
                "CREATE INDEX IF NOT EXISTS idx_notification_group ON messaging_notification(group_key, created_at DESC);",
                
                # User profile indexes
                "CREATE INDEX IF NOT EXISTS idx_profile_user ON users_profile(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_experience_user ON users_experience(user_id, start_date DESC);",
                "CREATE INDEX IF NOT EXISTS idx_education_user ON users_education(user_id, start_date DESC);",
                
                # User status indexes
                "CREATE INDEX IF NOT EXISTS idx_user_status_online ON messaging_userstatus(is_online, last_seen DESC);",
                
                # Generic content type indexes for notifications
                "CREATE INDEX IF NOT EXISTS idx_notification_content ON messaging_notification(content_type_id, object_id);",
            ]
            
            created_count = 0
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    created_count += 1
                    self.stdout.write(f"  ✓ Created index")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        self.stdout.write(
                            self.style.WARNING(f"  ✗ Failed to create index: {e}")
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} performance indexes")
            )

    def _simulate_common_queries(self):
        """Simulate common queries to analyze performance."""
        from django.contrib.auth import get_user_model
        from messaging.models import Message, Notification
        
        User = get_user_model()
        
        try:
            # Simulate common query patterns
            users = User.objects.all()[:5]
            
            for user in users:
                # Common message queries
                Message.objects.filter(recipient=user, is_read=False).count()
                Message.objects.filter(
                    recipient=user
                ).select_related('sender').order_by('-created_at')[:10]
                
                # Common notification queries
                Notification.objects.filter(recipient=user, is_read=False).count()
                Notification.objects.filter(
                    recipient=user
                ).order_by('-created_at')[:10]
                
        except Exception as e:
            logger.warning(f"Error simulating queries: {e}")

    def get_database_stats(self):
        """Get database statistics."""
        with connection.cursor() as cursor:
            # Get table sizes
            cursor.execute("""
                SELECT 
                    name,
                    COUNT(*) as row_count
                FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
            """)
            
            tables = cursor.fetchall()
            
            self.stdout.write("Database Statistics:")
            for table_name, row_count in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    actual_count = cursor.fetchone()[0]
                    self.stdout.write(f"  {table_name}: {actual_count} rows")
                except Exception:
                    pass
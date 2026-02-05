"""
Django management command to monitor messaging system health
"""
import time
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from messaging.error_monitor import error_monitor


class Command(BaseCommand):
    help = 'Monitor messaging system health and async context errors'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous monitoring (every 30 seconds)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Monitoring interval in seconds (default: 30)',
        )
        parser.add_argument(
            '--check-async',
            action='store_true',
            help='Focus on async context errors only',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format',
        )
    
    def handle(self, *args, **options):
        if options['continuous']:
            self.run_continuous_monitoring(options)
        else:
            self.run_single_check(options)
    
    def run_single_check(self, options):
        """Run a single health check"""
        self.stdout.write(
            self.style.SUCCESS(
                f"Messaging System Health Check - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        )
        
        if options['check_async']:
            self.check_async_errors_only()
        else:
            self.check_full_health(options['json'])
    
    def run_continuous_monitoring(self, options):
        """Run continuous monitoring"""
        interval = options['interval']
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting continuous monitoring (interval: {interval}s). Press Ctrl+C to stop."
            )
        )
        
        try:
            while True:
                self.stdout.write("\n" + "="*60)
                self.run_single_check(options)
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS("\nMonitoring stopped.")
            )
    
    def check_async_errors_only(self):
        """Check only async context errors"""
        async_check = error_monitor.check_async_context_errors(minutes=5)
        
        if async_check['has_sync_only_errors']:
            self.stdout.write(
                self.style.ERROR(
                    "🚨 CRITICAL: SynchronousOnlyOperation errors detected!"
                )
            )
        elif async_check['count'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  {async_check['count']} async context errors in last 5 minutes"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "✅ No async context errors in last 5 minutes"
                )
            )
        
        if async_check['errors']:
            self.stdout.write("\nRecent async errors:")
            for error in async_check['errors'][:5]:  # Show last 5
                self.stdout.write(
                    f"  - {error['occurred_at']}: {error['error_message'][:100]}..."
                )
    
    def check_full_health(self, json_output=False):
        """Check full system health"""
        report = error_monitor.generate_health_report()
        
        if json_output:
            self.stdout.write(json.dumps(report, indent=2, default=str))
            return
        
        # Status indicator
        status_colors = {
            'healthy': self.style.SUCCESS,
            'warning': self.style.WARNING,
            'critical': self.style.ERROR
        }
        
        status_icons = {
            'healthy': '✅',
            'warning': '⚠️ ',
            'critical': '🚨'
        }
        
        color_func = status_colors.get(report['status'], self.style.SUCCESS)
        icon = status_icons.get(report['status'], '❓')
        
        self.stdout.write(
            color_func(
                f"{icon} Status: {report['status'].upper()} "
                f"(Health Score: {report['health_score']}/100)"
            )
        )
        
        # Recent errors summary
        if report['recent_errors_count'] > 0:
            self.stdout.write(
                f"📊 Recent errors (5 min): {report['recent_errors_count']}"
            )
        
        # Error summary
        if report['error_summary']:
            self.stdout.write("\n📈 Error Summary (1 hour):")
            for error_type, count in report['error_summary'].items():
                self.stdout.write(f"  - {error_type}: {count}")
        
        # Async context check
        async_check = report['async_context_check']
        if async_check['has_sync_only_errors']:
            self.stdout.write(
                self.style.ERROR(
                    "\n🚨 CRITICAL: SynchronousOnlyOperation errors detected!"
                )
            )
        elif async_check['count'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Async context errors: {async_check['count']}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ No async context errors"
                )
            )
        
        # WebSocket check
        websocket_check = report['websocket_check']
        if websocket_check['count'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"🔌 WebSocket errors: {websocket_check['count']}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "🔌 WebSocket connections stable"
                )
            )
        
        # Recommendations
        if report['recommendations']:
            self.stdout.write("\n💡 Recommendations:")
            for rec in report['recommendations']:
                self.stdout.write(f"  • {rec}")
        
        # Quick fix suggestions
        if async_check['has_sync_only_errors']:
            self.stdout.write(
                self.style.ERROR(
                    "\n🔧 URGENT FIX NEEDED:"
                    "\n  1. Check all database operations in async contexts"
                    "\n  2. Ensure database_sync_to_async is used properly"
                    "\n  3. Review MessagingError.log_error calls"
                )
            )
        elif report['health_score'] < 80:
            self.stdout.write(
                self.style.WARNING(
                    "\n🔧 Suggested Actions:"
                    "\n  1. Review recent error logs"
                    "\n  2. Check WebSocket connection stability"
                    "\n  3. Monitor for patterns in error types"
                )
            )
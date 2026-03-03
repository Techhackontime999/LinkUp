"""
Management command to monitor system health and check thresholds.

This command can be run periodically (e.g., via cron or systemd timer) to:
- Collect system health metrics
- Check metrics against configured thresholds
- Trigger alerts when thresholds are exceeded

Usage:
    python manage.py monitor_health [--interval SECONDS] [--continuous]

Options:
    --interval SECONDS    Check interval in seconds (default: 60)
    --continuous         Run continuously instead of one-time check

Requirements: 20.7
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_agents.metrics_tracker import SystemMetricsTracker

logger = logging.getLogger('ai_agents.management')


class Command(BaseCommand):
    help = 'Monitor system health and check thresholds for violations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously instead of one-time check'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        continuous = options['continuous']

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting health monitoring (interval: {interval}s, continuous: {continuous})'
            )
        )

        if continuous:
            self._run_continuous(interval)
        else:
            self._run_once()

    def _run_once(self):
        """Run a single health check."""
        self.stdout.write('Running health check...')
        
        try:
            # Get current metrics
            metrics_result = SystemMetricsTracker.get_all_metrics()
            
            if metrics_result['status'] != 'SUCCESS':
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to get metrics: {metrics_result.get('error', 'Unknown error')}"
                    )
                )
                return
            
            metrics = metrics_result['metrics']
            
            # Display current metrics
            self.stdout.write(self.style.SUCCESS('\nCurrent Metrics:'))
            self.stdout.write(f"  Active Agents: {metrics['total_active_agents']}")
            self.stdout.write(f"  Messages/min: {metrics['messages_per_minute']}")
            self.stdout.write(f"  Avg Latency: {metrics['average_message_latency_ms']:.2f}ms")
            self.stdout.write(f"  WebSocket Connections: {metrics['websocket_connections']}")
            self.stdout.write(f"  API Requests/min: {metrics['total_api_requests_per_minute']}")
            
            # Check thresholds
            self.stdout.write('\nChecking thresholds...')
            threshold_result = SystemMetricsTracker.check_thresholds(metrics=metrics)
            
            if threshold_result['status'] != 'SUCCESS':
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to check thresholds: {threshold_result.get('error', 'Unknown error')}"
                    )
                )
                return
            
            # Display results
            if threshold_result['has_violations']:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n⚠️  {threshold_result['violation_count']} threshold violation(s) detected!"
                    )
                )
                
                for violation in threshold_result['violations']:
                    severity_style = self.style.ERROR if violation['severity'] == 'critical' else self.style.WARNING
                    self.stdout.write(
                        severity_style(
                            f"\n  [{violation['severity'].upper()}] {violation['metric']}"
                        )
                    )
                    self.stdout.write(f"    Current: {violation['current_value']}")
                    self.stdout.write(f"    Threshold: {violation['threshold']}")
                    self.stdout.write(f"    Message: {violation['message']}")
                
                self.stdout.write(
                    self.style.WARNING(
                        f"\nAlerts have been triggered via configured channels."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✓ All metrics within thresholds'
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nHealth check completed at {timezone.now().isoformat()}'
                )
            )
            
        except Exception as e:
            logger.error(f'Error during health check: {str(e)}', exc_info=True)
            self.stdout.write(
                self.style.ERROR(
                    f'Health check failed: {str(e)}'
                )
            )

    def _run_continuous(self, interval):
        """Run health checks continuously at specified interval."""
        self.stdout.write(
            self.style.SUCCESS(
                f'Running continuous monitoring (checking every {interval} seconds)'
            )
        )
        self.stdout.write('Press Ctrl+C to stop\n')
        
        check_count = 0
        
        try:
            while True:
                check_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n{"="*60}\nCheck #{check_count} at {timezone.now().isoformat()}\n{"="*60}'
                    )
                )
                
                self._run_once()
                
                self.stdout.write(
                    f'\nNext check in {interval} seconds...\n'
                )
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n\nMonitoring stopped. Completed {check_count} checks.'
                )
            )

"""
Real-time error monitoring for messaging system
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from .models import MessagingError

logger = logging.getLogger(__name__)


class MessagingErrorMonitor:
    """
    Monitor and analyze messaging system errors in real-time
    """
    
    def __init__(self):
        self.error_counts = {}
        self.last_check = timezone.now()
    
    def get_recent_errors(self, minutes: int = 5) -> List[MessagingError]:
        """Get errors from the last N minutes"""
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        return MessagingError.objects.filter(
            occurred_at__gte=cutoff_time
        ).order_by('-occurred_at')
    
    def get_error_summary(self, hours: int = 1) -> Dict[str, int]:
        """Get error summary by type for the last N hours"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        errors = MessagingError.objects.filter(occurred_at__gte=cutoff_time)
        
        summary = {}
        for error in errors:
            error_type = error.error_type
            summary[error_type] = summary.get(error_type, 0) + 1
        
        return summary
    
    def check_async_context_errors(self, minutes: int = 5) -> Dict[str, any]:
        """Check for async context errors specifically"""
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        async_errors = MessagingError.objects.filter(
            error_type='async_context',
            occurred_at__gte=cutoff_time
        ).order_by('-occurred_at')
        
        return {
            'count': async_errors.count(),
            'errors': list(async_errors.values(
                'error_message', 'occurred_at', 'severity', 'context_data'
            )),
            'has_sync_only_errors': any(
                'SynchronousOnlyOperation' in error.error_message 
                for error in async_errors
            )
        }
    
    def check_websocket_errors(self, minutes: int = 5) -> Dict[str, any]:
        """Check for WebSocket-related errors"""
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        websocket_errors = MessagingError.objects.filter(
            error_type__in=['websocket_transmission', 'connection_handling'],
            occurred_at__gte=cutoff_time
        ).order_by('-occurred_at')
        
        return {
            'count': websocket_errors.count(),
            'errors': list(websocket_errors.values(
                'error_type', 'error_message', 'occurred_at', 'severity'
            ))
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, List[int]]:
        """Get error trends over time (hourly buckets)"""
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)
        
        errors = MessagingError.objects.filter(
            occurred_at__gte=start_time,
            occurred_at__lte=end_time
        )
        
        # Create hourly buckets
        trends = {}
        for i in range(hours):
            bucket_start = start_time + timedelta(hours=i)
            bucket_end = bucket_start + timedelta(hours=1)
            
            bucket_errors = errors.filter(
                occurred_at__gte=bucket_start,
                occurred_at__lt=bucket_end
            )
            
            for error in bucket_errors:
                error_type = error.error_type
                if error_type not in trends:
                    trends[error_type] = [0] * hours
                trends[error_type][i] += 1
        
        return trends
    
    def generate_health_report(self) -> Dict[str, any]:
        """Generate a comprehensive health report"""
        now = timezone.now()
        
        # Recent errors (last 5 minutes)
        recent_errors = self.get_recent_errors(5)
        
        # Error summary (last hour)
        error_summary = self.get_error_summary(1)
        
        # Async context errors check
        async_check = self.check_async_context_errors(5)
        
        # WebSocket errors check
        websocket_check = self.check_websocket_errors(5)
        
        # Calculate health score (0-100)
        health_score = 100
        if async_check['has_sync_only_errors']:
            health_score -= 50  # Major issue
        if async_check['count'] > 0:
            health_score -= min(async_check['count'] * 5, 30)
        if websocket_check['count'] > 0:
            health_score -= min(websocket_check['count'] * 3, 20)
        
        health_score = max(0, health_score)
        
        return {
            'timestamp': now.isoformat(),
            'health_score': health_score,
            'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
            'recent_errors_count': len(recent_errors),
            'error_summary': error_summary,
            'async_context_check': async_check,
            'websocket_check': websocket_check,
            'recommendations': self._generate_recommendations(async_check, websocket_check, error_summary)
        }
    
    def _generate_recommendations(self, async_check, websocket_check, error_summary) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []
        
        if async_check['has_sync_only_errors']:
            recommendations.append(
                "CRITICAL: SynchronousOnlyOperation errors detected. "
                "Check that all database operations in async contexts use database_sync_to_async."
            )
        
        if async_check['count'] > 5:
            recommendations.append(
                "High number of async context errors. "
                "Review async/await usage in WebSocket consumers."
            )
        
        if websocket_check['count'] > 10:
            recommendations.append(
                "High number of WebSocket errors. "
                "Check connection stability and error handling."
            )
        
        if error_summary.get('json_serialization', 0) > 5:
            recommendations.append(
                "JSON serialization errors detected. "
                "Check data types being serialized in WebSocket messages."
            )
        
        if not recommendations:
            recommendations.append("System appears healthy. Continue monitoring.")
        
        return recommendations
    
    def log_health_report(self):
        """Log the current health report"""
        report = self.generate_health_report()
        
        log_level = logging.INFO
        if report['status'] == 'critical':
            log_level = logging.ERROR
        elif report['status'] == 'warning':
            log_level = logging.WARNING
        
        logger.log(
            log_level,
            f"Messaging System Health Report - Status: {report['status']} "
            f"(Score: {report['health_score']}/100)",
            extra={
                'health_report': report,
                'error_summary': report['error_summary'],
                'recommendations': report['recommendations']
            }
        )
        
        return report


# Global monitor instance
error_monitor = MessagingErrorMonitor()


def get_health_status() -> Dict[str, any]:
    """Get current health status - convenience function"""
    return error_monitor.generate_health_report()


def log_current_health():
    """Log current health status - convenience function"""
    return error_monitor.log_health_report()
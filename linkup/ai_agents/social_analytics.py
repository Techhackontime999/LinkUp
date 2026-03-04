"""
Analytics and Monitoring Service for AI Agent Social Platform.

Provides:
- Metrics collection and export (Prometheus format)
- Error tracking and logging
- Platform usage analytics
- Alert threshold monitoring
"""
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Avg, Sum, Q
from .models import AIAgent
from .social_models import (
    AgentPost, AgentComment, AgentReaction, AgentFollow,
    AgentNotification, AgentCollaborationSpace, AgentCapabilityListing
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and exports platform metrics in Prometheus format.
    """
    
    @staticmethod
    def collect_api_metrics() -> Dict[str, Any]:
        """
        Collect API request metrics from cache.
        
        Returns:
            Dict with API metrics
        """
        # Get metrics from cache (would be populated by middleware)
        metrics = {
            'total_requests': cache.get('metrics:api:total_requests', 0),
            'successful_requests': cache.get('metrics:api:successful_requests', 0),
            'failed_requests': cache.get('metrics:api:failed_requests', 0),
            'avg_response_time_ms': cache.get('metrics:api:avg_response_time', 0),
            'requests_per_endpoint': cache.get('metrics:api:per_endpoint', {}),
        }
        
        return metrics
    
    @staticmethod
    def collect_platform_metrics() -> Dict[str, Any]:
        """
        Collect platform-wide metrics.
        
        Returns:
            Dict with platform metrics
        """
        # Count active agents
        active_agents = AIAgent.objects.filter(
            is_active=True,
            is_suspended=False
        ).count()
        
        # Count content
        total_posts = AgentPost.objects.filter(is_deleted=False).count()
        total_comments = AgentComment.objects.filter(is_deleted=False).count()
        total_reactions = AgentReaction.objects.count()
        
        # Count relationships
        total_follows = AgentFollow.objects.count()
        
        # Count spaces and listings
        total_spaces = AgentCollaborationSpace.objects.count()
        total_listings = AgentCapabilityListing.objects.filter(is_active=True).count()
        
        # Count notifications
        unread_notifications = AgentNotification.objects.filter(is_read=False).count()
        
        return {
            'active_agents': active_agents,
            'total_posts': total_posts,
            'total_comments': total_comments,
            'total_reactions': total_reactions,
            'total_follows': total_follows,
            'total_spaces': total_spaces,
            'total_listings': total_listings,
            'unread_notifications': unread_notifications,
        }
    
    @staticmethod
    def export_prometheus_metrics() -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        api_metrics = MetricsCollector.collect_api_metrics()
        platform_metrics = MetricsCollector.collect_platform_metrics()
        
        lines = [
            '# HELP social_platform_active_agents Number of active agents',
            '# TYPE social_platform_active_agents gauge',
            f'social_platform_active_agents {platform_metrics["active_agents"]}',
            '',
            '# HELP social_platform_total_posts Total number of posts',
            '# TYPE social_platform_total_posts gauge',
            f'social_platform_total_posts {platform_metrics["total_posts"]}',
            '',
            '# HELP social_platform_total_comments Total number of comments',
            '# TYPE social_platform_total_comments gauge',
            f'social_platform_total_comments {platform_metrics["total_comments"]}',
            '',
            '# HELP social_platform_total_reactions Total number of reactions',
            '# TYPE social_platform_total_reactions gauge',
            f'social_platform_total_reactions {platform_metrics["total_reactions"]}',
            '',
            '# HELP social_platform_api_requests_total Total API requests',
            '# TYPE social_platform_api_requests_total counter',
            f'social_platform_api_requests_total {api_metrics["total_requests"]}',
            '',
            '# HELP social_platform_api_response_time_ms Average API response time',
            '# TYPE social_platform_api_response_time_ms gauge',
            f'social_platform_api_response_time_ms {api_metrics["avg_response_time_ms"]}',
            '',
        ]
        
        return '\n'.join(lines)


class ErrorTracker:
    """
    Tracks and logs errors for monitoring.
    """
    
    @staticmethod
    def log_error(
        error_type: str,
        message: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict] = None
    ):
        """
        Log an error with context.
        
        Args:
            error_type: Type of error
            message: Error message
            stack_trace: Stack trace if available
            context: Additional context
        """
        error_entry = {
            'error_type': error_type,
            'message': message,
            'stack_trace': stack_trace,
            'context': context or {},
            'timestamp': timezone.now().isoformat()
        }
        
        # Log to Django logger
        logger.error(f"{error_type}: {message}", extra=error_entry)
        
        # Store in cache for recent errors
        cache_key = 'errors:recent'
        recent_errors = cache.get(cache_key, [])
        recent_errors.append(error_entry)
        
        # Keep only last 100 errors
        if len(recent_errors) > 100:
            recent_errors = recent_errors[-100:]
        
        cache.set(cache_key, recent_errors, timeout=3600)  # 1 hour
        
        # Increment error counter
        error_count_key = f'metrics:errors:{error_type}'
        cache.incr(error_count_key, 1)
    
    @staticmethod
    def get_recent_errors(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent errors.
        
        Args:
            limit: Maximum number of errors to return
        
        Returns:
            List of recent errors
        """
        cache_key = 'errors:recent'
        recent_errors = cache.get(cache_key, [])
        return recent_errors[-limit:][::-1]  # Most recent first
    
    @staticmethod
    def get_error_counts() -> Dict[str, int]:
        """
        Get error counts by type.
        
        Returns:
            Dict mapping error types to counts
        """
        # Get all error count keys from cache
        # This is a simplified version - in production, use a proper metrics store
        error_types = [
            'authentication_error',
            'validation_error',
            'database_error',
            'rate_limit_error',
            'not_found_error',
            'permission_error',
        ]
        
        counts = {}
        for error_type in error_types:
            key = f'metrics:errors:{error_type}'
            counts[error_type] = cache.get(key, 0)
        
        return counts


class AnalyticsService:
    """
    Provides platform usage analytics and insights.
    """
    
    @staticmethod
    def get_agent_activity_metrics(agent_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get activity metrics for a specific agent.
        
        Args:
            agent_id: UUID of the agent
            days: Number of days to analyze
        
        Returns:
            Dict with activity metrics
        """
        since = timezone.now() - timedelta(days=days)
        
        try:
            agent = AIAgent.objects.get(id=agent_id)
        except AIAgent.DoesNotExist:
            return {'error': 'Agent not found'}
        
        # Count posts
        posts_count = AgentPost.objects.filter(
            agent_id=agent_id,
            created_at__gte=since,
            is_deleted=False
        ).count()
        
        # Count comments
        comments_count = AgentComment.objects.filter(
            agent_id=agent_id,
            created_at__gte=since,
            is_deleted=False
        ).count()
        
        # Count reactions given
        reactions_given = AgentReaction.objects.filter(
            agent_id=agent_id,
            created_at__gte=since
        ).count()
        
        # Count reactions received on posts
        reactions_received = AgentReaction.objects.filter(
            post__agent_id=agent_id,
            created_at__gte=since
        ).count()
        
        # Count new followers
        new_followers = AgentFollow.objects.filter(
            followed_id=agent_id,
            created_at__gte=since
        ).count()
        
        # Count new following
        new_following = AgentFollow.objects.filter(
            follower_id=agent_id,
            created_at__gte=since
        ).count()
        
        return {
            'agent_id': str(agent_id),
            'agent_name': agent.name,
            'period_days': days,
            'posts_created': posts_count,
            'comments_created': comments_count,
            'reactions_given': reactions_given,
            'reactions_received': reactions_received,
            'new_followers': new_followers,
            'new_following': new_following,
            'total_activity': posts_count + comments_count + reactions_given,
        }
    
    @staticmethod
    def get_platform_summary(days: int = 7) -> Dict[str, Any]:
        """
        Get platform-wide summary statistics.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dict with platform summary
        """
        since = timezone.now() - timedelta(days=days)
        
        # New agents
        new_agents = AIAgent.objects.filter(
            created_at__gte=since,
            is_active=True
        ).count()
        
        # New posts
        new_posts = AgentPost.objects.filter(
            created_at__gte=since,
            is_deleted=False
        ).count()
        
        # New comments
        new_comments = AgentComment.objects.filter(
            created_at__gte=since,
            is_deleted=False
        ).count()
        
        # New reactions
        new_reactions = AgentReaction.objects.filter(
            created_at__gte=since
        ).count()
        
        # New follows
        new_follows = AgentFollow.objects.filter(
            created_at__gte=since
        ).count()
        
        # Active agents (posted or commented in period)
        active_agents = AIAgent.objects.filter(
            Q(agentpost__created_at__gte=since) |
            Q(agentcomment__created_at__gte=since)
        ).distinct().count()
        
        return {
            'period_days': days,
            'new_agents': new_agents,
            'active_agents': active_agents,
            'new_posts': new_posts,
            'new_comments': new_comments,
            'new_reactions': new_reactions,
            'new_follows': new_follows,
            'total_engagement': new_posts + new_comments + new_reactions,
        }
    
    @staticmethod
    def get_trending_content(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending posts based on recent engagement.
        
        Args:
            limit: Maximum number of posts to return
        
        Returns:
            List of trending posts
        """
        # Get posts from last 7 days
        since = timezone.now() - timedelta(days=7)
        
        trending_posts = AgentPost.objects.filter(
            created_at__gte=since,
            is_deleted=False,
            visibility='PUBLIC'
        ).annotate(
            engagement_score=Count('agentreaction') + Count('agentcomment') * 2
        ).order_by('-engagement_score')[:limit]
        
        results = []
        for post in trending_posts:
            results.append({
                'post_id': str(post.id),
                'agent_id': str(post.agent_id),
                'agent_name': post.agent.name,
                'post_type': post.post_type,
                'content_preview': post.content[:100] + '...' if len(post.content) > 100 else post.content,
                'reaction_count': post.reaction_count,
                'comment_count': post.comment_count,
                'created_at': post.created_at.isoformat(),
            })
        
        return results


class AlertManager:
    """
    Manages alert thresholds and notifications.
    """
    
    # Default thresholds
    THRESHOLDS = {
        'error_rate': 0.05,  # 5% error rate
        'avg_response_time_ms': 1000,  # 1 second
        'failed_requests_per_minute': 50,
        'cache_miss_rate': 0.5,  # 50% cache miss rate
    }
    
    @staticmethod
    def check_thresholds() -> List[Dict[str, Any]]:
        """
        Check if any metrics exceed thresholds.
        
        Returns:
            List of alerts
        """
        alerts = []
        
        # Check error rate
        api_metrics = MetricsCollector.collect_api_metrics()
        total_requests = api_metrics['total_requests']
        failed_requests = api_metrics['failed_requests']
        
        if total_requests > 0:
            error_rate = failed_requests / total_requests
            if error_rate > AlertManager.THRESHOLDS['error_rate']:
                alerts.append({
                    'type': 'error_rate',
                    'severity': 'high',
                    'message': f'Error rate is {error_rate:.2%}, threshold is {AlertManager.THRESHOLDS["error_rate"]:.2%}',
                    'current_value': error_rate,
                    'threshold': AlertManager.THRESHOLDS['error_rate'],
                    'timestamp': timezone.now().isoformat()
                })
        
        # Check response time
        avg_response_time = api_metrics['avg_response_time_ms']
        if avg_response_time > AlertManager.THRESHOLDS['avg_response_time_ms']:
            alerts.append({
                'type': 'response_time',
                'severity': 'medium',
                'message': f'Average response time is {avg_response_time}ms, threshold is {AlertManager.THRESHOLDS["avg_response_time_ms"]}ms',
                'current_value': avg_response_time,
                'threshold': AlertManager.THRESHOLDS['avg_response_time_ms'],
                'timestamp': timezone.now().isoformat()
            })
        
        # Store alerts in cache
        if alerts:
            cache_key = 'alerts:active'
            existing_alerts = cache.get(cache_key, [])
            existing_alerts.extend(alerts)
            cache.set(cache_key, existing_alerts, timeout=3600)  # 1 hour
        
        return alerts
    
    @staticmethod
    def get_active_alerts() -> List[Dict[str, Any]]:
        """
        Get currently active alerts.
        
        Returns:
            List of active alerts
        """
        cache_key = 'alerts:active'
        return cache.get(cache_key, [])
    
    @staticmethod
    def acknowledge_alert(alert_timestamp: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_timestamp: Timestamp of the alert to acknowledge
        
        Returns:
            True if acknowledged, False otherwise
        """
        cache_key = 'alerts:active'
        alerts = cache.get(cache_key, [])
        
        # Remove alert with matching timestamp
        updated_alerts = [a for a in alerts if a['timestamp'] != alert_timestamp]
        
        if len(updated_alerts) < len(alerts):
            cache.set(cache_key, updated_alerts, timeout=3600)
            return True
        
        return False

"""
Dashboard statistics service for admin panel
"""
from django.utils import timezone
from django.contrib.admin.models import LogEntry
from django.core.cache import cache
from django.db.models import Count, Q
from datetime import timedelta
from typing import Dict, List


class DashboardStats:
    """Service class for calculating and caching dashboard statistics"""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def get_user_stats() -> Dict[str, int]:
        """
        Returns total users, new users (30 days), active users
        
        Returns:
            Dict with user statistics
        """
        cache_key = 'admin_dashboard_user_stats'
        stats = cache.get(cache_key)
        
        if stats is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            stats = {
                'total': User.objects.count(),
                'new_30_days': User.objects.filter(date_joined__gte=thirty_days_ago).count(),
                'active': User.objects.filter(is_active=True).count(),
                'staff': User.objects.filter(is_staff=True).count(),
            }
            
            cache.set(cache_key, stats, DashboardStats.CACHE_TIMEOUT)
        
        return stats
    
    @staticmethod
    def get_content_stats() -> Dict[str, int]:
        """
        Returns total posts, new posts (30 days), total comments
        
        Returns:
            Dict with content statistics
        """
        cache_key = 'admin_dashboard_content_stats'
        stats = cache.get(cache_key)
        
        if stats is None:
            try:
                from feed.models import Post, Comment
                
                thirty_days_ago = timezone.now() - timedelta(days=30)
                
                stats = {
                    'total_posts': Post.objects.count(),
                    'new_posts_30_days': Post.objects.filter(created_at__gte=thirty_days_ago).count(),
                    'total_comments': Comment.objects.count(),
                    'new_comments_30_days': Comment.objects.filter(created_at__gte=thirty_days_ago).count(),
                }
            except Exception:
                stats = {
                    'total_posts': 0,
                    'new_posts_30_days': 0,
                    'total_comments': 0,
                    'new_comments_30_days': 0,
                }
            
            cache.set(cache_key, stats, DashboardStats.CACHE_TIMEOUT)
        
        return stats
    
    @staticmethod
    def get_job_stats() -> Dict[str, int]:
        """
        Returns total jobs, active jobs, total applications
        
        Returns:
            Dict with job statistics
        """
        cache_key = 'admin_dashboard_job_stats'
        stats = cache.get(cache_key)
        
        if stats is None:
            try:
                from jobs.models import Job, Application
                
                thirty_days_ago = timezone.now() - timedelta(days=30)
                
                stats = {
                    'total_jobs': Job.objects.count(),
                    'active_jobs': Job.objects.filter(is_active=True).count(),
                    'total_applications': Application.objects.count(),
                    'new_applications_30_days': Application.objects.filter(applied_at__gte=thirty_days_ago).count(),
                }
            except Exception:
                stats = {
                    'total_jobs': 0,
                    'active_jobs': 0,
                    'total_applications': 0,
                    'new_applications_30_days': 0,
                }
            
            cache.set(cache_key, stats, DashboardStats.CACHE_TIMEOUT)
        
        return stats
    
    @staticmethod
    def get_network_stats() -> Dict[str, int]:
        """
        Returns total connections, pending connections, total follows
        
        Returns:
            Dict with network statistics
        """
        cache_key = 'admin_dashboard_network_stats'
        stats = cache.get(cache_key)
        
        if stats is None:
            try:
                from network.models import Connection, Follow
                
                stats = {
                    'total_connections': Connection.objects.count(),
                    'pending_connections': Connection.objects.filter(status='pending').count(),
                    'accepted_connections': Connection.objects.filter(status='accepted').count(),
                    'total_follows': Follow.objects.count(),
                }
            except Exception:
                stats = {
                    'total_connections': 0,
                    'pending_connections': 0,
                    'accepted_connections': 0,
                    'total_follows': 0,
                }
            
            cache.set(cache_key, stats, DashboardStats.CACHE_TIMEOUT)
        
        return stats
    
    @staticmethod
    def get_recent_actions(limit: int = 10):
        """
        Returns recent admin log entries
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            QuerySet of recent LogEntry objects
        """
        return LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:limit]
    
    @staticmethod
    def get_chart_data() -> Dict[str, List]:
        """
        Returns time-series data for charts
        
        Returns:
            Dict with chart data for users, posts, and applications
        """
        cache_key = 'admin_dashboard_chart_data'
        data = cache.get(cache_key)
        
        if data is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get data for last 30 days
            days = []
            user_counts = []
            post_counts = []
            
            for i in range(29, -1, -1):
                date = timezone.now().date() - timedelta(days=i)
                days.append(date.strftime('%m/%d'))
                
                # User registrations
                user_count = User.objects.filter(
                    date_joined__date=date
                ).count()
                user_counts.append(user_count)
                
                # Post creations
                try:
                    from feed.models import Post
                    post_count = Post.objects.filter(
                        created_at__date=date
                    ).count()
                    post_counts.append(post_count)
                except Exception:
                    post_counts.append(0)
            
            data = {
                'labels': days,
                'user_registrations': user_counts,
                'post_creations': post_counts,
            }
            
            cache.set(cache_key, data, DashboardStats.CACHE_TIMEOUT)
        
        return data
    
    @staticmethod
    def clear_cache():
        """Clear all dashboard statistics cache"""
        cache_keys = [
            'admin_dashboard_user_stats',
            'admin_dashboard_content_stats',
            'admin_dashboard_job_stats',
            'admin_dashboard_network_stats',
            'admin_dashboard_chart_data',
        ]
        for key in cache_keys:
            cache.delete(key)

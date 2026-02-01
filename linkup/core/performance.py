"""
Performance optimization utilities for the professional network platform.
Implements query optimization, caching strategies, and performance monitoring.
"""

import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Utility class for optimizing database queries and preventing N+1 problems.
    """
    
    @staticmethod
    def optimize_user_queries(queryset):
        """
        Optimize user-related queries with proper select_related and prefetch_related.
        """
        return queryset.select_related('profile').prefetch_related(
            'experiences',
            'educations',
            'sent_messages',
            'received_messages'
        )
    
    @staticmethod
    def optimize_message_queries(queryset):
        """
        Optimize message queries to prevent N+1 problems.
        """
        return queryset.select_related(
            'sender',
            'sender__profile',
            'recipient',
            'recipient__profile'
        ).prefetch_related(
            'sender__experiences',
            'recipient__experiences'
        )
    
    @staticmethod
    def optimize_notification_queries(queryset):
        """
        Optimize notification queries with proper relationships.
        """
        return queryset.select_related(
            'recipient',
            'recipient__profile',
            'sender',
            'sender__profile',
            'content_type'
        )
    
    @staticmethod
    def optimize_job_queries(queryset):
        """
        Optimize job-related queries.
        """
        return queryset.select_related(
            'company',
            'posted_by',
            'posted_by__profile'
        ).prefetch_related(
            'applications',
            'applications__applicant',
            'applications__applicant__profile'
        )
    
    @staticmethod
    def optimize_feed_queries(queryset):
        """
        Optimize feed/post queries for better performance.
        """
        return queryset.select_related(
            'author',
            'author__profile'
        ).prefetch_related(
            'likes',
            'likes__user',
            'comments',
            'comments__author',
            'comments__author__profile'
        )


class CacheManager:
    """
    Centralized cache management for the application.
    """
    
    # Cache timeout configurations (in seconds)
    CACHE_TIMEOUTS = {
        'user_profile': 300,      # 5 minutes
        'user_stats': 600,        # 10 minutes
        'feed_posts': 180,        # 3 minutes
        'notifications': 60,      # 1 minute
        'search_results': 300,    # 5 minutes
        'job_listings': 600,      # 10 minutes
        'static_content': 3600,   # 1 hour
    }
    
    @classmethod
    def get_cache_key(cls, prefix, *args):
        """Generate consistent cache keys."""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    @classmethod
    def cache_user_profile(cls, user_id, profile_data):
        """Cache user profile data."""
        cache_key = cls.get_cache_key('user_profile', user_id)
        cache.set(cache_key, profile_data, cls.CACHE_TIMEOUTS['user_profile'])
    
    @classmethod
    def get_cached_user_profile(cls, user_id):
        """Get cached user profile data."""
        cache_key = cls.get_cache_key('user_profile', user_id)
        return cache.get(cache_key)
    
    @classmethod
    def invalidate_user_cache(cls, user_id):
        """Invalidate all cache entries for a user."""
        patterns = [
            cls.get_cache_key('user_profile', user_id),
            cls.get_cache_key('user_stats', user_id),
            cls.get_cache_key('feed_posts', user_id),
        ]
        for pattern in patterns:
            cache.delete(pattern)
    
    @classmethod
    def cache_search_results(cls, query, results):
        """Cache search results."""
        cache_key = cls.get_cache_key('search_results', query)
        cache.set(cache_key, results, cls.CACHE_TIMEOUTS['search_results'])
    
    @classmethod
    def get_cached_search_results(cls, query):
        """Get cached search results."""
        cache_key = cls.get_cache_key('search_results', query)
        return cache.get(cache_key)


def performance_monitor(func):
    """
    Decorator to monitor function performance and log slow operations.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Count initial queries
        initial_queries = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            
            # Calculate performance metrics
            execution_time = time.time() - start_time
            query_count = len(connection.queries) - initial_queries
            
            # Log performance data
            if execution_time > 1.0 or query_count > 10:  # Slow operation thresholds
                logger.warning(
                    f"Slow operation detected - Function: {func.__name__}, "
                    f"Time: {execution_time:.2f}s, Queries: {query_count}"
                )
            else:
                logger.debug(
                    f"Performance - Function: {func.__name__}, "
                    f"Time: {execution_time:.2f}s, Queries: {query_count}"
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Error in {func.__name__} after {execution_time:.2f}s: {str(e)}"
            )
            raise
    
    return wrapper


def cache_result(timeout=300, key_prefix=''):
    """
    Decorator to cache function results.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            
            return result
        return wrapper
    return decorator


class OptimizedPaginator:
    """
    Optimized paginator that uses efficient counting and query optimization.
    """
    
    def __init__(self, queryset, per_page=25, optimize_func=None):
        self.queryset = queryset
        self.per_page = per_page
        self.optimize_func = optimize_func
    
    def get_page(self, page_number):
        """Get optimized page with efficient counting."""
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = 1
        
        # Apply query optimization if provided
        if self.optimize_func:
            optimized_queryset = self.optimize_func(self.queryset)
        else:
            optimized_queryset = self.queryset
        
        # Use Django's paginator with optimizations
        paginator = Paginator(optimized_queryset, self.per_page)
        
        try:
            page = paginator.page(page_number)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        
        return page
    
    def get_page_data(self, page_number):
        """Get page data with metadata for API responses."""
        page = self.get_page(page_number)
        
        return {
            'results': list(page.object_list.values()),
            'pagination': {
                'current_page': page.number,
                'total_pages': page.paginator.num_pages,
                'total_items': page.paginator.count,
                'per_page': self.per_page,
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
                'next_page': page.next_page_number() if page.has_next() else None,
                'previous_page': page.previous_page_number() if page.has_previous() else None,
            }
        }


class DatabaseOptimizer:
    """
    Database optimization utilities and query analysis.
    """
    
    @staticmethod
    def analyze_queries():
        """Analyze recent queries for optimization opportunities."""
        if not settings.DEBUG:
            return "Query analysis only available in DEBUG mode"
        
        queries = connection.queries
        
        # Analyze query patterns
        slow_queries = [q for q in queries if float(q['time']) > 0.1]
        duplicate_queries = {}
        
        for query in queries:
            sql = query['sql']
            if sql in duplicate_queries:
                duplicate_queries[sql] += 1
            else:
                duplicate_queries[sql] = 1
        
        duplicates = {sql: count for sql, count in duplicate_queries.items() if count > 1}
        
        return {
            'total_queries': len(queries),
            'slow_queries': len(slow_queries),
            'duplicate_queries': len(duplicates),
            'slowest_query': max(queries, key=lambda x: float(x['time'])) if queries else None,
            'duplicates': duplicates
        }
    
    @staticmethod
    def get_query_stats():
        """Get database query statistics."""
        return {
            'query_count': len(connection.queries),
            'total_time': sum(float(q['time']) for q in connection.queries),
            'average_time': sum(float(q['time']) for q in connection.queries) / len(connection.queries) if connection.queries else 0
        }


def optimize_static_files():
    """
    Optimize static file serving with proper caching headers.
    """
    def decorator(view_func):
        @wraps(view_func)
        @cache_page(3600)  # Cache for 1 hour
        @vary_on_headers('Accept-Encoding')
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Add caching headers for static content
            response['Cache-Control'] = 'public, max-age=3600'
            response['Expires'] = time.strftime(
                '%a, %d %b %Y %H:%M:%S GMT',
                time.gmtime(time.time() + 3600)
            )
            
            return response
        return wrapper
    return decorator


class PerformanceMiddleware:
    """
    Middleware to monitor and optimize performance across requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Start timing
        start_time = time.time()
        initial_queries = len(connection.queries)
        
        # Process request
        response = self.get_response(request)
        
        # Calculate metrics
        execution_time = time.time() - start_time
        query_count = len(connection.queries) - initial_queries
        
        # Add performance headers (for debugging)
        if settings.DEBUG:
            response['X-Execution-Time'] = f"{execution_time:.3f}s"
            response['X-Query-Count'] = str(query_count)
        
        # Log slow requests
        if execution_time > 2.0 or query_count > 20:
            logger.warning(
                f"Slow request: {request.path} - "
                f"Time: {execution_time:.2f}s, Queries: {query_count}"
            )
        
        return response


# Utility functions for common optimizations

def bulk_create_optimized(model_class, objects, batch_size=1000):
    """
    Optimized bulk create with batching.
    """
    created_objects = []
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        created_objects.extend(model_class.objects.bulk_create(batch))
    return created_objects


def bulk_update_optimized(objects, fields, batch_size=1000):
    """
    Optimized bulk update with batching.
    """
    from django.db import models
    
    if not objects:
        return
    
    model_class = objects[0].__class__
    
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        model_class.objects.bulk_update(batch, fields)


@cache_result(timeout=600, key_prefix='stats')
def get_dashboard_stats(user_id):
    """
    Get cached dashboard statistics for a user.
    """
    from django.contrib.auth import get_user_model
    from messaging.models import Message, Notification
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        
        stats = {
            'unread_messages': Message.objects.filter(recipient=user, is_read=False).count(),
            'unread_notifications': Notification.objects.filter(recipient=user, is_read=False).count(),
            'total_connections': user.connections.count() if hasattr(user, 'connections') else 0,
            'profile_completeness': calculate_profile_completeness(user),
        }
        
        return stats
    except User.DoesNotExist:
        return {}


def calculate_profile_completeness(user):
    """
    Calculate profile completeness percentage.
    """
    if not hasattr(user, 'profile'):
        return 0
    
    profile = user.profile
    fields_to_check = ['headline', 'bio', 'location', 'avatar']
    completed_fields = sum(1 for field in fields_to_check if getattr(profile, field))
    
    # Add experience and education
    has_experience = user.experiences.exists()
    has_education = user.educations.exists()
    
    total_sections = len(fields_to_check) + 2  # +2 for experience and education
    completed_sections = completed_fields + (1 if has_experience else 0) + (1 if has_education else 0)
    
    return int((completed_sections / total_sections) * 100)
"""
Caching utilities for AI Agent Social Platform.

Provides Redis-based caching with TTL management and cache invalidation.
"""
import logging
from typing import Optional, Any, Callable
from functools import wraps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class SocialCache:
    """
    Caching service for social platform data.
    
    Provides methods for caching profiles, feeds, reputation scores, etc.
    with automatic TTL management and cache invalidation.
    """
    
    # Cache TTL values (in seconds)
    TTL_PROFILE = 900  # 15 minutes
    TTL_FEED = 300  # 5 minutes
    TTL_REPUTATION = 3600  # 1 hour
    TTL_POST = 600  # 10 minutes
    TTL_DISCOVERY = 1800  # 30 minutes
    
    # Cache key prefixes
    PREFIX_PROFILE = 'social:profile:'
    PREFIX_FEED = 'social:feed:'
    PREFIX_REPUTATION = 'social:reputation:'
    PREFIX_POST = 'social:post:'
    PREFIX_DISCOVERY = 'social:discovery:'
    
    @staticmethod
    def get_profile(agent_id: str) -> Optional[dict]:
        """
        Get cached profile data.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Profile dict or None if not cached
        """
        cache_key = f'{SocialCache.PREFIX_PROFILE}{agent_id}'
        return cache.get(cache_key)
    
    @staticmethod
    def set_profile(agent_id: str, profile_data: dict) -> bool:
        """
        Cache profile data.
        
        Args:
            agent_id: UUID of the agent
            profile_data: Profile data dict
        
        Returns:
            True if cached successfully
        """
        cache_key = f'{SocialCache.PREFIX_PROFILE}{agent_id}'
        try:
            cache.set(cache_key, profile_data, timeout=SocialCache.TTL_PROFILE)
            logger.debug(f"Cached profile for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error caching profile: {e}")
            return False
    
    @staticmethod
    def invalidate_profile(agent_id: str) -> bool:
        """
        Invalidate cached profile data.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            True if invalidated successfully
        """
        cache_key = f'{SocialCache.PREFIX_PROFILE}{agent_id}'
        try:
            cache.delete(cache_key)
            logger.debug(f"Invalidated profile cache for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating profile cache: {e}")
            return False
    
    @staticmethod
    def get_feed(agent_id: str, page: int = 1) -> Optional[dict]:
        """
        Get cached feed data.
        
        Args:
            agent_id: UUID of the agent
            page: Page number
        
        Returns:
            Feed dict or None if not cached
        """
        cache_key = f'{SocialCache.PREFIX_FEED}{agent_id}:page:{page}'
        return cache.get(cache_key)
    
    @staticmethod
    def set_feed(agent_id: str, feed_data: dict, page: int = 1) -> bool:
        """
        Cache feed data.
        
        Args:
            agent_id: UUID of the agent
            feed_data: Feed data dict
            page: Page number
        
        Returns:
            True if cached successfully
        """
        cache_key = f'{SocialCache.PREFIX_FEED}{agent_id}:page:{page}'
        try:
            cache.set(cache_key, feed_data, timeout=SocialCache.TTL_FEED)
            logger.debug(f"Cached feed for agent {agent_id} page {page}")
            return True
        except Exception as e:
            logger.error(f"Error caching feed: {e}")
            return False
    
    @staticmethod
    def invalidate_feed(agent_id: str) -> bool:
        """
        Invalidate all cached feed pages for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            True if invalidated successfully
        """
        try:
            # Invalidate first 10 pages (reasonable limit)
            for page in range(1, 11):
                cache_key = f'{SocialCache.PREFIX_FEED}{agent_id}:page:{page}'
                cache.delete(cache_key)
            
            logger.debug(f"Invalidated feed cache for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating feed cache: {e}")
            return False
    
    @staticmethod
    def get_reputation(agent_id: str) -> Optional[dict]:
        """
        Get cached reputation data.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Reputation dict or None if not cached
        """
        cache_key = f'{SocialCache.PREFIX_REPUTATION}{agent_id}'
        return cache.get(cache_key)
    
    @staticmethod
    def set_reputation(agent_id: str, reputation_data: dict) -> bool:
        """
        Cache reputation data.
        
        Args:
            agent_id: UUID of the agent
            reputation_data: Reputation data dict
        
        Returns:
            True if cached successfully
        """
        cache_key = f'{SocialCache.PREFIX_REPUTATION}{agent_id}'
        try:
            cache.set(cache_key, reputation_data, timeout=SocialCache.TTL_REPUTATION)
            logger.debug(f"Cached reputation for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error caching reputation: {e}")
            return False
    
    @staticmethod
    def invalidate_reputation(agent_id: str) -> bool:
        """
        Invalidate cached reputation data.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            True if invalidated successfully
        """
        cache_key = f'{SocialCache.PREFIX_REPUTATION}{agent_id}'
        try:
            cache.delete(cache_key)
            logger.debug(f"Invalidated reputation cache for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating reputation cache: {e}")
            return False
    
    @staticmethod
    def get_post(post_id: str) -> Optional[dict]:
        """
        Get cached post data.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            Post dict or None if not cached
        """
        cache_key = f'{SocialCache.PREFIX_POST}{post_id}'
        return cache.get(cache_key)
    
    @staticmethod
    def set_post(post_id: str, post_data: dict) -> bool:
        """
        Cache post data.
        
        Args:
            post_id: UUID of the post
            post_data: Post data dict
        
        Returns:
            True if cached successfully
        """
        cache_key = f'{SocialCache.PREFIX_POST}{post_id}'
        try:
            cache.set(cache_key, post_data, timeout=SocialCache.TTL_POST)
            logger.debug(f"Cached post {post_id}")
            return True
        except Exception as e:
            logger.error(f"Error caching post: {e}")
            return False
    
    @staticmethod
    def invalidate_post(post_id: str) -> bool:
        """
        Invalidate cached post data.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            True if invalidated successfully
        """
        cache_key = f'{SocialCache.PREFIX_POST}{post_id}'
        try:
            cache.delete(cache_key)
            logger.debug(f"Invalidated post cache {post_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating post cache: {e}")
            return False
    
    @staticmethod
    def warm_popular_profiles(agent_ids: list) -> int:
        """
        Warm cache for popular profiles.
        
        Args:
            agent_ids: List of agent UUIDs
        
        Returns:
            Number of profiles cached
        """
        from .social_services import SocialProfileService
        
        cached_count = 0
        for agent_id in agent_ids:
            try:
                profile_data = SocialProfileService.get_profile(agent_id)
                if profile_data:
                    SocialCache.set_profile(agent_id, profile_data)
                    cached_count += 1
            except Exception as e:
                logger.error(f"Error warming cache for profile {agent_id}: {e}")
        
        logger.info(f"Warmed cache for {cached_count} profiles")
        return cached_count


def cache_result(cache_key_func: Callable, ttl: int = 300):
    """
    Decorator for caching function results.
    
    Args:
        cache_key_func: Function that generates cache key from function args
        ttl: Time to live in seconds
    
    Example:
        @cache_result(lambda agent_id: f'profile:{agent_id}', ttl=900)
        def get_profile(agent_id):
            # expensive operation
            return profile_data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_key_func(*args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss - call function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                cache.set(cache_key, result, timeout=ttl)
            
            return result
        
        return wrapper
    return decorator

"""
Engagement Metrics Consistency Service for AI Agent Social Platform.

Provides:
- Atomic counter updates
- Metrics reconciliation
- Consistency verification
"""
import logging
from typing import Dict, Any, List
from django.db import transaction
from django.db.models import Count
from .models import AIAgent
from .social_models import AgentPost, AgentComment, AgentReaction, AgentSocialProfile

logger = logging.getLogger(__name__)


class MetricsUpdateService:
    """
    Service for atomic counter updates and consistency maintenance.
    """
    
    @staticmethod
    @transaction.atomic
    def increment_post_reaction_count(post_id: str) -> bool:
        """
        Atomically increment post reaction count.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            True if successful
        """
        try:
            post = AgentPost.objects.select_for_update().get(id=post_id)
            post.reaction_count += 1
            post.save(update_fields=['reaction_count'])
            return True
        except AgentPost.DoesNotExist:
            logger.error(f"Post {post_id} not found for reaction count increment")
            return False
    
    @staticmethod
    @transaction.atomic
    def decrement_post_reaction_count(post_id: str) -> bool:
        """
        Atomically decrement post reaction count.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            True if successful
        """
        try:
            post = AgentPost.objects.select_for_update().get(id=post_id)
            post.reaction_count = max(0, post.reaction_count - 1)
            post.save(update_fields=['reaction_count'])
            return True
        except AgentPost.DoesNotExist:
            logger.error(f"Post {post_id} not found for reaction count decrement")
            return False
    
    @staticmethod
    @transaction.atomic
    def increment_post_comment_count(post_id: str) -> bool:
        """
        Atomically increment post comment count.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            True if successful
        """
        try:
            post = AgentPost.objects.select_for_update().get(id=post_id)
            post.comment_count += 1
            post.save(update_fields=['comment_count'])
            return True
        except AgentPost.DoesNotExist:
            logger.error(f"Post {post_id} not found for comment count increment")
            return False
    
    @staticmethod
    @transaction.atomic
    def decrement_post_comment_count(post_id: str) -> bool:
        """
        Atomically decrement post comment count.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            True if successful
        """
        try:
            post = AgentPost.objects.select_for_update().get(id=post_id)
            post.comment_count = max(0, post.comment_count - 1)
            post.save(update_fields=['comment_count'])
            return True
        except AgentPost.DoesNotExist:
            logger.error(f"Post {post_id} not found for comment count decrement")
            return False
    
    @staticmethod
    @transaction.atomic
    def increment_comment_reaction_count(comment_id: str) -> bool:
        """
        Atomically increment comment reaction count.
        
        Args:
            comment_id: UUID of the comment
        
        Returns:
            True if successful
        """
        try:
            comment = AgentComment.objects.select_for_update().get(id=comment_id)
            comment.reaction_count += 1
            comment.save(update_fields=['reaction_count'])
            return True
        except AgentComment.DoesNotExist:
            logger.error(f"Comment {comment_id} not found for reaction count increment")
            return False
    
    @staticmethod
    @transaction.atomic
    def decrement_comment_reaction_count(comment_id: str) -> bool:
        """
        Atomically decrement comment reaction count.
        
        Args:
            comment_id: UUID of the comment
        
        Returns:
            True if successful
        """
        try:
            comment = AgentComment.objects.select_for_update().get(id=comment_id)
            comment.reaction_count = max(0, comment.reaction_count - 1)
            comment.save(update_fields=['reaction_count'])
            return True
        except AgentComment.DoesNotExist:
            logger.error(f"Comment {comment_id} not found for reaction count decrement")
            return False


class MetricsReconciliationService:
    """
    Service for verifying and fixing metrics consistency.
    """
    
    @staticmethod
    def reconcile_post_metrics(post_id: str) -> Dict[str, Any]:
        """
        Reconcile metrics for a specific post.
        
        Args:
            post_id: UUID of the post
        
        Returns:
            Dict with reconciliation results
        """
        try:
            post = AgentPost.objects.get(id=post_id)
        except AgentPost.DoesNotExist:
            return {'error': 'Post not found'}
        
        # Count actual reactions
        actual_reaction_count = AgentReaction.objects.filter(
            post_id=post_id
        ).count()
        
        # Count actual comments
        actual_comment_count = AgentComment.objects.filter(
            post_id=post_id,
            is_deleted=False
        ).count()
        
        # Check for discrepancies
        discrepancies = []
        
        if post.reaction_count != actual_reaction_count:
            discrepancies.append({
                'metric': 'reaction_count',
                'stored': post.reaction_count,
                'actual': actual_reaction_count,
                'difference': actual_reaction_count - post.reaction_count
            })
            # Fix discrepancy
            post.reaction_count = actual_reaction_count
        
        if post.comment_count != actual_comment_count:
            discrepancies.append({
                'metric': 'comment_count',
                'stored': post.comment_count,
                'actual': actual_comment_count,
                'difference': actual_comment_count - post.comment_count
            })
            # Fix discrepancy
            post.comment_count = actual_comment_count
        
        # Save if there were discrepancies
        if discrepancies:
            post.save(update_fields=['reaction_count', 'comment_count'])
            logger.info(f"Reconciled metrics for post {post_id}: {len(discrepancies)} discrepancies fixed")
        
        return {
            'post_id': str(post_id),
            'discrepancies': discrepancies,
            'fixed': len(discrepancies) > 0
        }
    
    @staticmethod
    def reconcile_profile_metrics(agent_id: str) -> Dict[str, Any]:
        """
        Reconcile metrics for an agent's social profile.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dict with reconciliation results
        """
        try:
            agent = AIAgent.objects.get(id=agent_id)
            profile = agent.social_profile
        except (AIAgent.DoesNotExist, AgentSocialProfile.DoesNotExist):
            return {'error': 'Agent or profile not found'}
        
        # Count actual followers
        actual_follower_count = agent.followers.count()
        
        # Count actual following
        actual_following_count = agent.following.count()
        
        # Count actual posts
        actual_post_count = AgentPost.objects.filter(
            agent_id=agent_id,
            is_deleted=False
        ).count()
        
        # Check for discrepancies
        discrepancies = []
        
        if profile.follower_count != actual_follower_count:
            discrepancies.append({
                'metric': 'follower_count',
                'stored': profile.follower_count,
                'actual': actual_follower_count,
                'difference': actual_follower_count - profile.follower_count
            })
            profile.follower_count = actual_follower_count
        
        if profile.following_count != actual_following_count:
            discrepancies.append({
                'metric': 'following_count',
                'stored': profile.following_count,
                'actual': actual_following_count,
                'difference': actual_following_count - profile.following_count
            })
            profile.following_count = actual_following_count
        
        if profile.post_count != actual_post_count:
            discrepancies.append({
                'metric': 'post_count',
                'stored': profile.post_count,
                'actual': actual_post_count,
                'difference': actual_post_count - profile.post_count
            })
            profile.post_count = actual_post_count
        
        # Save if there were discrepancies
        if discrepancies:
            profile.save(update_fields=['follower_count', 'following_count', 'post_count'])
            logger.info(f"Reconciled metrics for profile {agent_id}: {len(discrepancies)} discrepancies fixed")
        
        return {
            'agent_id': str(agent_id),
            'discrepancies': discrepancies,
            'fixed': len(discrepancies) > 0
        }
    
    @staticmethod
    def reconcile_all_posts(limit: int = 100) -> Dict[str, Any]:
        """
        Reconcile metrics for all posts (or a batch).
        
        Args:
            limit: Maximum number of posts to reconcile
        
        Returns:
            Dict with reconciliation summary
        """
        posts = AgentPost.objects.filter(is_deleted=False)[:limit]
        
        total_posts = 0
        total_discrepancies = 0
        posts_fixed = 0
        
        for post in posts:
            result = MetricsReconciliationService.reconcile_post_metrics(str(post.id))
            total_posts += 1
            
            if 'discrepancies' in result:
                total_discrepancies += len(result['discrepancies'])
                if result['fixed']:
                    posts_fixed += 1
        
        return {
            'total_posts_checked': total_posts,
            'posts_with_discrepancies': posts_fixed,
            'total_discrepancies_fixed': total_discrepancies
        }
    
    @staticmethod
    def reconcile_all_profiles(limit: int = 100) -> Dict[str, Any]:
        """
        Reconcile metrics for all profiles (or a batch).
        
        Args:
            limit: Maximum number of profiles to reconcile
        
        Returns:
            Dict with reconciliation summary
        """
        agents = AIAgent.objects.filter(is_active=True)[:limit]
        
        total_profiles = 0
        total_discrepancies = 0
        profiles_fixed = 0
        
        for agent in agents:
            result = MetricsReconciliationService.reconcile_profile_metrics(str(agent.id))
            total_profiles += 1
            
            if 'discrepancies' in result:
                total_discrepancies += len(result['discrepancies'])
                if result['fixed']:
                    profiles_fixed += 1
        
        return {
            'total_profiles_checked': total_profiles,
            'profiles_with_discrepancies': profiles_fixed,
            'total_discrepancies_fixed': total_discrepancies
        }
    
    @staticmethod
    def run_full_reconciliation() -> Dict[str, Any]:
        """
        Run full reconciliation for all posts and profiles.
        
        Returns:
            Dict with complete reconciliation summary
        """
        logger.info("Starting full metrics reconciliation")
        
        # Reconcile all posts
        post_results = MetricsReconciliationService.reconcile_all_posts(limit=1000)
        
        # Reconcile all profiles
        profile_results = MetricsReconciliationService.reconcile_all_profiles(limit=1000)
        
        logger.info("Full metrics reconciliation completed")
        
        return {
            'posts': post_results,
            'profiles': profile_results,
            'total_discrepancies_fixed': (
                post_results['total_discrepancies_fixed'] +
                profile_results['total_discrepancies_fixed']
            )
        }

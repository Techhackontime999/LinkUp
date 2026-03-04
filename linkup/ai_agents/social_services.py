"""
Social Platform Services for AI Agent interactions.

This module provides business logic services for:
- Social profile management
- Post creation and management
- Follow relationships
- Feed generation
- Agent discovery
- Reputation calculation
"""
import logging
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q, F, Count
from .models import AIAgent
from .social_models import (
    AgentSocialProfile,
    AgentPost,
    AgentFollow,
    AgentReaction,
    AgentComment,
    AgentReputation,
)

logger = logging.getLogger(__name__)


class SocialProfileService:
    """Service for managing agent social profiles."""
    
    @staticmethod
    def create_profile(agent: AIAgent, display_name: str, **kwargs) -> AgentSocialProfile:
        """
        Create a social profile for an agent.
        
        Args:
            agent: AIAgent instance
            display_name: Display name for the profile
            **kwargs: Additional profile fields (bio, avatar_url, etc.)
        
        Returns:
            Created AgentSocialProfile instance
        """
        profile = AgentSocialProfile.objects.create(
            agent=agent,
            display_name=display_name,
            **kwargs
        )
        logger.info(f"Created social profile for agent {agent.name}")
        return profile
    
    @staticmethod
    def get_profile(agent_id: str, viewer_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get agent social profile with visibility checks.
        
        Args:
            agent_id: UUID of the agent
            viewer_id: UUID of the viewing agent (for visibility checks)
        
        Returns:
            Profile data dict or None if not found/not visible
        """
        # Try cache first (only for public profiles without viewer restrictions)
        if viewer_id is None or viewer_id == agent_id:
            from .social_cache import SocialCache
            cached_profile = SocialCache.get_profile(agent_id)
            if cached_profile:
                return cached_profile
        
        try:
            profile = AgentSocialProfile.objects.select_related('agent').get(agent_id=agent_id)
            
            # Check visibility
            if not profile.is_public and viewer_id != agent_id:
                # Check if viewer follows this agent
                if viewer_id:
                    is_follower = AgentFollow.objects.filter(
                        follower_id=viewer_id,
                        followed_id=agent_id
                    ).exists()
                    if not is_follower:
                        return None
                else:
                    return None
            
            result = {
                'agent_id': str(profile.agent.id),
                'agent_name': profile.agent.name,
                'display_name': profile.display_name,
                'bio': profile.bio,
                'avatar_url': profile.avatar_url,
                'banner_url': profile.banner_url,
                'website': profile.website,
                'tags': profile.tags,
                'follower_count': profile.follower_count,
                'following_count': profile.following_count,
                'post_count': profile.post_count,
                'reputation_score': profile.reputation_score,
                'is_public': profile.is_public,
                'is_verified': profile.is_verified,
                'created_at': profile.created_at.isoformat(),
            }
            
            # Cache public profiles
            if profile.is_public and (viewer_id is None or viewer_id == agent_id):
                from .social_cache import SocialCache
                SocialCache.set_profile(agent_id, result)
            
            return result
        except AgentSocialProfile.DoesNotExist:
            return None
    
    @staticmethod
    def update_profile(agent_id: str, **updates) -> Optional[AgentSocialProfile]:
        """
        Update agent social profile.
        
        Args:
            agent_id: UUID of the agent
            **updates: Fields to update
        
        Returns:
            Updated profile or None if not found
        """
        try:
            profile = AgentSocialProfile.objects.get(agent_id=agent_id)
            
            for field, value in updates.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
            
            profile.full_clean()
            profile.save()
            
            # Invalidate cache
            from .social_cache import SocialCache
            SocialCache.invalidate_profile(agent_id)
            
            logger.info(f"Updated social profile for agent {agent_id}")
            return profile
        except AgentSocialProfile.DoesNotExist:
            return None


class PostService:
    """Service for managing agent posts."""
    
    @staticmethod
    @transaction.atomic
    def create_post(agent_id: str, post_type: str, content: str, 
                   visibility: str = 'PUBLIC', metadata: Optional[Dict] = None) -> AgentPost:
        """
        Create a new post.
        
        Args:
            agent_id: UUID of the agent creating the post
            post_type: Type of post (TEXT, CODE, DATA, etc.)
            content: Post content
            visibility: Visibility level
            metadata: Additional metadata
        
        Returns:
            Created AgentPost instance
        """
        agent = AIAgent.objects.get(id=agent_id)
        
        post = AgentPost.objects.create(
            agent=agent,
            post_type=post_type,
            content=content,
            visibility=visibility,
            metadata=metadata or {}
        )
        
        # Update agent's post count
        profile = AgentSocialProfile.objects.get(agent=agent)
        profile.post_count = F('post_count') + 1
        profile.save(update_fields=['post_count'])
        
        logger.info(f"Created post {post.id} by agent {agent.name}")
        return post
    
    @staticmethod
    def can_view_post(post: AgentPost, viewer_id: Optional[str]) -> bool:
        """
        Check if viewer can see the post based on visibility settings.
        
        Args:
            post: AgentPost instance
            viewer_id: UUID of viewing agent
        
        Returns:
            True if viewer can see the post
        """
        if post.visibility == 'PUBLIC':
            return True
        
        if not viewer_id:
            return False
        
        if str(post.agent_id) == viewer_id:
            return True
        
        if post.visibility == 'FOLLOWERS':
            return AgentFollow.objects.filter(
                follower_id=viewer_id,
                followed_id=post.agent_id
            ).exists()
        
        if post.visibility == 'PRIVATE':
            return False
        
        return False
    
    @staticmethod
    def get_posts(agent_id: str, viewer_id: Optional[str] = None, 
                 limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get posts by an agent with visibility checks.
        
        Args:
            agent_id: UUID of the agent
            viewer_id: UUID of viewing agent
            limit: Maximum number of posts to return
            offset: Offset for pagination
        
        Returns:
            List of post dicts
        """
        posts = AgentPost.objects.filter(
            agent_id=agent_id,
            is_deleted=False
        ).order_by('-created_at')[offset:offset + limit]
        
        result = []
        for post in posts:
            if PostService.can_view_post(post, viewer_id):
                result.append({
                    'id': str(post.id),
                    'agent_id': str(post.agent_id),
                    'agent_name': post.agent.name,
                    'post_type': post.post_type,
                    'content': post.content,
                    'metadata': post.metadata,
                    'visibility': post.visibility,
                    'view_count': post.view_count,
                    'reaction_count': post.reaction_count,
                    'comment_count': post.comment_count,
                    'share_count': post.share_count,
                    'created_at': post.created_at.isoformat(),
                    'updated_at': post.updated_at.isoformat(),
                })
        
        return result


class FollowService:
    """Service for managing follow relationships."""
    
    @staticmethod
    @transaction.atomic
    def follow_agent(follower_id: str, followed_id: str) -> Dict[str, Any]:
        """
        Create a follow relationship.
        
        Args:
            follower_id: UUID of the follower agent
            followed_id: UUID of the agent to follow
        
        Returns:
            Dict with success status and follow info
        """
        # Validate agents exist
        try:
            follower = AIAgent.objects.get(id=follower_id)
            followed = AIAgent.objects.get(id=followed_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent not found'
            }
        
        # Check for self-follow
        if follower_id == followed_id:
            return {
                'success': False,
                'error': 'Cannot follow yourself'
            }
        
        # Check if already following
        if AgentFollow.objects.filter(follower=follower, followed=followed).exists():
            return {
                'success': False,
                'error': 'Already following this agent'
            }
        
        # Create follow relationship
        follow = AgentFollow.objects.create(
            follower=follower,
            followed=followed
        )
        
        # Update counts
        follower_profile = AgentSocialProfile.objects.get(agent=follower)
        follower_profile.following_count = F('following_count') + 1
        follower_profile.save(update_fields=['following_count'])
        
        followed_profile = AgentSocialProfile.objects.get(agent=followed)
        followed_profile.follower_count = F('follower_count') + 1
        followed_profile.save(update_fields=['follower_count'])
        
        # Send notification
        from .social_services import NotificationService
        NotificationService.notify_new_follower(
            followed_id=str(followed_id),
            follower_id=str(follower_id)
        )
        
        logger.info(f"Agent {follower.name} followed {followed.name}")
        
        return {
            'success': True,
            'follow_id': follow.id,
            'follower_id': str(follower_id),
            'followed_id': str(followed_id),
            'created_at': follow.created_at.isoformat()
        }
    
    @staticmethod
    @transaction.atomic
    def unfollow_agent(follower_id: str, followed_id: str) -> Dict[str, Any]:
        """
        Remove a follow relationship.
        
        Args:
            follower_id: UUID of the follower agent
            followed_id: UUID of the agent to unfollow
        
        Returns:
            Dict with success status
        """
        try:
            follow = AgentFollow.objects.get(
                follower_id=follower_id,
                followed_id=followed_id
            )
            
            follow.delete()
            
            # Update counts
            follower_profile = AgentSocialProfile.objects.get(agent_id=follower_id)
            follower_profile.following_count = F('following_count') - 1
            follower_profile.save(update_fields=['following_count'])
            
            followed_profile = AgentSocialProfile.objects.get(agent_id=followed_id)
            followed_profile.follower_count = F('follower_count') - 1
            followed_profile.save(update_fields=['follower_count'])
            
            logger.info(f"Agent {follower_id} unfollowed {followed_id}")
            
            return {
                'success': True,
                'message': 'Successfully unfollowed agent'
            }
            
        except AgentFollow.DoesNotExist:
            return {
                'success': False,
                'error': 'Follow relationship does not exist'
            }
    
    @staticmethod
    def get_followers(agent_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get followers of an agent.
        
        Args:
            agent_id: UUID of the agent
            limit: Maximum number of followers to return
            offset: Offset for pagination
        
        Returns:
            List of follower agent dicts
        """
        follows = AgentFollow.objects.filter(
            followed_id=agent_id
        ).select_related('follower', 'follower__social_profile')[offset:offset + limit]
        
        return [{
            'agent_id': str(follow.follower.id),
            'agent_name': follow.follower.name,
            'display_name': follow.follower.social_profile.display_name,
            'avatar_url': follow.follower.social_profile.avatar_url,
            'reputation_score': follow.follower.social_profile.reputation_score,
            'followed_at': follow.created_at.isoformat()
        } for follow in follows]
    
    @staticmethod
    def get_following(agent_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get agents that an agent is following.
        
        Args:
            agent_id: UUID of the agent
            limit: Maximum number to return
            offset: Offset for pagination
        
        Returns:
            List of followed agent dicts
        """
        follows = AgentFollow.objects.filter(
            follower_id=agent_id
        ).select_related('followed', 'followed__social_profile')[offset:offset + limit]
        
        return [{
            'agent_id': str(follow.followed.id),
            'agent_name': follow.followed.name,
            'display_name': follow.followed.social_profile.display_name,
            'avatar_url': follow.followed.social_profile.avatar_url,
            'reputation_score': follow.followed.social_profile.reputation_score,
            'followed_at': follow.created_at.isoformat()
        } for follow in follows]



class ReactionService:
    """Service for managing reactions to posts and comments."""
    
    @staticmethod
    @transaction.atomic
    def add_reaction(agent_id: str, target_type: str, target_id: str, 
                    reaction_type: str) -> Dict[str, Any]:
        """
        Add a reaction to a post or comment.
        
        Args:
            agent_id: UUID of the agent adding the reaction
            target_type: 'post' or 'comment'
            target_id: UUID of the target
            reaction_type: Type of reaction (LIKE, LOVE, INSIGHTFUL, etc.)
        
        Returns:
            Dict with success status and reaction info
        """
        from django.contrib.contenttypes.models import ContentType
        
        try:
            agent = AIAgent.objects.get(id=agent_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent not found'
            }
        
        # Get target object
        if target_type == 'post':
            try:
                target = AgentPost.objects.get(id=target_id, is_deleted=False)
                content_type = ContentType.objects.get_for_model(AgentPost)
            except AgentPost.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Post not found'
                }
        elif target_type == 'comment':
            try:
                target = AgentComment.objects.get(id=target_id, is_deleted=False)
                content_type = ContentType.objects.get_for_model(AgentComment)
            except AgentComment.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Comment not found'
                }
        else:
            return {
                'success': False,
                'error': 'Invalid target type. Must be "post" or "comment"'
            }
        
        # Check if reaction already exists
        existing = AgentReaction.objects.filter(
            agent=agent,
            content_type=content_type,
            object_id=target_id
        ).first()
        
        if existing:
            # Update existing reaction
            existing.reaction_type = reaction_type
            existing.save(update_fields=['reaction_type'])
            
            return {
                'success': True,
                'reaction_id': existing.id,
                'action': 'updated',
                'reaction_type': reaction_type
            }
        
        # Create new reaction
        reaction = AgentReaction.objects.create(
            agent=agent,
            content_type=content_type,
            object_id=target_id,
            reaction_type=reaction_type
        )
        
        # Update target's reaction count
        target.reaction_count = F('reaction_count') + 1
        target.save(update_fields=['reaction_count'])
        
        # Send notification if reacting to someone else's content
        if target_type == 'post' and str(target.agent_id) != agent_id:
            from .social_services import NotificationService
            NotificationService.notify_post_reaction(
                post_agent_id=str(target.agent_id),
                reactor_id=agent_id,
                post_id=target_id,
                reaction_type=reaction_type
            )
        
        logger.info(f"Agent {agent.name} reacted to {target_type} {target_id}")
        
        return {
            'success': True,
            'reaction_id': reaction.id,
            'action': 'created',
            'reaction_type': reaction_type,
            'created_at': reaction.created_at.isoformat()
        }
    
    @staticmethod
    @transaction.atomic
    def remove_reaction(agent_id: str, target_type: str, target_id: str) -> Dict[str, Any]:
        """
        Remove a reaction from a post or comment.
        
        Args:
            agent_id: UUID of the agent removing the reaction
            target_type: 'post' or 'comment'
            target_id: UUID of the target
        
        Returns:
            Dict with success status
        """
        from django.contrib.contenttypes.models import ContentType
        
        # Get content type
        if target_type == 'post':
            content_type = ContentType.objects.get_for_model(AgentPost)
            try:
                target = AgentPost.objects.get(id=target_id, is_deleted=False)
            except AgentPost.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Post not found'
                }
        elif target_type == 'comment':
            content_type = ContentType.objects.get_for_model(AgentComment)
            try:
                target = AgentComment.objects.get(id=target_id, is_deleted=False)
            except AgentComment.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Comment not found'
                }
        else:
            return {
                'success': False,
                'error': 'Invalid target type. Must be "post" or "comment"'
            }
        
        # Find and delete reaction
        try:
            reaction = AgentReaction.objects.get(
                agent_id=agent_id,
                content_type=content_type,
                object_id=target_id
            )
            
            reaction.delete()
            
            # Update target's reaction count
            target.reaction_count = F('reaction_count') - 1
            target.save(update_fields=['reaction_count'])
            
            logger.info(f"Agent {agent_id} removed reaction from {target_type} {target_id}")
            
            return {
                'success': True,
                'message': 'Reaction removed successfully'
            }
            
        except AgentReaction.DoesNotExist:
            return {
                'success': False,
                'error': 'Reaction not found'
            }
    
    @staticmethod
    def get_reactions(target_type: str, target_id: str, 
                     limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get reactions for a post or comment.
        
        Args:
            target_type: 'post' or 'comment'
            target_id: UUID of the target
            limit: Maximum number of reactions to return
            offset: Offset for pagination
        
        Returns:
            List of reaction dicts
        """
        from django.contrib.contenttypes.models import ContentType
        
        # Get content type
        if target_type == 'post':
            content_type = ContentType.objects.get_for_model(AgentPost)
        elif target_type == 'comment':
            content_type = ContentType.objects.get_for_model(AgentComment)
        else:
            return []
        
        reactions = AgentReaction.objects.filter(
            content_type=content_type,
            object_id=target_id
        ).select_related('agent', 'agent__social_profile')[offset:offset + limit]
        
        return [{
            'id': reaction.id,
            'agent_id': str(reaction.agent.id),
            'agent_name': reaction.agent.name,
            'display_name': reaction.agent.social_profile.display_name,
            'reaction_type': reaction.reaction_type,
            'created_at': reaction.created_at.isoformat()
        } for reaction in reactions]



class CommentService:
    """Service for managing comments on posts."""
    
    @staticmethod
    @transaction.atomic
    def create_comment(agent_id: str, post_id: str, content: str, 
                      parent_comment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a comment on a post or reply to another comment.
        
        Args:
            agent_id: UUID of the agent creating the comment
            post_id: UUID of the post
            content: Comment content
            parent_comment_id: UUID of parent comment (for replies)
        
        Returns:
            Dict with success status and comment info
        """
        try:
            agent = AIAgent.objects.get(id=agent_id)
            post = AgentPost.objects.get(id=post_id, is_deleted=False)
        except (AIAgent.DoesNotExist, AgentPost.DoesNotExist) as e:
            return {
                'success': False,
                'error': str(e)
            }
        
        # Validate content length
        if len(content) > 2000:
            return {
                'success': False,
                'error': 'Comment exceeds maximum length of 2000 characters'
            }
        
        # Validate parent comment if provided
        parent_comment = None
        if parent_comment_id:
            try:
                parent_comment = AgentComment.objects.get(
                    id=parent_comment_id,
                    post=post,
                    is_deleted=False
                )
            except AgentComment.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Parent comment not found'
                }
        
        # Create comment
        comment = AgentComment.objects.create(
            agent=agent,
            post=post,
            parent_comment=parent_comment,
            content=content
        )
        
        # Update post's comment count
        post.comment_count = F('comment_count') + 1
        post.save(update_fields=['comment_count'])
        
        # Send notification
        from .social_services import NotificationService
        if parent_comment_id:
            # Reply to comment
            if str(parent_comment.agent_id) != agent_id:
                NotificationService.notify_comment_reply(
                    comment_agent_id=str(parent_comment.agent_id),
                    replier_id=agent_id,
                    comment_id=parent_comment_id,
                    reply_id=str(comment.id)
                )
        else:
            # Comment on post
            if str(post.agent_id) != agent_id:
                NotificationService.notify_post_comment(
                    post_agent_id=str(post.agent_id),
                    commenter_id=agent_id,
                    post_id=post_id,
                    comment_id=str(comment.id)
                )
        
        logger.info(f"Agent {agent.name} commented on post {post_id}")
        
        return {
            'success': True,
            'comment': {
                'id': str(comment.id),
                'agent_id': str(comment.agent_id),
                'agent_name': comment.agent.name,
                'post_id': str(comment.post_id),
                'parent_comment_id': str(parent_comment_id) if parent_comment_id else None,
                'content': comment.content,
                'reaction_count': comment.reaction_count,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            }
        }
    
    @staticmethod
    @transaction.atomic
    def update_comment(comment_id: str, agent_id: str, content: str) -> Dict[str, Any]:
        """
        Update a comment.
        
        Args:
            comment_id: UUID of the comment
            agent_id: UUID of the agent (must be comment owner)
            content: New content
        
        Returns:
            Dict with success status
        """
        try:
            comment = AgentComment.objects.get(id=comment_id, is_deleted=False)
        except AgentComment.DoesNotExist:
            return {
                'success': False,
                'error': 'Comment not found'
            }
        
        # Check ownership
        if str(comment.agent_id) != agent_id:
            return {
                'success': False,
                'error': 'Not authorized to update this comment'
            }
        
        # Validate content length
        if len(content) > 2000:
            return {
                'success': False,
                'error': 'Comment exceeds maximum length of 2000 characters'
            }
        
        comment.content = content
        comment.save(update_fields=['content', 'updated_at'])
        
        logger.info(f"Comment {comment_id} updated by agent {agent_id}")
        
        return {
            'success': True,
            'comment': {
                'id': str(comment.id),
                'content': comment.content,
                'updated_at': comment.updated_at.isoformat()
            }
        }
    
    @staticmethod
    @transaction.atomic
    def delete_comment(comment_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Delete a comment (soft delete).
        
        Args:
            comment_id: UUID of the comment
            agent_id: UUID of the agent (must be comment owner)
        
        Returns:
            Dict with success status
        """
        try:
            comment = AgentComment.objects.get(id=comment_id, is_deleted=False)
        except AgentComment.DoesNotExist:
            return {
                'success': False,
                'error': 'Comment not found'
            }
        
        # Check ownership
        if str(comment.agent_id) != agent_id:
            return {
                'success': False,
                'error': 'Not authorized to delete this comment'
            }
        
        # Soft delete
        comment.is_deleted = True
        comment.save(update_fields=['is_deleted'])
        
        # Update post's comment count
        post = comment.post
        post.comment_count = F('comment_count') - 1
        post.save(update_fields=['comment_count'])
        
        logger.info(f"Comment {comment_id} deleted by agent {agent_id}")
        
        return {
            'success': True,
            'message': 'Comment deleted successfully'
        }
    
    @staticmethod
    def get_comments(post_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get comments for a post.
        
        Args:
            post_id: UUID of the post
            limit: Maximum number of comments to return
            offset: Offset for pagination
        
        Returns:
            List of comment dicts
        """
        comments = AgentComment.objects.filter(
            post_id=post_id,
            is_deleted=False,
            parent_comment__isnull=True  # Only top-level comments
        ).select_related('agent', 'agent__social_profile').order_by('-created_at')[offset:offset + limit]
        
        result = []
        for comment in comments:
            # Get reply count
            reply_count = AgentComment.objects.filter(
                parent_comment=comment,
                is_deleted=False
            ).count()
            
            result.append({
                'id': str(comment.id),
                'agent_id': str(comment.agent_id),
                'agent_name': comment.agent.name,
                'display_name': comment.agent.social_profile.display_name,
                'avatar_url': comment.agent.social_profile.avatar_url,
                'content': comment.content,
                'reaction_count': comment.reaction_count,
                'reply_count': reply_count,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def get_replies(comment_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get replies to a comment.
        
        Args:
            comment_id: UUID of the parent comment
            limit: Maximum number of replies to return
            offset: Offset for pagination
        
        Returns:
            List of reply dicts
        """
        replies = AgentComment.objects.filter(
            parent_comment_id=comment_id,
            is_deleted=False
        ).select_related('agent', 'agent__social_profile').order_by('created_at')[offset:offset + limit]
        
        return [{
            'id': str(reply.id),
            'agent_id': str(reply.agent_id),
            'agent_name': reply.agent.name,
            'display_name': reply.agent.social_profile.display_name,
            'avatar_url': reply.agent.social_profile.avatar_url,
            'content': reply.content,
            'reaction_count': reply.reaction_count,
            'created_at': reply.created_at.isoformat(),
            'updated_at': reply.updated_at.isoformat()
        } for reply in replies]



class FeedService:
    """Service for generating personalized feeds."""
    
    @staticmethod
    def calculate_relevance_score(post: AgentPost, agent_interests: List[str], 
                                  agent_capabilities: Dict[str, Any]) -> float:
        """
        Calculate relevance score for a post based on agent's interests and engagement.
        
        Args:
            post: AgentPost instance
            agent_interests: List of agent's interest tags
            agent_capabilities: Dict of agent's capabilities
        
        Returns:
            Relevance score between 0.0 and 1.0
        """
        import math
        from datetime import datetime, timezone
        
        # Initialize component scores
        interest_score = 0.0
        engagement_score = 0.0
        recency_score = 0.0
        author_reputation_score = 0.0
        
        # Step 1: Calculate interest overlap
        post_tags = post.metadata.get('tags', []) if post.metadata else []
        if agent_interests:
            common_interests = set(agent_interests) & set(post_tags)
            interest_score = len(common_interests) / len(agent_interests)
        
        # Step 2: Calculate engagement score
        total_engagement = post.reaction_count + post.comment_count + post.share_count
        if total_engagement > 0:
            # Normalize using logarithmic scale
            engagement_score = math.log(1 + total_engagement) / math.log(1 + 1000)
            engagement_score = min(engagement_score, 1.0)
        
        # Step 3: Calculate recency score
        now = timezone.now()
        age_hours = (now - post.created_at).total_seconds() / 3600
        recency_score = math.exp(-age_hours / 24.0)  # Decay over 24 hours
        
        # Step 4: Get author reputation
        try:
            profile = AgentSocialProfile.objects.get(agent_id=post.agent_id)
            author_reputation_score = profile.reputation_score / 100.0
        except AgentSocialProfile.DoesNotExist:
            author_reputation_score = 0.0
        
        # Step 5: Weighted combination
        relevance_score = (
            0.35 * interest_score +
            0.25 * engagement_score +
            0.25 * recency_score +
            0.15 * author_reputation_score
        )
        
        # Step 6: Ensure bounds
        relevance_score = max(0.0, min(1.0, relevance_score))
        
        return relevance_score
    
    @staticmethod
    def generate_feed(agent_id: str, page_size: int = 20, 
                     cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate personalized feed for an agent.
        
        Args:
            agent_id: UUID of the agent
            page_size: Number of items per page (max 100)
            cursor: Pagination cursor
        
        Returns:
            Dict with feed items and next cursor
        """
        from datetime import timedelta
        from django.utils import timezone
        import base64
        import json
        
        # Validate page size
        page_size = min(page_size, 100)
        
        # Get agent's profile and interests
        try:
            profile = AgentSocialProfile.objects.get(agent_id=agent_id)
            agent_interests = profile.tags
        except AgentSocialProfile.DoesNotExist:
            return {
                'feed': [],
                'next_cursor': None
            }
        
        # Get followed agents
        followed_ids = AgentFollow.objects.filter(
            follower_id=agent_id
        ).values_list('followed_id', flat=True)
        
        if not followed_ids:
            return {
                'feed': [],
                'next_cursor': None
            }
        
        # Get posts from followed agents (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        # Decode cursor if provided
        offset = 0
        if cursor:
            try:
                cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
                offset = cursor_data.get('offset', 0)
            except Exception:
                offset = 0
        
        # Get posts
        posts = AgentPost.objects.filter(
            agent_id__in=followed_ids,
            created_at__gte=seven_days_ago,
            is_deleted=False
        ).select_related('agent', 'agent__social_profile').order_by('-created_at')
        
        # Calculate relevance scores
        scored_posts = []
        for post in posts:
            score = FeedService.calculate_relevance_score(
                post=post,
                agent_interests=agent_interests,
                agent_capabilities={}
            )
            scored_posts.append((score, post))
        
        # Sort by relevance score (descending) then timestamp (descending)
        scored_posts.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
        
        # Apply pagination
        paginated_posts = scored_posts[offset:offset + page_size]
        
        # Build feed items
        feed_items = []
        for score, post in paginated_posts:
            feed_items.append({
                'id': str(post.id),
                'agent_id': str(post.agent_id),
                'agent_name': post.agent.name,
                'display_name': post.agent.social_profile.display_name,
                'avatar_url': post.agent.social_profile.avatar_url,
                'post_type': post.post_type,
                'content': post.content,
                'metadata': post.metadata,
                'visibility': post.visibility,
                'view_count': post.view_count,
                'reaction_count': post.reaction_count,
                'comment_count': post.comment_count,
                'share_count': post.share_count,
                'relevance_score': round(score, 4),
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat()
            })
        
        # Generate next cursor
        next_cursor = None
        if len(scored_posts) > offset + page_size:
            cursor_data = {'offset': offset + page_size}
            next_cursor = base64.b64encode(
                json.dumps(cursor_data).encode('utf-8')
            ).decode('utf-8')
        
        return {
            'feed': feed_items,
            'count': len(feed_items),
            'next_cursor': next_cursor
        }



class DiscoveryService:
    """Service for agent discovery and recommendations."""
    
    @staticmethod
    def calculate_agent_similarity(requesting_agent: AgentSocialProfile, 
                                   candidate: AgentSocialProfile) -> float:
        """
        Calculate similarity score between two agents.
        
        Args:
            requesting_agent: Profile of requesting agent
            candidate: Profile of candidate agent
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Calculate interest overlap
        requesting_interests = set(requesting_agent.tags)
        candidate_interests = set(candidate.tags)
        
        if not requesting_interests:
            interest_similarity = 0.0
        else:
            common_interests = requesting_interests & candidate_interests
            interest_similarity = len(common_interests) / len(requesting_interests)
        
        # Factor in reputation (higher reputation = more attractive)
        reputation_factor = candidate.reputation_score / 100.0
        
        # Weighted combination
        similarity_score = (
            0.7 * interest_similarity +
            0.3 * reputation_factor
        )
        
        return min(1.0, max(0.0, similarity_score))
    
    @staticmethod
    def discover_agents(agent_id: str, filters: Optional[Dict[str, Any]] = None, 
                       limit: int = 50) -> List[Dict[str, Any]]:
        """
        Discover and recommend agents based on similarity.
        
        Args:
            agent_id: UUID of requesting agent
            filters: Optional filters (agent_type, capabilities, min_reputation)
            limit: Maximum number of recommendations (max 50)
        
        Returns:
            List of recommended agent profiles
        """
        filters = filters or {}
        limit = min(limit, 50)
        
        # Get requesting agent's profile
        try:
            requesting_profile = AgentSocialProfile.objects.select_related('agent').get(
                agent_id=agent_id
            )
        except AgentSocialProfile.DoesNotExist:
            return []
        
        # Get agents already followed
        already_following = set(
            AgentFollow.objects.filter(follower_id=agent_id).values_list('followed_id', flat=True)
        )
        
        # Build query
        query = AgentSocialProfile.objects.select_related('agent').exclude(
            agent_id=agent_id
        ).exclude(
            agent_id__in=already_following
        ).filter(
            agent__is_active=True,
            agent__is_suspended=False
        )
        
        # Apply filters
        if filters.get('agent_type'):
            query = query.filter(agent__agent_type=filters['agent_type'])
        
        if filters.get('min_reputation'):
            query = query.filter(reputation_score__gte=filters['min_reputation'])
        
        # Get candidates (3x limit for scoring)
        candidates = list(query[:limit * 3])
        
        # Calculate similarity scores
        scored_candidates = []
        for candidate in candidates:
            similarity_score = DiscoveryService.calculate_agent_similarity(
                requesting_profile,
                candidate
            )
            scored_candidates.append({
                'profile': candidate,
                'score': similarity_score
            })
        
        # Sort by similarity score
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top N results
        recommended = []
        for item in scored_candidates[:limit]:
            profile = item['profile']
            recommended.append({
                'agent_id': str(profile.agent_id),
                'agent_name': profile.agent.name,
                'display_name': profile.display_name,
                'bio': profile.bio,
                'avatar_url': profile.avatar_url,
                'tags': profile.tags,
                'follower_count': profile.follower_count,
                'post_count': profile.post_count,
                'reputation_score': profile.reputation_score,
                'is_verified': profile.is_verified,
                'similarity_score': round(item['score'], 4)
            })
        
        return recommended



class ReputationService:
    """Service for calculating and managing agent reputation."""
    
    @staticmethod
    def calculate_reputation(agent_id: str) -> Dict[str, float]:
        """
        Calculate reputation scores for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dict with overall, trust, expertise, and engagement scores
        """
        import math
        from datetime import datetime, timezone as dt_timezone
        
        try:
            agent = AIAgent.objects.get(id=agent_id)
            profile = AgentSocialProfile.objects.get(agent=agent)
        except (AIAgent.DoesNotExist, AgentSocialProfile.DoesNotExist):
            return {
                'overall': 0.0,
                'trust': 0.0,
                'expertise': 0.0,
                'engagement': 0.0
            }
        
        # Get or create reputation record
        reputation, created = AgentReputation.objects.get_or_create(
            agent=agent,
            defaults={
                'overall_score': 0.0,
                'trust_score': 0.0,
                'expertise_score': 0.0,
                'engagement_score': 0.0
            }
        )
        
        # Step 1: Calculate Trust Score
        account_age_days = (timezone.now() - agent.created_at).days
        age_factor = min(account_age_days / 365.0, 1.0)  # Max at 1 year
        
        verification_factor = 1.0 if profile.is_verified else 0.5
        
        # Assume 100% success rate for now (can be enhanced with actual tracking)
        interaction_success_rate = 1.0
        
        trust_score = (
            0.3 * age_factor +
            0.3 * verification_factor +
            0.4 * interaction_success_rate
        ) * 100.0
        
        # Step 2: Calculate Expertise Score
        quality_reactions = reputation.helpful_count + reputation.insightful_count + reputation.innovative_count
        total_posts = reputation.total_posts
        
        quality_ratio = 0.0
        if total_posts > 0:
            quality_ratio = min(quality_reactions / total_posts, 5.0) / 5.0
        
        reaction_received_factor = 0.0
        if reputation.total_reactions_received > 0:
            reaction_received_factor = math.log(1 + reputation.total_reactions_received) / math.log(1 + 10000)
            reaction_received_factor = min(reaction_received_factor, 1.0)
        
        expertise_score = (
            0.6 * quality_ratio +
            0.4 * reaction_received_factor
        ) * 100.0
        
        # Step 3: Calculate Engagement Score
        total_activity = reputation.total_posts + reputation.total_comments + reputation.total_reactions_given
        
        activity_factor = 0.0
        if total_activity > 0:
            activity_factor = math.log(1 + total_activity) / math.log(1 + 5000)
            activity_factor = min(activity_factor, 1.0)
        
        collaboration_factor = 0.0
        if reputation.collaboration_count > 0:
            collaboration_factor = math.log(1 + reputation.collaboration_count) / math.log(1 + 100)
            collaboration_factor = min(collaboration_factor, 1.0)
        
        engagement_score = (
            0.6 * activity_factor +
            0.4 * collaboration_factor
        ) * 100.0
        
        # Step 4: Calculate Overall Score
        overall_score = (
            0.35 * trust_score +
            0.40 * expertise_score +
            0.25 * engagement_score
        )
        
        # Step 5: Update reputation record
        reputation.trust_score = trust_score
        reputation.expertise_score = expertise_score
        reputation.engagement_score = engagement_score
        reputation.overall_score = overall_score
        reputation.last_calculated_at = timezone.now()
        reputation.save()
        
        # Step 6: Update social profile
        profile.reputation_score = overall_score
        profile.save(update_fields=['reputation_score'])
        
        # Step 7: Cache reputation data
        from .social_cache import SocialCache
        reputation_data = {
            'overall': round(overall_score, 2),
            'trust': round(trust_score, 2),
            'expertise': round(expertise_score, 2),
            'engagement': round(engagement_score, 2)
        }
        SocialCache.set_reputation(agent_id, reputation_data)
        
        logger.info(f"Calculated reputation for agent {agent.name}: {overall_score:.2f}")
        
        return reputation_data
    
    @staticmethod
    def update_reputation_metrics(agent_id: str, metric_type: str, increment: int = 1):
        """
        Update reputation metrics for an agent.
        
        Args:
            agent_id: UUID of the agent
            metric_type: Type of metric to update
            increment: Amount to increment (default: 1)
        """
        try:
            agent = AIAgent.objects.get(id=agent_id)
            reputation, created = AgentReputation.objects.get_or_create(
                agent=agent,
                defaults={
                    'overall_score': 0.0,
                    'trust_score': 0.0,
                    'expertise_score': 0.0,
                    'engagement_score': 0.0
                }
            )
            
            # Update the appropriate metric
            if metric_type == 'post':
                reputation.total_posts = F('total_posts') + increment
            elif metric_type == 'comment':
                reputation.total_comments = F('total_comments') + increment
            elif metric_type == 'reaction_given':
                reputation.total_reactions_given = F('total_reactions_given') + increment
            elif metric_type == 'reaction_received':
                reputation.total_reactions_received = F('total_reactions_received') + increment
            elif metric_type == 'helpful':
                reputation.helpful_count = F('helpful_count') + increment
            elif metric_type == 'insightful':
                reputation.insightful_count = F('insightful_count') + increment
            elif metric_type == 'innovative':
                reputation.innovative_count = F('innovative_count') + increment
            elif metric_type == 'collaboration':
                reputation.collaboration_count = F('collaboration_count') + increment
            
            reputation.save()
            
        except AIAgent.DoesNotExist:
            logger.error(f"Agent {agent_id} not found for reputation update")
    
    @staticmethod
    def get_reputation(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get reputation scores for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dict with reputation scores or None if not found
        """
        # Try cache first
        from .social_cache import SocialCache
        cached_reputation = SocialCache.get_reputation(agent_id)
        if cached_reputation:
            return cached_reputation
        
        try:
            reputation = AgentReputation.objects.select_related('agent').get(agent_id=agent_id)
            
            result = {
                'agent_id': str(reputation.agent_id),
                'overall_score': reputation.overall_score,
                'trust_score': reputation.trust_score,
                'expertise_score': reputation.expertise_score,
                'engagement_score': reputation.engagement_score,
                'total_posts': reputation.total_posts,
                'total_comments': reputation.total_comments,
                'total_reactions_received': reputation.total_reactions_received,
                'total_reactions_given': reputation.total_reactions_given,
                'helpful_count': reputation.helpful_count,
                'insightful_count': reputation.insightful_count,
                'innovative_count': reputation.innovative_count,
                'collaboration_count': reputation.collaboration_count,
                'last_calculated_at': reputation.last_calculated_at.isoformat()
            }
            
            # Cache the result
            SocialCache.set_reputation(agent_id, result)
            
            return result
        except AgentReputation.DoesNotExist:
            return None



class NotificationService:
    """Service for creating and managing notifications."""
    
    @staticmethod
    def create_notification(recipient_id: str, notification_type: str, 
                          title: str, message: str, 
                          sender_id: Optional[str] = None,
                          priority: str = 'MEDIUM',
                          metadata: Optional[Dict] = None,
                          target_object: Optional[Any] = None) -> Dict[str, Any]:
        """
        Create a notification for an agent.
        
        Args:
            recipient_id: UUID of recipient agent
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            sender_id: UUID of sender agent (optional)
            priority: Notification priority (LOW, MEDIUM, HIGH, URGENT)
            metadata: Additional metadata
            target_object: Target object (post, comment, etc.)
        
        Returns:
            Dict with notification info
        """
        from django.contrib.contenttypes.models import ContentType
        from .social_models import AgentNotification
        
        try:
            recipient = AIAgent.objects.get(id=recipient_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Recipient not found'
            }
        
        sender = None
        if sender_id:
            try:
                sender = AIAgent.objects.get(id=sender_id)
            except AIAgent.DoesNotExist:
                pass
        
        # Get content type and object ID for target
        content_type = None
        object_id = None
        if target_object:
            content_type = ContentType.objects.get_for_model(target_object)
            object_id = target_object.id
        
        # Create notification
        notification = AgentNotification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            metadata=metadata or {},
            content_type=content_type,
            object_id=object_id
        )
        
        logger.info(f"Created notification {notification.id} for agent {recipient.name}")
        
        # Attempt WebSocket delivery
        NotificationService._deliver_via_websocket(notification, sender)
        
        return {
            'success': True,
            'notification_id': str(notification.id),
            'recipient_id': str(recipient_id),
            'notification_type': notification_type,
            'created_at': notification.created_at.isoformat()
        }
    
    @staticmethod
    def get_notifications(agent_id: str, unread_only: bool = False,
                         limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get notifications for an agent.
        
        Args:
            agent_id: UUID of the agent
            unread_only: Only return unread notifications
            limit: Maximum number to return
            offset: Offset for pagination
        
        Returns:
            List of notification dicts
        """
        from .social_models import AgentNotification
        
        query = AgentNotification.objects.filter(
            recipient_id=agent_id
        ).select_related('sender').order_by('-created_at')
        
        if unread_only:
            query = query.filter(is_read=False)
        
        notifications = query[offset:offset + limit]
        
        result = []
        for notif in notifications:
            result.append({
                'id': str(notif.id),
                'notification_type': notif.notification_type,
                'priority': notif.priority,
                'title': notif.title,
                'message': notif.message,
                'metadata': notif.metadata,
                'sender_id': str(notif.sender_id) if notif.sender_id else None,
                'sender_name': notif.sender.name if notif.sender else None,
                'is_read': notif.is_read,
                'read_at': notif.read_at.isoformat() if notif.read_at else None,
                'created_at': notif.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def mark_as_read(notification_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read.
        
        Args:
            notification_id: UUID of the notification
            agent_id: UUID of the agent (must be recipient)
        
        Returns:
            Dict with success status
        """
        from .social_models import AgentNotification
        
        try:
            notification = AgentNotification.objects.get(
                id=notification_id,
                recipient_id=agent_id
            )
            
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save(update_fields=['is_read', 'read_at'])
            
            return {
                'success': True,
                'message': 'Notification marked as read'
            }
            
        except AgentNotification.DoesNotExist:
            return {
                'success': False,
                'error': 'Notification not found'
            }
    
    @staticmethod
    def get_unread_count(agent_id: str) -> int:
        """
        Get count of unread notifications for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Count of unread notifications
        """
        from .social_models import AgentNotification
        
        return AgentNotification.objects.filter(
            recipient_id=agent_id,
            is_read=False
        ).count()
    
    @staticmethod
    def notify_new_follower(followed_id: str, follower_id: str):
        """Queue notification for new follower."""
        NotificationService.create_notification(
            recipient_id=followed_id,
            sender_id=follower_id,
            notification_type='NEW_FOLLOWER',
            title='New Follower',
            message='started following you',
            priority='LOW'
        )
    
    @staticmethod
    def notify_post_reaction(post_agent_id: str, reactor_id: str, 
                           post_id: str, reaction_type: str):
        """Queue notification for post reaction."""
        NotificationService.create_notification(
            recipient_id=post_agent_id,
            sender_id=reactor_id,
            notification_type='POST_REACTION',
            title='Post Reaction',
            message=f'reacted {reaction_type} to your post',
            priority='LOW',
            metadata={'post_id': str(post_id), 'reaction_type': reaction_type}
        )
    
    @staticmethod
    def notify_post_comment(post_agent_id: str, commenter_id: str, 
                          post_id: str, comment_id: str):
        """Queue notification for post comment."""
        NotificationService.create_notification(
            recipient_id=post_agent_id,
            sender_id=commenter_id,
            notification_type='POST_COMMENT',
            title='New Comment',
            message='commented on your post',
            priority='MEDIUM',
            metadata={'post_id': str(post_id), 'comment_id': str(comment_id)}
        )
    
    @staticmethod
    def notify_comment_reply(comment_agent_id: str, replier_id: str,
                           comment_id: str, reply_id: str):
        """Queue notification for comment reply."""
        NotificationService.create_notification(
            recipient_id=comment_agent_id,
            sender_id=replier_id,
            notification_type='COMMENT_REPLY',
            title='Comment Reply',
            message='replied to your comment',
            priority='MEDIUM',
            metadata={'comment_id': str(comment_id), 'reply_id': str(reply_id)}
        )



class CollaborationSpaceService:
    """Service for managing collaboration spaces."""
    
    @staticmethod
    @transaction.atomic
    def create_space(
        creator_id: str,
        name: str,
        description: str,
        space_type: str = 'PUBLIC',
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a collaboration space.
        
        Args:
            creator_id: UUID of the creator agent
            name: Space name
            description: Space description
            space_type: Space visibility type (PUBLIC, PRIVATE, INVITE_ONLY)
            tags: Optional list of tags
        
        Returns:
            Created space data dict
        """
        from .social_models import AgentCollaborationSpace, SpaceMembership
        
        creator = AIAgent.objects.get(id=creator_id)
        
        space = AgentCollaborationSpace.objects.create(
            name=name,
            description=description,
            creator=creator,
            space_type=space_type,
            tags=tags or [],
            member_count=1
        )
        
        # Add creator as owner
        SpaceMembership.objects.create(
            space=space,
            agent=creator,
            role='OWNER'
        )
        
        logger.info(f"Created collaboration space '{name}' by agent {creator.name}")
        
        return {
            'id': str(space.id),
            'name': space.name,
            'description': space.description,
            'creator_id': str(creator.id),
            'space_type': space.space_type,
            'tags': space.tags,
            'member_count': space.member_count,
            'post_count': space.post_count,
            'created_at': space.created_at.isoformat(),
        }
    
    @staticmethod
    @transaction.atomic
    def invite_to_space(
        space_id: str,
        inviter_id: str,
        invitee_id: str
    ) -> Dict[str, Any]:
        """
        Invite an agent to a collaboration space.
        
        Args:
            space_id: UUID of the space
            inviter_id: UUID of the inviting agent
            invitee_id: UUID of the agent being invited
        
        Returns:
            Invitation result dict
        
        Raises:
            PermissionError: If inviter doesn't have permission
        """
        from .social_models import AgentCollaborationSpace, SpaceMembership
        
        space = AgentCollaborationSpace.objects.get(id=space_id)
        
        # Check inviter has permission (OWNER or ADMIN)
        inviter_membership = SpaceMembership.objects.filter(
            space=space,
            agent_id=inviter_id,
            role__in=['OWNER', 'ADMIN']
        ).first()
        
        if not inviter_membership:
            raise PermissionDenied("Only space owners and admins can invite members")
        
        # Check if invitee is already a member
        existing = SpaceMembership.objects.filter(
            space=space,
            agent_id=invitee_id
        ).exists()
        
        if existing:
            return {
                'success': False,
                'message': 'Agent is already a member'
            }
        
        # Create notification for invitee
        NotificationService.create_notification(
            recipient_id=invitee_id,
            sender_id=inviter_id,
            notification_type='SPACE_INVITE',
            title=f"Invitation to {space.name}",
            message=f"You've been invited to join the collaboration space '{space.name}'",
            metadata={
                'space_id': str(space.id),
                'space_name': space.name,
                'inviter_id': str(inviter_id)
            }
        )
        
        logger.info(f"Agent {inviter_id} invited agent {invitee_id} to space {space.name}")
        
        return {
            'success': True,
            'message': 'Invitation sent',
            'space_id': str(space.id)
        }
    
    @staticmethod
    @transaction.atomic
    def join_space(space_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Join a collaboration space.
        
        Args:
            space_id: UUID of the space
            agent_id: UUID of the agent joining
        
        Returns:
            Join result dict
        
        Raises:
            PermissionError: If space is INVITE_ONLY or PRIVATE
        """
        from .social_models import AgentCollaborationSpace, SpaceMembership
        
        space = AgentCollaborationSpace.objects.get(id=space_id)
        agent = AIAgent.objects.get(id=agent_id)
        
        # Check if already a member
        existing = SpaceMembership.objects.filter(
            space=space,
            agent=agent
        ).exists()
        
        if existing:
            return {
                'success': False,
                'message': 'Already a member'
            }
        
        # Check space type permissions
        if space.space_type in ['PRIVATE', 'INVITE_ONLY']:
            # Check if there's a pending invitation
            from .social_models import AgentNotification
            invitation = AgentNotification.objects.filter(
                recipient=agent,
                notification_type='SPACE_INVITE',
                metadata__space_id=str(space.id),
                is_read=False
            ).first()
            
            if not invitation:
                raise PermissionDenied("This space requires an invitation")
            
            # Mark invitation as read
            invitation.mark_as_read()
        
        # Create membership
        SpaceMembership.objects.create(
            space=space,
            agent=agent,
            role='MEMBER'
        )
        
        # Update member count
        space.member_count = F('member_count') + 1
        space.save(update_fields=['member_count'])
        
        logger.info(f"Agent {agent.name} joined space {space.name}")
        
        return {
            'success': True,
            'message': 'Successfully joined space',
            'space_id': str(space.id),
            'membership_role': 'MEMBER'
        }
    
    @staticmethod
    def get_space_members(space_id: str, viewer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get members of a collaboration space.
        
        Args:
            space_id: UUID of the space
            viewer_id: UUID of the viewing agent (for permission checks)
        
        Returns:
            List of member data dicts
        """
        from .social_models import AgentCollaborationSpace, SpaceMembership
        
        space = AgentCollaborationSpace.objects.get(id=space_id)
        
        # Check visibility
        if space.space_type == 'PRIVATE' and viewer_id:
            is_member = SpaceMembership.objects.filter(
                space=space,
                agent_id=viewer_id
            ).exists()
            if not is_member:
                raise PermissionDenied("Only members can view private space members")
        
        memberships = SpaceMembership.objects.filter(
            space=space
        ).select_related('agent', 'agent__social_profile').order_by('-joined_at')
        
        return [
            {
                'agent_id': str(m.agent.id),
                'agent_name': m.agent.name,
                'display_name': m.agent.social_profile.display_name if hasattr(m.agent, 'social_profile') else m.agent.name,
                'role': m.role,
                'joined_at': m.joined_at.isoformat(),
                'contribution_count': m.contribution_count
            }
            for m in memberships
        ]
    
    @staticmethod
    @transaction.atomic
    def create_space_post(
        space_id: str,
        agent_id: str,
        post_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a post in a collaboration space.
        
        Args:
            space_id: UUID of the space
            agent_id: UUID of the posting agent
            post_type: Type of post
            content: Post content
            metadata: Optional post metadata
        
        Returns:
            Created post data dict
        
        Raises:
            PermissionError: If agent is not a member
        """
        from .social_models import AgentCollaborationSpace, SpaceMembership
        
        space = AgentCollaborationSpace.objects.get(id=space_id)
        agent = AIAgent.objects.get(id=agent_id)
        
        # Check membership
        membership = SpaceMembership.objects.filter(
            space=space,
            agent=agent
        ).first()
        
        if not membership:
            raise PermissionDenied("Only members can post in this space")
        
        # Create post with space reference in metadata
        post_metadata = metadata or {}
        post_metadata['space_id'] = str(space.id)
        post_metadata['space_name'] = space.name
        
        post = AgentPost.objects.create(
            agent=agent,
            post_type=post_type,
            content=content,
            metadata=post_metadata,
            visibility='CONNECTIONS'  # Space posts visible to connections
        )
        
        # Update counts
        space.post_count = F('post_count') + 1
        space.save(update_fields=['post_count'])
        
        membership.contribution_count = F('contribution_count') + 1
        membership.save(update_fields=['contribution_count'])
        
        # Update agent's post count
        profile = AgentSocialProfile.objects.get(agent=agent)
        profile.post_count = F('post_count') + 1
        profile.save(update_fields=['post_count'])
        
        logger.info(f"Agent {agent.name} created post in space {space.name}")
        
        return {
            'id': str(post.id),
            'agent_id': str(agent.id),
            'post_type': post.post_type,
            'content': post.content,
            'metadata': post.metadata,
            'visibility': post.visibility,
            'created_at': post.created_at.isoformat()
        }



class MarketplaceService:
    """Service for managing capability marketplace."""
    
    @staticmethod
    def create_listing(
        agent_id: str,
        title: str,
        description: str,
        listing_type: str,
        capabilities: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None,
        pricing_model: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a capability listing.
        
        Args:
            agent_id: UUID of the agent
            title: Listing title
            description: Listing description
            listing_type: Type of listing (SERVICE, API, SKILL, RESOURCE)
            capabilities: Capability specifications
            requirements: Requirements for using capability
            pricing_model: Pricing information
            tags: Tags for discovery
            category: Category
        
        Returns:
            Created listing data dict
        """
        from .social_models import AgentCapabilityListing
        
        agent = AIAgent.objects.get(id=agent_id)
        
        listing = AgentCapabilityListing.objects.create(
            agent=agent,
            title=title,
            description=description,
            listing_type=listing_type,
            capabilities=capabilities,
            requirements=requirements or {},
            pricing_model=pricing_model or {},
            tags=tags or [],
            category=category or 'General',
            status='ACTIVE'
        )
        
        logger.info(f"Created capability listing '{title}' by agent {agent.name}")
        
        return {
            'id': str(listing.id),
            'agent_id': str(agent.id),
            'title': listing.title,
            'description': listing.description,
            'listing_type': listing.listing_type,
            'capabilities': listing.capabilities,
            'requirements': listing.requirements,
            'pricing_model': listing.pricing_model,
            'tags': listing.tags,
            'category': listing.category,
            'status': listing.status,
            'view_count': listing.view_count,
            'request_count': listing.request_count,
            'rating_average': listing.rating_average,
            'rating_count': listing.rating_count,
            'created_at': listing.created_at.isoformat()
        }
    
    @staticmethod
    def update_listing(
        listing_id: str,
        agent_id: str,
        **updates
    ) -> Dict[str, Any]:
        """
        Update a capability listing.
        
        Args:
            listing_id: UUID of the listing
            agent_id: UUID of the agent (for permission check)
            **updates: Fields to update
        
        Returns:
            Updated listing data dict
        
        Raises:
            PermissionError: If agent doesn't own the listing
        """
        from .social_models import AgentCapabilityListing
        
        listing = AgentCapabilityListing.objects.get(id=listing_id)
        
        # Check ownership
        if str(listing.agent.id) != agent_id:
            raise PermissionDenied("Only the listing owner can update it")
        
        # Update allowed fields
        allowed_fields = [
            'title', 'description', 'capabilities', 'requirements',
            'pricing_model', 'tags', 'category', 'status'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(listing, field, value)
        
        listing.save()
        
        logger.info(f"Updated capability listing {listing.title}")
        
        return {
            'id': str(listing.id),
            'agent_id': str(listing.agent.id),
            'title': listing.title,
            'description': listing.description,
            'listing_type': listing.listing_type,
            'capabilities': listing.capabilities,
            'requirements': listing.requirements,
            'pricing_model': listing.pricing_model,
            'tags': listing.tags,
            'category': listing.category,
            'status': listing.status,
            'updated_at': listing.updated_at.isoformat()
        }
    
    @staticmethod
    def search_marketplace(
        query: Optional[str] = None,
        listing_type: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search capability marketplace.
        
        Args:
            query: Search query for title/description
            listing_type: Filter by listing type
            category: Filter by category
            tags: Filter by tags
            min_rating: Minimum rating filter
            limit: Maximum results (default 50)
        
        Returns:
            List of listing data dicts
        """
        from .social_models import AgentCapabilityListing
        
        queryset = AgentCapabilityListing.objects.filter(status='ACTIVE')
        
        # Apply filters
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        
        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if tags:
            # Filter by tags (listings that have any of the specified tags)
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        if min_rating is not None:
            queryset = queryset.filter(rating_average__gte=min_rating)
        
        # Order by rating and recency
        queryset = queryset.order_by('-rating_average', '-created_at')[:limit]
        
        return [
            {
                'id': str(listing.id),
                'agent_id': str(listing.agent.id),
                'agent_name': listing.agent.name,
                'title': listing.title,
                'description': listing.description,
                'listing_type': listing.listing_type,
                'capabilities': listing.capabilities,
                'requirements': listing.requirements,
                'pricing_model': listing.pricing_model,
                'tags': listing.tags,
                'category': listing.category,
                'view_count': listing.view_count,
                'request_count': listing.request_count,
                'rating_average': listing.rating_average,
                'rating_count': listing.rating_count,
                'created_at': listing.created_at.isoformat()
            }
            for listing in queryset
        ]
    
    @staticmethod
    @transaction.atomic
    def get_listing(listing_id: str, increment_view: bool = True) -> Dict[str, Any]:
        """
        Get a capability listing by ID.
        
        Args:
            listing_id: UUID of the listing
            increment_view: Whether to increment view count
        
        Returns:
            Listing data dict
        """
        from .social_models import AgentCapabilityListing
        
        listing = AgentCapabilityListing.objects.select_related('agent').get(id=listing_id)
        
        # Increment view count
        if increment_view:
            listing.view_count = F('view_count') + 1
            listing.save(update_fields=['view_count'])
            listing.refresh_from_db()
        
        return {
            'id': str(listing.id),
            'agent_id': str(listing.agent.id),
            'agent_name': listing.agent.name,
            'title': listing.title,
            'description': listing.description,
            'listing_type': listing.listing_type,
            'capabilities': listing.capabilities,
            'requirements': listing.requirements,
            'pricing_model': listing.pricing_model,
            'tags': listing.tags,
            'category': listing.category,
            'status': listing.status,
            'view_count': listing.view_count,
            'request_count': listing.request_count,
            'rating_average': listing.rating_average,
            'rating_count': listing.rating_count,
            'created_at': listing.created_at.isoformat(),
            'updated_at': listing.updated_at.isoformat()
        }
    
    @staticmethod
    @transaction.atomic
    def rate_listing(
        listing_id: str,
        agent_id: str,
        rating: float
    ) -> Dict[str, Any]:
        """
        Rate a capability listing.
        
        Args:
            listing_id: UUID of the listing
            agent_id: UUID of the rating agent
            rating: Rating value (1.0 to 5.0)
        
        Returns:
            Updated listing data dict
        
        Raises:
            ValueError: If rating is out of range
        """
        from .social_models import AgentCapabilityListing
        
        if not (1.0 <= rating <= 5.0):
            raise ValueError("Rating must be between 1.0 and 5.0")
        
        listing = AgentCapabilityListing.objects.get(id=listing_id)
        
        # Calculate new average rating
        total_rating = listing.rating_average * listing.rating_count
        new_total = total_rating + rating
        new_count = listing.rating_count + 1
        new_average = new_total / new_count
        
        listing.rating_average = new_average
        listing.rating_count = new_count
        listing.save(update_fields=['rating_average', 'rating_count'])
        
        logger.info(f"Agent {agent_id} rated listing {listing.title}: {rating}")
        
        return {
            'id': str(listing.id),
            'rating_average': listing.rating_average,
            'rating_count': listing.rating_count
        }

    
    @staticmethod
    def _deliver_via_websocket(notification, sender):
        """
        Deliver notification via WebSocket if agent is online.
        
        Falls back to database storage if WebSocket delivery fails.
        
        Args:
            notification: AgentNotification instance
            sender: AIAgent instance (sender) or None
        
        Requirements: 12.4, 12.9, 16.3, 16.6
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            
            if not channel_layer:
                logger.warning("Channel layer not configured, skipping WebSocket delivery")
                return
            
            # Check if agent is online
            cache_key = f'social_agent_online:{notification.recipient_id}'
            is_online = cache.get(cache_key)
            
            if not is_online:
                logger.debug(f"Agent {notification.recipient_id} is offline, notification stored in database")
                return
            
            # Prepare notification data
            notification_data = {
                'type': 'social_notification',
                'notification_id': str(notification.id),
                'notification_type': notification.notification_type,
                'priority': notification.priority,
                'title': notification.title,
                'message': notification.message,
                'metadata': notification.metadata,
                'sender_id': str(sender.id) if sender else None,
                'sender_name': sender.name if sender else None,
                'timestamp': notification.created_at.isoformat()
            }
            
            # Send to agent's channel group
            channel_group_name = f'social_agent_{notification.recipient_id}'
            
            async_to_sync(channel_layer.group_send)(
                channel_group_name,
                notification_data
            )
            
            logger.debug(f"Notification {notification.id} sent via WebSocket to agent {notification.recipient_id}")
            
        except Exception as e:
            logger.error(f"Error delivering notification via WebSocket: {e}", exc_info=True)
            # Notification remains in database for later retrieval

"""
Content Moderation Service for AI Agent Social Platform.

Provides moderation capabilities including:
- Content flagging
- Moderation queue management
- Content removal
- Agent suspension
- Audit logging
"""
import logging
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from .models import AIAgent
from .social_models import AgentPost, AgentComment

logger = logging.getLogger(__name__)


class ModerationService:
    """Service for content moderation and agent management."""
    
    @staticmethod
    @transaction.atomic
    def flag_content(
        content_type: str,
        content_id: str,
        flagger_id: str,
        reason: str,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Flag content for moderation review.
        
        Args:
            content_type: Type of content ('post' or 'comment')
            content_id: UUID of the content
            flagger_id: UUID of the agent flagging the content
            reason: Reason for flagging
            details: Additional details
        
        Returns:
            Dict with success status and flag info
        """
        try:
            flagger = AIAgent.objects.get(id=flagger_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Flagger agent not found'
            }
        
        # Get content and flag it
        if content_type == 'post':
            try:
                content = AgentPost.objects.get(id=content_id, is_deleted=False)
                content.is_flagged = True
                content.save(update_fields=['is_flagged'])
                
                logger.info(f"Post {content_id} flagged by agent {flagger_id}: {reason}")
                
                return {
                    'success': True,
                    'content_type': 'post',
                    'content_id': str(content_id),
                    'flagged_at': timezone.now().isoformat(),
                    'reason': reason
                }
            except AgentPost.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Post not found'
                }
        
        elif content_type == 'comment':
            try:
                content = AgentComment.objects.get(id=content_id, is_deleted=False)
                # Comments don't have is_flagged field, so we'll use metadata
                if not content.post.metadata:
                    content.post.metadata = {}
                
                if 'flagged_comments' not in content.post.metadata:
                    content.post.metadata['flagged_comments'] = []
                
                content.post.metadata['flagged_comments'].append({
                    'comment_id': str(content_id),
                    'flagger_id': str(flagger_id),
                    'reason': reason,
                    'flagged_at': timezone.now().isoformat()
                })
                content.post.save(update_fields=['metadata'])
                
                logger.info(f"Comment {content_id} flagged by agent {flagger_id}: {reason}")
                
                return {
                    'success': True,
                    'content_type': 'comment',
                    'content_id': str(content_id),
                    'flagged_at': timezone.now().isoformat(),
                    'reason': reason
                }
            except AgentComment.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Comment not found'
                }
        
        else:
            return {
                'success': False,
                'error': 'Invalid content type. Must be "post" or "comment"'
            }
    
    @staticmethod
    def get_moderation_queue(
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get flagged content for moderation review.
        
        Args:
            content_type: Filter by content type ('post' or 'comment')
            limit: Maximum number of items to return
            offset: Offset for pagination
        
        Returns:
            List of flagged content items
        """
        queue = []
        
        # Get flagged posts
        if content_type is None or content_type == 'post':
            flagged_posts = AgentPost.objects.filter(
                is_flagged=True,
                is_deleted=False
            ).select_related('agent').order_by('-updated_at')[offset:offset + limit]
            
            for post in flagged_posts:
                queue.append({
                    'content_type': 'post',
                    'content_id': str(post.id),
                    'agent_id': str(post.agent_id),
                    'agent_name': post.agent.name,
                    'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
                    'post_type': post.post_type,
                    'visibility': post.visibility,
                    'created_at': post.created_at.isoformat(),
                    'flagged_at': post.updated_at.isoformat()
                })
        
        # Get flagged comments (stored in post metadata)
        if content_type is None or content_type == 'comment':
            posts_with_flagged_comments = AgentPost.objects.filter(
                metadata__flagged_comments__isnull=False
            ).select_related('agent')
            
            for post in posts_with_flagged_comments:
                if 'flagged_comments' in post.metadata:
                    for flag_info in post.metadata['flagged_comments']:
                        try:
                            comment = AgentComment.objects.get(
                                id=flag_info['comment_id'],
                                is_deleted=False
                            )
                            queue.append({
                                'content_type': 'comment',
                                'content_id': flag_info['comment_id'],
                                'agent_id': str(comment.agent_id),
                                'agent_name': comment.agent.name,
                                'content': comment.content[:200] + '...' if len(comment.content) > 200 else comment.content,
                                'post_id': str(post.id),
                                'created_at': comment.created_at.isoformat(),
                                'flagged_at': flag_info['flagged_at'],
                                'flag_reason': flag_info['reason']
                            })
                        except AgentComment.DoesNotExist:
                            continue
        
        return queue[:limit]
    
    @staticmethod
    @transaction.atomic
    def remove_content(
        content_type: str,
        content_id: str,
        moderator_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Remove content (soft delete).
        
        Args:
            content_type: Type of content ('post' or 'comment')
            content_id: UUID of the content
            moderator_id: UUID of the moderator
            reason: Reason for removal
        
        Returns:
            Dict with success status
        """
        try:
            moderator = AIAgent.objects.get(id=moderator_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Moderator not found'
            }
        
        # Remove content
        if content_type == 'post':
            try:
                post = AgentPost.objects.get(id=content_id)
                post.is_deleted = True
                post.is_flagged = False
                post.save(update_fields=['is_deleted', 'is_flagged'])
                
                # Log moderation action
                ModerationService._log_moderation_action(
                    moderator_id=moderator_id,
                    action='REMOVE_POST',
                    target_type='post',
                    target_id=content_id,
                    reason=reason
                )
                
                logger.info(f"Post {content_id} removed by moderator {moderator_id}: {reason}")
                
                return {
                    'success': True,
                    'message': 'Post removed successfully'
                }
            except AgentPost.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Post not found'
                }
        
        elif content_type == 'comment':
            try:
                comment = AgentComment.objects.get(id=content_id)
                comment.is_deleted = True
                comment.save(update_fields=['is_deleted'])
                
                # Update post's comment count
                post = comment.post
                post.comment_count = max(0, post.comment_count - 1)
                post.save(update_fields=['comment_count'])
                
                # Log moderation action
                ModerationService._log_moderation_action(
                    moderator_id=moderator_id,
                    action='REMOVE_COMMENT',
                    target_type='comment',
                    target_id=content_id,
                    reason=reason
                )
                
                logger.info(f"Comment {content_id} removed by moderator {moderator_id}: {reason}")
                
                return {
                    'success': True,
                    'message': 'Comment removed successfully'
                }
            except AgentComment.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Comment not found'
                }
        
        else:
            return {
                'success': False,
                'error': 'Invalid content type'
            }
    
    @staticmethod
    @transaction.atomic
    def suspend_agent(
        agent_id: str,
        moderator_id: str,
        reason: str,
        duration_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Suspend an agent.
        
        Args:
            agent_id: UUID of the agent to suspend
            moderator_id: UUID of the moderator
            reason: Reason for suspension
            duration_days: Duration in days (None for permanent)
        
        Returns:
            Dict with success status
        """
        try:
            agent = AIAgent.objects.get(id=agent_id)
            moderator = AIAgent.objects.get(id=moderator_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent or moderator not found'
            }
        
        # Suspend agent
        agent.is_suspended = True
        agent.save(update_fields=['is_suspended'])
        
        # Log moderation action
        ModerationService._log_moderation_action(
            moderator_id=moderator_id,
            action='SUSPEND_AGENT',
            target_type='agent',
            target_id=agent_id,
            reason=reason,
            metadata={
                'duration_days': duration_days,
                'suspended_at': timezone.now().isoformat()
            }
        )
        
        logger.info(f"Agent {agent_id} suspended by moderator {moderator_id}: {reason}")
        
        return {
            'success': True,
            'message': 'Agent suspended successfully',
            'agent_id': str(agent_id),
            'suspended_at': timezone.now().isoformat(),
            'duration_days': duration_days
        }
    
    @staticmethod
    @transaction.atomic
    def unsuspend_agent(
        agent_id: str,
        moderator_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Unsuspend an agent.
        
        Args:
            agent_id: UUID of the agent to unsuspend
            moderator_id: UUID of the moderator
            reason: Reason for unsuspension
        
        Returns:
            Dict with success status
        """
        try:
            agent = AIAgent.objects.get(id=agent_id)
            moderator = AIAgent.objects.get(id=moderator_id)
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent or moderator not found'
            }
        
        # Unsuspend agent
        agent.is_suspended = False
        agent.save(update_fields=['is_suspended'])
        
        # Log moderation action
        ModerationService._log_moderation_action(
            moderator_id=moderator_id,
            action='UNSUSPEND_AGENT',
            target_type='agent',
            target_id=agent_id,
            reason=reason
        )
        
        logger.info(f"Agent {agent_id} unsuspended by moderator {moderator_id}: {reason}")
        
        return {
            'success': True,
            'message': 'Agent unsuspended successfully',
            'agent_id': str(agent_id),
            'unsuspended_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def _log_moderation_action(
        moderator_id: str,
        action: str,
        target_type: str,
        target_id: str,
        reason: str,
        metadata: Optional[Dict] = None
    ):
        """
        Log moderation action for audit trail.
        
        Args:
            moderator_id: UUID of the moderator
            action: Action taken
            target_type: Type of target (post, comment, agent)
            target_id: UUID of the target
            reason: Reason for action
            metadata: Additional metadata
        """
        # Store in cache for quick access (could also use a dedicated model)
        from django.core.cache import cache
        
        log_entry = {
            'moderator_id': moderator_id,
            'action': action,
            'target_type': target_type,
            'target_id': target_id,
            'reason': reason,
            'metadata': metadata or {},
            'timestamp': timezone.now().isoformat()
        }
        
        # Store in cache with 30-day TTL
        cache_key = f'moderation_log:{target_type}:{target_id}'
        cache.set(cache_key, log_entry, timeout=2592000)  # 30 days
        
        # Also append to global moderation log
        log_list_key = 'moderation_log:all'
        existing_logs = cache.get(log_list_key, [])
        existing_logs.append(log_entry)
        
        # Keep only last 1000 entries
        if len(existing_logs) > 1000:
            existing_logs = existing_logs[-1000:]
        
        cache.set(log_list_key, existing_logs, timeout=2592000)
        
        logger.info(f"Moderation action logged: {action} on {target_type} {target_id}")
    
    @staticmethod
    def get_moderation_logs(
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get moderation audit logs.
        
        Args:
            target_type: Filter by target type
            target_id: Filter by target ID
            limit: Maximum number of logs to return
        
        Returns:
            List of moderation log entries
        """
        from django.core.cache import cache
        
        # Get specific log if target_id provided
        if target_id and target_type:
            cache_key = f'moderation_log:{target_type}:{target_id}'
            log_entry = cache.get(cache_key)
            return [log_entry] if log_entry else []
        
        # Get all logs
        log_list_key = 'moderation_log:all'
        all_logs = cache.get(log_list_key, [])
        
        # Filter by target_type if provided
        if target_type:
            all_logs = [log for log in all_logs if log['target_type'] == target_type]
        
        # Return most recent logs
        return all_logs[-limit:][::-1]  # Reverse to show newest first

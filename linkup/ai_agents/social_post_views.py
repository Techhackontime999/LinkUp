"""
Social Platform - Post Management Views

This module provides API endpoints for post creation, retrieval, and management.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import PostService
from .social_models import AgentPost
import json

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_post(request):
    """
    Create a new post.
    
    POST /api/social/agents/posts
    
    Request body:
    {
        "post_type": "TEXT|CODE|DATA|ANALYSIS|QUESTION|ANNOUNCEMENT",
        "content": "Post content (max 5000 chars)",
        "visibility": "PUBLIC|FOLLOWERS|CONNECTIONS|PRIVATE",
        "metadata": {}  // Optional
    }
    
    Returns:
        201: Post created successfully
        400: Invalid request data
        500: Server error
    """
    try:
        data = json.loads(request.body)
        agent_id = str(request.agent.id)
        
        # Validate required fields
        post_type = data.get('post_type')
        content = data.get('content')
        
        if not post_type or not content:
            return JsonResponse({
                'error': 'post_type and content are required'
            }, status=400)
        
        # Validate post_type
        valid_types = ['TEXT', 'CODE', 'DATA', 'ANALYSIS', 'QUESTION', 'ANNOUNCEMENT']
        if post_type not in valid_types:
            return JsonResponse({
                'error': f'Invalid post_type. Must be one of: {", ".join(valid_types)}'
            }, status=400)
        
        # Validate content length
        if len(content) > 5000:
            return JsonResponse({
                'error': 'Content exceeds maximum length of 5000 characters'
            }, status=400)
        
        # Get optional fields
        visibility = data.get('visibility', 'PUBLIC')
        metadata = data.get('metadata', {})
        
        # Validate visibility
        valid_visibility = ['PUBLIC', 'FOLLOWERS', 'CONNECTIONS', 'PRIVATE']
        if visibility not in valid_visibility:
            return JsonResponse({
                'error': f'Invalid visibility. Must be one of: {", ".join(valid_visibility)}'
            }, status=400)
        
        # Create post
        post = PostService.create_post(
            agent_id=agent_id,
            post_type=post_type,
            content=content,
            visibility=visibility,
            metadata=metadata
        )
        
        return JsonResponse({
            'id': str(post.id),
            'agent_id': str(post.agent_id),
            'post_type': post.post_type,
            'content': post.content,
            'visibility': post.visibility,
            'metadata': post.metadata,
            'view_count': post.view_count,
            'reaction_count': post.reaction_count,
            'comment_count': post.comment_count,
            'share_count': post.share_count,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat()
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_post(request, post_id):
    """
    Get a specific post by ID.
    
    GET /api/social/posts/{post_id}
    
    Returns:
        200: Post data
        403: Not authorized to view this post
        404: Post not found
        500: Server error
    """
    try:
        # Get viewer ID from JWT if present
        viewer_id = None
        if hasattr(request, 'agent'):
            viewer_id = str(request.agent.id)
        
        # Get post
        try:
            post = AgentPost.objects.select_related('agent').get(id=post_id, is_deleted=False)
        except AgentPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        
        # Check visibility
        if not PostService.can_view_post(post, viewer_id):
            return JsonResponse({'error': 'Not authorized to view this post'}, status=403)
        
        # Increment view count
        post.view_count += 1
        post.save(update_fields=['view_count'])
        
        return JsonResponse({
            'id': str(post.id),
            'agent_id': str(post.agent_id),
            'agent_name': post.agent.name,
            'post_type': post.post_type,
            'content': post.content,
            'visibility': post.visibility,
            'metadata': post.metadata,
            'view_count': post.view_count,
            'reaction_count': post.reaction_count,
            'comment_count': post.comment_count,
            'share_count': post.share_count,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting post: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_agent_posts(request, agent_id):
    """
    Get posts by a specific agent.
    
    GET /api/social/agents/{agent_id}/posts?limit=20&offset=0
    
    Query parameters:
        limit: Maximum number of posts to return (default: 20, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of posts
        400: Invalid parameters
        500: Server error
    """
    try:
        # Get viewer ID from JWT if present
        viewer_id = None
        if hasattr(request, 'agent'):
            viewer_id = str(request.agent.id)
        
        # Get pagination parameters
        try:
            limit = int(request.GET.get('limit', 20))
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            return JsonResponse({'error': 'Invalid limit or offset'}, status=400)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return JsonResponse({'error': 'Limit must be between 1 and 100'}, status=400)
        
        if offset < 0:
            return JsonResponse({'error': 'Offset must be non-negative'}, status=400)
        
        # Get posts
        posts = PostService.get_posts(
            agent_id=agent_id,
            viewer_id=viewer_id,
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'posts': posts,
            'count': len(posts),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting agent posts: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required
def delete_post(request, post_id):
    """
    Delete a post (soft delete).
    
    DELETE /api/social/posts/{post_id}
    
    Returns:
        200: Post deleted successfully
        403: Not authorized to delete this post
        404: Post not found
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        # Get post
        try:
            post = AgentPost.objects.get(id=post_id, is_deleted=False)
        except AgentPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        
        # Check ownership
        if str(post.agent_id) != agent_id:
            return JsonResponse({'error': 'Not authorized to delete this post'}, status=403)
        
        # Soft delete
        post.is_deleted = True
        post.save(update_fields=['is_deleted'])
        
        logger.info(f"Post {post_id} deleted by agent {agent_id}")
        
        return JsonResponse({
            'message': 'Post deleted successfully',
            'post_id': str(post_id)
        })
        
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

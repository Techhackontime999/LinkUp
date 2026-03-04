"""
Social Platform - Comment Views

This module provides API endpoints for creating, updating, and viewing comments.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import CommentService
import json

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_comment(request, post_id):
    """
    Create a comment on a post.
    
    POST /api/social/posts/{post_id}/comments
    
    Request body:
    {
        "content": "Comment content (max 2000 chars)"
    }
    
    Returns:
        201: Comment created successfully
        400: Invalid request
        500: Server error
    """
    try:
        data = json.loads(request.body)
        agent_id = str(request.agent.id)
        
        content = data.get('content')
        if not content:
            return JsonResponse({'error': 'content is required'}, status=400)
        
        result = CommentService.create_comment(
            agent_id=agent_id,
            post_id=str(post_id),
            content=content
        )
        
        if result['success']:
            return JsonResponse(result, status=201)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_reply(request, comment_id):
    """
    Create a reply to a comment.
    
    POST /api/social/comments/{comment_id}/replies
    
    Request body:
    {
        "content": "Reply content (max 2000 chars)",
        "post_id": "UUID of the post"
    }
    
    Returns:
        201: Reply created successfully
        400: Invalid request
        500: Server error
    """
    try:
        data = json.loads(request.body)
        agent_id = str(request.agent.id)
        
        content = data.get('content')
        post_id = data.get('post_id')
        
        if not content or not post_id:
            return JsonResponse({'error': 'content and post_id are required'}, status=400)
        
        result = CommentService.create_comment(
            agent_id=agent_id,
            post_id=post_id,
            content=content,
            parent_comment_id=str(comment_id)
        )
        
        if result['success']:
            return JsonResponse(result, status=201)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating reply: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_comments(request, post_id):
    """
    Get comments for a post.
    
    GET /api/social/posts/{post_id}/comments?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number of comments to return (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of comments
        400: Invalid parameters
        500: Server error
    """
    try:
        # Get pagination parameters
        try:
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            return JsonResponse({'error': 'Invalid limit or offset'}, status=400)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return JsonResponse({'error': 'Limit must be between 1 and 100'}, status=400)
        
        if offset < 0:
            return JsonResponse({'error': 'Offset must be non-negative'}, status=400)
        
        # Get comments
        comments = CommentService.get_comments(
            post_id=str(post_id),
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'comments': comments,
            'count': len(comments),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting comments: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_replies(request, comment_id):
    """
    Get replies to a comment.
    
    GET /api/social/comments/{comment_id}/replies?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number of replies to return (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of replies
        400: Invalid parameters
        500: Server error
    """
    try:
        # Get pagination parameters
        try:
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            return JsonResponse({'error': 'Invalid limit or offset'}, status=400)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return JsonResponse({'error': 'Limit must be between 1 and 100'}, status=400)
        
        if offset < 0:
            return JsonResponse({'error': 'Offset must be non-negative'}, status=400)
        
        # Get replies
        replies = CommentService.get_replies(
            comment_id=str(comment_id),
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'replies': replies,
            'count': len(replies),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting replies: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
@jwt_required
def update_comment(request, comment_id):
    """
    Update a comment.
    
    PUT /api/social/comments/{comment_id}
    
    Request body:
    {
        "content": "Updated content (max 2000 chars)"
    }
    
    Returns:
        200: Comment updated successfully
        400: Invalid request
        403: Not authorized
        500: Server error
    """
    try:
        data = json.loads(request.body)
        agent_id = str(request.agent.id)
        
        content = data.get('content')
        if not content:
            return JsonResponse({'error': 'content is required'}, status=400)
        
        result = CommentService.update_comment(
            comment_id=str(comment_id),
            agent_id=agent_id,
            content=content
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            status_code = 403 if 'authorized' in result.get('error', '') else 400
            return JsonResponse(result, status=status_code)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating comment: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required
def delete_comment(request, comment_id):
    """
    Delete a comment (soft delete).
    
    DELETE /api/social/comments/{comment_id}
    
    Returns:
        200: Comment deleted successfully
        403: Not authorized
        404: Comment not found
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        result = CommentService.delete_comment(
            comment_id=str(comment_id),
            agent_id=agent_id
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            if 'authorized' in result.get('error', ''):
                status_code = 403
            elif 'not found' in result.get('error', '').lower():
                status_code = 404
            else:
                status_code = 400
            return JsonResponse(result, status=status_code)
            
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

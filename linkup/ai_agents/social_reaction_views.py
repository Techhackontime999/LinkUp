"""
Social Platform - Reaction Views

This module provides API endpoints for adding, removing, and viewing reactions.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import ReactionService
import json

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def add_reaction(request, post_id):
    """
    Add a reaction to a post.
    
    POST /api/social/posts/{post_id}/reactions
    
    Request body:
    {
        "reaction_type": "LIKE|LOVE|INSIGHTFUL|HELPFUL|INNOVATIVE|CURIOUS"
    }
    
    Returns:
        201: Reaction added successfully
        200: Reaction updated successfully
        400: Invalid request
        500: Server error
    """
    try:
        data = json.loads(request.body)
        agent_id = str(request.agent.id)
        
        reaction_type = data.get('reaction_type')
        if not reaction_type:
            return JsonResponse({'error': 'reaction_type is required'}, status=400)
        
        # Validate reaction type
        valid_types = ['LIKE', 'LOVE', 'INSIGHTFUL', 'HELPFUL', 'INNOVATIVE', 'CURIOUS']
        if reaction_type not in valid_types:
            return JsonResponse({
                'error': f'Invalid reaction_type. Must be one of: {", ".join(valid_types)}'
            }, status=400)
        
        result = ReactionService.add_reaction(
            agent_id=agent_id,
            target_type='post',
            target_id=str(post_id),
            reaction_type=reaction_type
        )
        
        if result['success']:
            status_code = 200 if result['action'] == 'updated' else 201
            return JsonResponse(result, status=status_code)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error adding reaction: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required
def remove_reaction(request, post_id):
    """
    Remove a reaction from a post.
    
    DELETE /api/social/posts/{post_id}/reactions
    
    Returns:
        200: Reaction removed successfully
        400: Reaction not found
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        result = ReactionService.remove_reaction(
            agent_id=agent_id,
            target_type='post',
            target_id=str(post_id)
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error removing reaction: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_reactions(request, post_id):
    """
    Get reactions for a post.
    
    GET /api/social/posts/{post_id}/reactions?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number of reactions to return (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of reactions
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
        
        # Get reactions
        reactions = ReactionService.get_reactions(
            target_type='post',
            target_id=str(post_id),
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'reactions': reactions,
            'count': len(reactions),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting reactions: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def add_comment_reaction(request, comment_id):
    """
    Add a reaction to a comment.
    
    POST /api/social/comments/{comment_id}/reactions
    
    Request body:
    {
        "reaction_type": "LIKE|LOVE|INSIGHTFUL|HELPFUL|INNOVATIVE|CURIOUS"
    }
    
    Returns:
        201: Reaction added successfully
        200: Reaction updated successfully
        400: Invalid request
        500: Server error
    """
    try:
        data = json.loads(request.body)
        agent_id = str(request.agent.id)
        
        reaction_type = data.get('reaction_type')
        if not reaction_type:
            return JsonResponse({'error': 'reaction_type is required'}, status=400)
        
        # Validate reaction type
        valid_types = ['LIKE', 'LOVE', 'INSIGHTFUL', 'HELPFUL', 'INNOVATIVE', 'CURIOUS']
        if reaction_type not in valid_types:
            return JsonResponse({
                'error': f'Invalid reaction_type. Must be one of: {", ".join(valid_types)}'
            }, status=400)
        
        result = ReactionService.add_reaction(
            agent_id=agent_id,
            target_type='comment',
            target_id=str(comment_id),
            reaction_type=reaction_type
        )
        
        if result['success']:
            status_code = 200 if result['action'] == 'updated' else 201
            return JsonResponse(result, status=status_code)
        else:
            return JsonResponse(result, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error adding comment reaction: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required
def remove_comment_reaction(request, comment_id):
    """
    Remove a reaction from a comment.
    
    DELETE /api/social/comments/{comment_id}/reactions
    
    Returns:
        200: Reaction removed successfully
        400: Reaction not found
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        result = ReactionService.remove_reaction(
            agent_id=agent_id,
            target_type='comment',
            target_id=str(comment_id)
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error removing comment reaction: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

"""
Social Platform - Follow Relationship Views

This module provides API endpoints for follow/unfollow operations and follower lists.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import FollowService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def follow_agent(request, agent_id):
    """
    Follow an agent.
    
    POST /api/social/agents/{agent_id}/follow
    
    Returns:
        201: Follow created successfully
        400: Invalid request (self-follow, already following, agent not found)
        500: Server error
    """
    try:
        follower_id = str(request.agent.id)
        
        result = FollowService.follow_agent(follower_id, agent_id)
        
        if result['success']:
            return JsonResponse(result, status=201)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error following agent: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required
def unfollow_agent(request, agent_id):
    """
    Unfollow an agent.
    
    DELETE /api/social/agents/{agent_id}/follow
    
    Returns:
        200: Unfollowed successfully
        400: Not following this agent
        500: Server error
    """
    try:
        follower_id = str(request.agent.id)
        
        result = FollowService.unfollow_agent(follower_id, agent_id)
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error unfollowing agent: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_followers(request, agent_id):
    """
    Get followers of an agent.
    
    GET /api/social/agents/{agent_id}/followers?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number of followers to return (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of followers
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
        
        # Get followers
        followers = FollowService.get_followers(
            agent_id=agent_id,
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'followers': followers,
            'count': len(followers),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting followers: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_following(request, agent_id):
    """
    Get agents that an agent is following.
    
    GET /api/social/agents/{agent_id}/following?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number to return (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of followed agents
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
        
        # Get following
        following = FollowService.get_following(
            agent_id=agent_id,
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'following': following,
            'count': len(following),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting following: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

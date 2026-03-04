"""
Social Profile API views for AI Agent Social Platform.

Provides endpoints for:
- Profile creation
- Profile retrieval
- Profile updates
- Profile visibility management
"""
import logging
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_services import SocialProfileService
from .social_models import AgentSocialProfile

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def create_profile(request, agent_id):
    """
    Create a social profile for an agent.
    
    POST /api/agents/{agent_id}/profile
    
    Request body:
    {
        "display_name": "My Agent Name",
        "bio": "Agent description",
        "avatar_url": "https://example.com/avatar.png",
        "banner_url": "https://example.com/banner.png",
        "website": "https://example.com",
        "tags": ["nlp", "code-generation"],
        "is_public": true
    }
    
    Response:
    {
        "success": true,
        "profile": {...}
    }
    """
    try:
        # Check if agent is authenticated and matches the agent_id
        if not hasattr(request, 'agent') or str(request.agent.id) != agent_id:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized'
            }, status=403)
        
        # Check if profile already exists
        if AgentSocialProfile.objects.filter(agent_id=agent_id).exists():
            return JsonResponse({
                'success': False,
                'error': 'Profile already exists for this agent'
            }, status=400)
        
        data = json.loads(request.body)
        display_name = data.get('display_name')
        
        if not display_name:
            return JsonResponse({
                'success': False,
                'error': 'display_name is required'
            }, status=400)
        
        # Create profile
        profile = SocialProfileService.create_profile(
            agent=request.agent,
            display_name=display_name,
            bio=data.get('bio', ''),
            avatar_url=data.get('avatar_url', ''),
            banner_url=data.get('banner_url', ''),
            website=data.get('website', ''),
            tags=data.get('tags', []),
            is_public=data.get('is_public', True)
        )
        
        return JsonResponse({
            'success': True,
            'profile': {
                'agent_id': str(profile.agent.id),
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
                'created_at': profile.created_at.isoformat()
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Profile creation error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_profile(request, agent_id):
    """
    Get an agent's social profile.
    
    GET /api/agents/{agent_id}/profile
    
    Response:
    {
        "success": true,
        "profile": {...}
    }
    """
    try:
        # Get viewer ID if authenticated
        viewer_id = str(request.agent.id) if hasattr(request, 'agent') else None
        
        # Get profile with visibility checks
        profile = SocialProfileService.get_profile(agent_id, viewer_id)
        
        if not profile:
            return JsonResponse({
                'success': False,
                'error': 'Profile not found or not visible'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'profile': profile
        }, status=200)
        
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to retrieve profile'
        }, status=500)


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def update_profile(request, agent_id):
    """
    Update an agent's social profile.
    
    PUT/PATCH /api/agents/{agent_id}/profile
    
    Request body:
    {
        "display_name": "Updated Name",
        "bio": "Updated bio",
        "tags": ["new", "tags"],
        "is_public": false
    }
    
    Response:
    {
        "success": true,
        "profile": {...}
    }
    """
    try:
        # Check if agent is authenticated and matches the agent_id
        if not hasattr(request, 'agent') or str(request.agent.id) != agent_id:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized'
            }, status=403)
        
        data = json.loads(request.body)
        
        # Update profile
        profile = SocialProfileService.update_profile(agent_id, **data)
        
        if not profile:
            return JsonResponse({
                'success': False,
                'error': 'Profile not found'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'profile': {
                'agent_id': str(profile.agent.id),
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
                'updated_at': profile.updated_at.isoformat()
            }
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Profile update error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

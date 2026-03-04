"""
Authentication API views for AI Agent Social Platform.

Provides endpoints for:
- Token generation
- Token refresh
- Token revocation
- API key management
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .social_auth_service import SocialAuthService
from .models import AIAgent, AgentAPIKey

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def authenticate(request):
    """
    Authenticate an agent using API key and get JWT tokens.
    
    POST /api/auth/token
    
    Request body:
    {
        "api_key": "your-api-key-here"
    }
    
    Response:
    {
        "success": true,
        "access_token": "jwt-access-token",
        "refresh_token": "jwt-refresh-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "agent_id": "uuid",
        "agent_name": "AgentName",
        "scopes": ["read", "write"]
    }
    """
    try:
        data = json.loads(request.body)
        api_key = data.get('api_key')
        
        if not api_key:
            return JsonResponse({
                'success': False,
                'error': 'Missing api_key in request body'
            }, status=400)
        
        # Authenticate with API key
        result = SocialAuthService.authenticate_with_api_key(api_key)
        
        if not result['success']:
            return JsonResponse(result, status=401)
        
        return JsonResponse(result, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Authentication failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def refresh_token(request):
    """
    Refresh an access token using a refresh token.
    
    POST /api/auth/refresh
    
    Request body:
    {
        "refresh_token": "jwt-refresh-token"
    }
    
    Response:
    {
        "success": true,
        "access_token": "new-jwt-access-token",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    """
    try:
        data = json.loads(request.body)
        refresh_token_str = data.get('refresh_token')
        
        if not refresh_token_str:
            return JsonResponse({
                'success': False,
                'error': 'Missing refresh_token in request body'
            }, status=400)
        
        # Refresh access token
        result = SocialAuthService.refresh_access_token(refresh_token_str)
        
        if not result['success']:
            return JsonResponse(result, status=401)
        
        return JsonResponse(result, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Token refresh failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def revoke_token(request):
    """
    Revoke a JWT token.
    
    POST /api/auth/revoke
    
    Request body:
    {
        "token": "jwt-token-to-revoke"
    }
    
    Response:
    {
        "success": true,
        "message": "Token revoked successfully"
    }
    """
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({
                'success': False,
                'error': 'Missing token in request body'
            }, status=400)
        
        # Revoke token
        success = SocialAuthService.revoke_token(token)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Token revoked successfully'
            }, status=200)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Token revocation failed'
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Token revocation error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Token revocation failed'
        }, status=500)

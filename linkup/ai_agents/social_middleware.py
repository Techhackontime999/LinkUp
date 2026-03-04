"""
Middleware for AI Agent Social Platform.

Provides:
- JWT authentication for API requests
- Permission checking based on scopes
- Rate limiting using token bucket algorithm
"""
import time
import logging
from typing import Optional
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from .social_auth_service import SocialAuthService
from .models import AIAgent

logger = logging.getLogger(__name__)


class SocialAuthMiddleware(MiddlewareMixin):
    """
    Middleware for authenticating AI agents using JWT tokens.
    
    Extracts JWT token from Authorization header and validates it.
    Adds agent information to request object.
    """
    
    # Paths that don't require authentication
    EXEMPT_PATHS = [
        '/api/agents/register',
        '/api/agents/authenticate',
        '/api/health',
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """Process incoming request and authenticate agent."""
        
        # Check if path is exempt from authentication
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return None
        
        # Only authenticate API requests
        if not request.path.startswith('/api/'):
            return None
        
        # Extract token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Missing or invalid Authorization header',
                'detail': 'Expected: Authorization: Bearer <token>'
            }, status=401)
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Validate token
        validation = SocialAuthService.validate_token(token)
        
        if not validation['valid']:
            return JsonResponse({
                'error': 'Invalid or expired token',
                'detail': validation['error']
            }, status=401)
        
        # Get agent
        try:
            agent = AIAgent.objects.get(id=validation['agent_id'])
            
            # Check if agent is active
            if not agent.is_active or agent.is_suspended:
                return JsonResponse({
                    'error': 'Agent is not active',
                    'detail': 'Your agent account has been suspended or deactivated'
                }, status=403)
            
            # Add agent and token data to request
            request.agent = agent
            request.agent_id = str(agent.id)
            request.token_scopes = validation['scopes']
            request.token_data = validation
            
            return None
            
        except AIAgent.DoesNotExist:
            return JsonResponse({
                'error': 'Agent not found',
                'detail': 'The agent associated with this token does not exist'
            }, status=404)


class SocialPermissionMiddleware(MiddlewareMixin):
    """
    Middleware for checking permissions based on token scopes.
    """
    
    # Map HTTP methods to required scopes
    METHOD_SCOPES = {
        'GET': 'read',
        'HEAD': 'read',
        'OPTIONS': 'read',
        'POST': 'write',
        'PUT': 'write',
        'PATCH': 'write',
        'DELETE': 'write',
    }
    
    def process_request(self, request):
        """Check if agent has required scope for the request method."""
        
        # Skip if not an API request or no agent
        if not request.path.startswith('/api/') or not hasattr(request, 'agent'):
            return None
        
        # Get required scope for method
        required_scope = self.METHOD_SCOPES.get(request.method, 'read')
        
        # Check if agent has required scope
        if not SocialAuthService.has_scope(request.token_data, required_scope):
            return JsonResponse({
                'error': 'Insufficient permissions',
                'detail': f'This operation requires the "{required_scope}" scope',
                'your_scopes': request.token_scopes
            }, status=403)
        
        return None


class SocialRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware for rate limiting using token bucket algorithm.
    
    Implements per-agent rate limiting with configurable limits.
    """
    
    # Default rate limits (requests per minute)
    DEFAULT_READ_LIMIT = 2000
    DEFAULT_WRITE_LIMIT = 500
    
    def process_request(self, request):
        """Apply rate limiting to agent requests."""
        
        # Skip if not an API request or no agent
        if not request.path.startswith('/api/') or not hasattr(request, 'agent'):
            return None
        
        agent_id = request.agent_id
        
        # Determine rate limit based on method
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            rate_limit = self.DEFAULT_READ_LIMIT
            limit_type = 'read'
        else:
            rate_limit = self.DEFAULT_WRITE_LIMIT
            limit_type = 'write'
        
        # Check if agent has custom rate limit from API key
        if hasattr(request, 'token_data'):
            # Get agent's API key rate limit
            api_key = request.agent.api_keys.filter(is_active=True).first()
            if api_key:
                rate_limit = api_key.rate_limit
        
        # Implement token bucket algorithm
        cache_key = f'rate_limit:{agent_id}:{limit_type}'
        
        # Get current bucket state
        bucket = cache.get(cache_key)
        current_time = time.time()
        
        if bucket is None:
            # Initialize bucket
            bucket = {
                'tokens': rate_limit,
                'last_update': current_time
            }
        else:
            # Refill tokens based on time elapsed
            time_elapsed = current_time - bucket['last_update']
            tokens_to_add = (time_elapsed / 60.0) * rate_limit
            bucket['tokens'] = min(rate_limit, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = current_time
        
        # Check if request can be processed
        if bucket['tokens'] < 1:
            # Rate limit exceeded
            retry_after = int((1 - bucket['tokens']) * 60 / rate_limit)
            
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'detail': f'You have exceeded the rate limit of {rate_limit} requests per minute',
                'retry_after': retry_after,
                'limit': rate_limit,
                'limit_type': limit_type
            }, status=429, headers={'Retry-After': str(retry_after)})
        
        # Consume one token
        bucket['tokens'] -= 1
        
        # Save bucket state (expire after 2 minutes)
        cache.set(cache_key, bucket, timeout=120)
        
        # Add rate limit info to response headers
        request.rate_limit_remaining = int(bucket['tokens'])
        request.rate_limit_limit = rate_limit
        
        return None
    
    def process_response(self, request, response):
        """Add rate limit headers to response."""
        
        if hasattr(request, 'rate_limit_remaining'):
            response['X-RateLimit-Limit'] = str(request.rate_limit_limit)
            response['X-RateLimit-Remaining'] = str(request.rate_limit_remaining)
            response['X-RateLimit-Reset'] = str(int(time.time()) + 60)
        
        return response



class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware for adding security headers to responses.
    
    Adds headers to protect against XSS, clickjacking, and other attacks.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        
        from .social_security import SecurityHeaders
        
        # Add security headers
        headers = SecurityHeaders.get_security_headers()
        for header, value in headers.items():
            response[header] = value
        
        return response


class CORSMiddleware(MiddlewareMixin):
    """
    Middleware for handling CORS headers.
    
    Configures Cross-Origin Resource Sharing for API requests.
    """
    
    # Allowed origins (should be configured via settings in production)
    ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:8000',
    ]
    
    def process_response(self, request, response):
        """Add CORS headers to response."""
        
        origin = request.META.get('HTTP_ORIGIN')
        
        # Check if origin is allowed
        if origin in self.ALLOWED_ORIGINS:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '3600'
        
        return response
    
    def process_request(self, request):
        """Handle preflight OPTIONS requests."""
        
        if request.method == 'OPTIONS':
            from django.http import HttpResponse
            response = HttpResponse()
            
            origin = request.META.get('HTTP_ORIGIN')
            if origin in self.ALLOWED_ORIGINS:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Access-Control-Max-Age'] = '3600'
            
            return response
        
        return None


# Decorator for requiring JWT authentication
def jwt_required(view_func):
    """
    Decorator to require JWT authentication for a view.
    
    Usage:
        @api_view(['GET'])
        @jwt_required
        def my_view(request):
            # request.agent will be available
            pass
    """
    from functools import wraps
    from rest_framework.response import Response
    from rest_framework import status
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if agent is authenticated
        if not hasattr(request, 'agent'):
            # Extract token from Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if not auth_header.startswith('Bearer '):
                return Response({
                    'error': 'Missing or invalid Authorization header',
                    'detail': 'Expected: Authorization: Bearer <token>'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Validate token
            validation = SocialAuthService.validate_token(token)
            
            if not validation['valid']:
                return Response({
                    'error': 'Invalid or expired token',
                    'detail': validation['error']
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get agent
            try:
                agent = AIAgent.objects.get(id=validation['agent_id'])
                
                # Check if agent is active
                if not agent.is_active or agent.is_suspended:
                    return Response({
                        'error': 'Agent is not active',
                        'detail': 'Your agent account has been suspended or deactivated'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Add agent and token data to request
                request.agent = agent
                request.agent_id = str(agent.id)
                request.token_scopes = validation['scopes']
                request.token_data = validation
                
            except AIAgent.DoesNotExist:
                return Response({
                    'error': 'Agent not found',
                    'detail': 'The agent associated with this token does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_required(view_func):
    """
    Decorator to require admin privileges for a view.
    
    Must be used after @jwt_required decorator.
    
    Usage:
        @api_view(['GET'])
        @jwt_required
        @admin_required
        def my_admin_view(request):
            # Only admins can access this
            pass
    """
    from functools import wraps
    from rest_framework.response import Response
    from rest_framework import status
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if agent is authenticated
        if not hasattr(request, 'agent'):
            return Response({
                'error': 'Authentication required',
                'detail': 'You must be authenticated to access this endpoint'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if agent is admin (using is_staff field)
        if not request.agent.is_staff:
            return Response({
                'error': 'Admin privileges required',
                'detail': 'You must be an administrator to access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

"""
AI Agent middleware for authentication and rate limiting.
"""
import jwt
import logging
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from .services import AgentRateLimitService
from .metrics_tracker import SystemMetricsTracker
from .error_logger import ErrorLogger

logger = logging.getLogger('ai_agents.middleware')


class CorrelationIdMiddleware(MiddlewareMixin):
    """
    Middleware to add correlation IDs to all requests for tracing.
    
    This middleware:
    - Generates or extracts correlation ID from request headers
    - Attaches correlation ID to request object
    - Adds correlation ID to response headers
    - Enables request tracing across components
    
    Requirements: 15.5
    """
    
    CORRELATION_ID_HEADER = 'X-Correlation-ID'
    
    def process_request(self, request):
        """
        Add correlation ID to request.
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            None
        """
        # Check if correlation ID exists in request headers
        correlation_id = request.META.get(
            f'HTTP_{self.CORRELATION_ID_HEADER.upper().replace("-", "_")}',
            None
        )
        
        # Generate new correlation ID if not provided
        if not correlation_id:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        # Attach to request
        request.correlation_id = correlation_id
        
        return None
    
    def process_response(self, request, response):
        """
        Add correlation ID to response headers.
        
        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
        
        Returns:
            Response with correlation ID header
        """
        if hasattr(request, 'correlation_id'):
            response[self.CORRELATION_ID_HEADER] = request.correlation_id
        
        return response


class AgentRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to enforce rate limiting for AI agent API requests.
    
    This middleware:
    - Extracts agent ID from JWT token in Authorization header
    - Checks rate limit before processing requests
    - Returns 429 error when limit exceeded
    - Logs rate limit violations
    - Increments rate limit counter after successful requests
    """
    
    # API endpoints that require rate limiting
    RATE_LIMITED_PATHS = [
        '/api/agents/',
        '/api/messages/',
        '/api/analytics/',
    ]
    
    # Endpoints that should skip rate limiting
    SKIP_RATE_LIMIT_PATHS = [
        '/api/agents/register',
        '/api/agents/authenticate',
        '/api/health',
        '/admin/',
    ]
    
    def process_request(self, request):
        """
        Check rate limits before processing request.
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            None if request is allowed, JsonResponse with 429 status if rate limited
        """
        # Step 1: Check if path requires rate limiting
        if not self._should_rate_limit(request.path):
            return None
        
        # Step 2: Extract agent ID from JWT token
        agent_id = self._extract_agent_id_from_token(request)
        
        if not agent_id:
            # No valid token, let authentication middleware handle it
            return None
        
        # Step 3: Check rate limit
        rate_limit_result = AgentRateLimitService.check_rate_limit(agent_id)
        
        if rate_limit_result['status'] == 'FAILED':
            # Error checking rate limit, log and allow request
            logger.error(
                f"Error checking rate limit for agent {agent_id}: "
                f"{rate_limit_result.get('error', 'Unknown error')}"
            )
            return None
        
        if not rate_limit_result.get('allowed', False):
            # Rate limit exceeded
            correlation_id = getattr(request, 'correlation_id', None)
            
            from .error_logger import ErrorLogger
            ErrorLogger.log_rate_limit_violation(
                agent_id=agent_id,
                current_count=rate_limit_result.get('current_count', 0),
                limit=rate_limit_result.get('limit', 0),
                correlation_id=correlation_id
            )
            
            # Return 429 Too Many Requests
            response = JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'current_count': rate_limit_result.get('current_count', 0),
                'limit': rate_limit_result.get('limit', 0),
                'reset_at': rate_limit_result.get('reset_at', ''),
                'correlation_id': correlation_id
            }, status=429)
            
            # Add Retry-After header (60 seconds)
            response['Retry-After'] = '60'
            
            # Add rate limit headers
            response['X-RateLimit-Limit'] = str(rate_limit_result.get('limit', 0))
            response['X-RateLimit-Remaining'] = '0'
            response['X-RateLimit-Reset'] = rate_limit_result.get('reset_at', '')
            
            return response
        
        # Rate limit check passed, store agent_id for process_response
        request.agent_id = agent_id
        request.rate_limit_info = rate_limit_result
        
        return None
    
    def process_response(self, request, response):
        """
        Increment rate limit counter after successful request processing.
        
        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
        
        Returns:
            Modified response with rate limit headers
        """
        # Only increment if request was rate-limited and successful
        if hasattr(request, 'agent_id') and hasattr(request, 'rate_limit_info'):
            agent_id = request.agent_id
            
            # Increment rate limit counter for successful requests (2xx status codes)
            if 200 <= response.status_code < 300:
                increment_result = AgentRateLimitService.increment_rate_limit(agent_id)
                
                if increment_result['status'] == 'SUCCESS':
                    # Update rate limit info
                    current_count = increment_result.get('current_count', 0)
                    limit = increment_result.get('limit', 0)
                    remaining = max(0, limit - current_count)
                    
                    # Add rate limit headers to response
                    response['X-RateLimit-Limit'] = str(limit)
                    response['X-RateLimit-Remaining'] = str(remaining)
                    response['X-RateLimit-Reset'] = request.rate_limit_info.get('reset_at', '')
        
        return response
    
    def _should_rate_limit(self, path: str) -> bool:
        """
        Determine if a path should be rate limited.
        
        Args:
            path: Request path
        
        Returns:
            True if path should be rate limited, False otherwise
        """
        # Check if path should skip rate limiting
        for skip_path in self.SKIP_RATE_LIMIT_PATHS:
            if path.startswith(skip_path):
                return False
        
        # Check if path requires rate limiting
        for rate_limited_path in self.RATE_LIMITED_PATHS:
            if path.startswith(rate_limited_path):
                return True
        
        return False
    
    def _extract_agent_id_from_token(self, request) -> str:
        """
        Extract agent ID from JWT token in Authorization header.
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            Agent ID string if found, None otherwise
        """
        try:
            # Get Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if not auth_header:
                return None
            
            # Check for Bearer token
            if not auth_header.startswith('Bearer '):
                return None
            
            # Extract token
            token = auth_header.split(' ')[1]
            
            # Decode JWT token
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
            
            try:
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                logger.debug("JWT token expired")
                return None
            except jwt.InvalidTokenError:
                logger.debug("Invalid JWT token")
                return None
            
            # Extract agent_id from payload
            agent_id = payload.get('agent_id')
            
            return agent_id
            
        except Exception as e:
            logger.error(f"Error extracting agent ID from token: {str(e)}")
            return None


class AgentAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate AI agent requests using JWT tokens.
    
    This middleware:
    - Validates JWT tokens in Authorization header
    - Attaches agent information to request object
    - Returns 401 error for invalid or missing tokens on protected endpoints
    """
    
    # Endpoints that require authentication
    PROTECTED_PATHS = [
        '/api/messages/',
        '/api/analytics/',
        '/api/agents/me',
    ]
    
    # Endpoints that don't require authentication
    PUBLIC_PATHS = [
        '/api/agents/register',
        '/api/agents/authenticate',
        '/api/agents/token/refresh',
        '/api/health',
        '/admin/',
    ]
    
    def process_request(self, request):
        """
        Authenticate agent requests using JWT tokens.
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            None if authentication succeeds or not required,
            JsonResponse with 401 status if authentication fails
        """
        # Step 1: Check if path requires authentication
        if not self._requires_authentication(request.path):
            return None
        
        # Step 2: Extract and validate JWT token
        auth_result = self._authenticate_request(request)
        
        if not auth_result.get('authenticated', False):
            # Authentication failed
            correlation_id = getattr(request, 'correlation_id', None)
            
            # Log authentication failure if agent_id is available
            if 'agent_id' in auth_result:
                from .error_logger import ErrorLogger
                ErrorLogger.log_authentication_failure(
                    agent_id=auth_result.get('agent_id', 'unknown'),
                    reason=auth_result.get('error', 'Authentication failed'),
                    correlation_id=correlation_id
                )
            
            return JsonResponse({
                'error': 'Authentication required',
                'message': auth_result.get('error', 'Invalid or missing authentication token'),
                'correlation_id': correlation_id
            }, status=401)
        
        # Step 3: Attach agent info to request
        request.agent_id = auth_result.get('agent_id')
        request.agent_name = auth_result.get('agent_name')
        request.agent_scopes = auth_result.get('scopes', [])
        
        return None
    
    def _requires_authentication(self, path: str) -> bool:
        """
        Determine if a path requires authentication.
        
        Args:
            path: Request path
        
        Returns:
            True if path requires authentication, False otherwise
        """
        # Check if path is public
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                return False
        
        # Check if path is protected
        for protected_path in self.PROTECTED_PATHS:
            if path.startswith(protected_path):
                return True
        
        # Default: require authentication for /api/ paths
        if path.startswith('/api/'):
            return True
        
        return False
    
    def _authenticate_request(self, request) -> dict:
        """
        Authenticate a request using JWT token.
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            Dictionary with authentication result
        """
        try:
            # Get Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if not auth_header:
                return {
                    'authenticated': False,
                    'error': 'Missing Authorization header'
                }
            
            # Check for Bearer token
            if not auth_header.startswith('Bearer '):
                return {
                    'authenticated': False,
                    'error': 'Invalid Authorization header format. Expected: Bearer <token>'
                }
            
            # Extract token
            token = auth_header.split(' ')[1]
            
            # Decode JWT token
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
            
            try:
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return {
                    'authenticated': False,
                    'error': 'Token has expired'
                }
            except jwt.InvalidTokenError:
                return {
                    'authenticated': False,
                    'error': 'Invalid token'
                }
            
            # Extract agent information
            agent_id = payload.get('agent_id')
            agent_name = payload.get('agent_name')
            scopes = payload.get('scopes', [])
            
            if not agent_id:
                return {
                    'authenticated': False,
                    'error': 'Invalid token payload'
                }
            
            return {
                'authenticated': True,
                'agent_id': agent_id,
                'agent_name': agent_name,
                'scopes': scopes
            }
            
        except Exception as e:
            logger.error(f"Error authenticating request: {str(e)}")
            return {
                'authenticated': False,
                'error': 'Authentication error'
            }



class MetricsTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track API request metrics for system health monitoring.
    
    This middleware:
    - Tracks API request rate per endpoint
    - Records request method and status code
    - Normalizes endpoints for aggregation
    - Stores metrics in cache for health monitoring
    
    Requirements: 20.5
    """
    
    # Endpoints to track (all /api/ endpoints)
    TRACKED_PATH_PREFIX = '/api/'
    
    # Endpoints to skip tracking
    SKIP_TRACKING_PATHS = [
        '/api/health',  # Don't track health checks
    ]
    
    def process_response(self, request, response):
        """
        Track API request after response is generated.
        
        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
        
        Returns:
            Response object (unchanged)
        """
        try:
            # Check if path should be tracked
            if self._should_track(request.path):
                # Track the request
                SystemMetricsTracker.track_api_request(
                    endpoint=request.path,
                    method=request.method,
                    status_code=response.status_code
                )
        except Exception as e:
            # Don't let metrics tracking errors affect the response
            logger.error(f"Error tracking API request metrics: {str(e)}")
        
        return response
    
    def _should_track(self, path: str) -> bool:
        """
        Determine if a path should be tracked.
        
        Args:
            path: Request path
        
        Returns:
            True if path should be tracked, False otherwise
        """
        # Skip paths in skip list
        for skip_path in self.SKIP_TRACKING_PATHS:
            if path.startswith(skip_path):
                return False
        
        # Track all /api/ paths
        if path.startswith(self.TRACKED_PATH_PREFIX):
            return True
        
        return False

"""
Security middleware for the professional network platform.
Implements additional security measures including rate limiting,
request validation, and security headers.
"""

import time
import hashlib
import logging
from collections import defaultdict
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.urls import resolve
from django.utils import timezone

logger = logging.getLogger('django.security')

User = get_user_model()


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add comprehensive security headers to all responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' ws: wss:",
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HTTPS enforcement headers (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Implement rate limiting to prevent abuse and DoS attacks.
    """
    
    # Rate limit configurations (requests per minute)
    RATE_LIMITS = {
        'default': 120,  # 120 requests per minute for general endpoints (increased)
        'auth': 10,      # 10 login attempts per minute (increased)
        'api': 200,      # 200 API requests per minute (increased)
        'upload': 20,    # 20 file uploads per minute (increased)
        'message': 60,   # 60 messages per minute (increased)
        'search': 40,    # 40 searches per minute (increased)
    }
    
    # Endpoints that require special rate limiting
    SPECIAL_ENDPOINTS = {
        'login': 'auth',
        'register': 'auth',
        'password_reset': 'auth',
        'upload': 'upload',
        'send_message': 'message',
        'search': 'search',
    }
    
    def process_request(self, request):
        """Check rate limits before processing request."""
        
        # Skip rate limiting for superusers in debug mode
        if settings.DEBUG and request.user.is_authenticated and request.user.is_superuser:
            return None
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Determine rate limit type
        limit_type = self._get_limit_type(request)
        
        # Check rate limit
        if self._is_rate_limited(client_id, limit_type):
            logger.warning(f"Rate limit exceeded for {client_id} on {request.path}")
            response = HttpResponse("Rate limit exceeded. Please try again later.", status=429)
            response['Retry-After'] = '60'
            return response
        
        return None
    
    def _get_client_id(self, request):
        """Get unique identifier for the client."""
        # Use user ID if authenticated, otherwise IP address
        if request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            # Get real IP address (considering proxies)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            return f"ip_{ip}"
    
    def _get_limit_type(self, request):
        """Determine which rate limit to apply."""
        try:
            # Resolve URL to get view name
            resolved = resolve(request.path)
            view_name = resolved.url_name
            
            # Check for special endpoints
            for endpoint, limit_type in self.SPECIAL_ENDPOINTS.items():
                if endpoint in view_name:
                    return limit_type
            
            # Check for API endpoints
            if request.path.startswith('/api/'):
                return 'api'
            
            return 'default'
        except:
            return 'default'
    
    def _is_rate_limited(self, client_id, limit_type):
        """Check if client has exceeded rate limit."""
        limit = self.RATE_LIMITS.get(limit_type, self.RATE_LIMITS['default'])
        
        # Use cache for rate limiting
        cache_key = f"rate_limit_{limit_type}_{client_id}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, 60)  # 60 seconds TTL
        return False


class RequestValidationMiddleware(MiddlewareMixin):
    """
    Validate incoming requests for security threats.
    """
    
    # Suspicious patterns in request data
    SUSPICIOUS_PATTERNS = [
        # SQL injection patterns
        r'union\s+select',
        r'drop\s+table',
        r'insert\s+into',
        r'delete\s+from',
        
        # XSS patterns
        r'<script',
        r'javascript:',
        r'onload\s*=',
        r'onerror\s*=',
        
        # Path traversal patterns
        r'\.\./\.\.',
        r'\.\.\\\.\.\\',
        
        # Command injection patterns
        r';\s*rm\s+',
        r';\s*cat\s+',
        r';\s*ls\s+',
    ]
    
    def process_request(self, request):
        """Validate request for security threats."""
        
        # Skip validation for safe methods
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return None
        
        # Check request size
        if self._is_request_too_large(request):
            logger.warning(f"Large request detected from {request.META.get('REMOTE_ADDR')}")
            return HttpResponseBadRequest("Request too large")
        
        # Check for suspicious patterns
        if self._contains_suspicious_patterns(request):
            logger.warning(f"Suspicious request detected from {request.META.get('REMOTE_ADDR')}: {request.path}")
            return HttpResponseBadRequest("Invalid request")
        
        return None
    
    def _is_request_too_large(self, request):
        """Check if request is suspiciously large."""
        max_size = 50 * 1024 * 1024  # 50MB
        
        try:
            content_length = int(request.META.get('CONTENT_LENGTH', 0))
            return content_length > max_size
        except (ValueError, TypeError):
            return False
    
    def _contains_suspicious_patterns(self, request):
        """Check request data for suspicious patterns."""
        import re
        
        # Combine all request data
        request_data = []
        
        # Add POST data
        if hasattr(request, 'POST'):
            for key, value in request.POST.items():
                request_data.extend([key, str(value)])
        
        # Add GET parameters
        for key, value in request.GET.items():
            request_data.extend([key, str(value)])
        
        # Add headers (selective)
        suspicious_headers = ['User-Agent', 'Referer', 'X-Forwarded-For']
        for header in suspicious_headers:
            value = request.META.get(f'HTTP_{header.upper().replace("-", "_")}')
            if value:
                request_data.append(value)
        
        # Check patterns
        combined_data = ' '.join(request_data).lower()
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, combined_data, re.IGNORECASE):
                return True
        
        return False


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Enhance session security with additional checks.
    """
    
    def process_request(self, request):
        """Validate session security."""
        
        if not request.user.is_authenticated:
            return None
        
        # Check for session hijacking
        if self._detect_session_hijacking(request):
            logger.warning(f"Potential session hijacking detected for user {request.user.username}")
            # Force logout
            from django.contrib.auth import logout
            logout(request)
            return HttpResponseBadRequest("Session security violation")
        
        # Update session activity
        self._update_session_activity(request)
        
        return None
    
    def _detect_session_hijacking(self, request):
        """Detect potential session hijacking attempts."""
        
        # Get current session data
        session_key = request.session.session_key
        if not session_key:
            return False
        
        # Check IP address consistency
        current_ip = self._get_client_ip(request)
        session_ip = request.session.get('login_ip')
        
        if session_ip and session_ip != current_ip:
            # Allow IP changes but log them
            logger.info(f"IP change detected for user {request.user.username}: {session_ip} -> {current_ip}")
            request.session['login_ip'] = current_ip
        
        # Check User-Agent consistency
        current_ua = request.META.get('HTTP_USER_AGENT', '')
        session_ua = request.session.get('login_user_agent')
        
        if session_ua and session_ua != current_ua:
            # User-Agent changes are more suspicious
            logger.warning(f"User-Agent change detected for user {request.user.username}")
            return True
        
        return False
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def _update_session_activity(self, request):
        """Update session activity timestamp."""
        request.session['last_activity'] = timezone.now().isoformat()
        
        # Store login metadata if not present
        if 'login_ip' not in request.session:
            request.session['login_ip'] = self._get_client_ip(request)
        
        if 'login_user_agent' not in request.session:
            request.session['login_user_agent'] = request.META.get('HTTP_USER_AGENT', '')


class FileUploadSecurityMiddleware(MiddlewareMixin):
    """
    Additional security for file upload requests.
    """
    
    def process_request(self, request):
        """Validate file upload requests."""
        
        # Only process requests with file uploads
        if not hasattr(request, 'FILES') or not request.FILES:
            return None
        
        # Check upload rate limiting
        if self._is_upload_rate_limited(request):
            logger.warning(f"Upload rate limit exceeded for {request.user}")
            response = HttpResponse("Upload rate limit exceeded", status=429)
            return response
        
        # Validate file uploads
        for field_name, uploaded_file in request.FILES.items():
            if not self._validate_upload_request(request, uploaded_file):
                logger.warning(f"Suspicious file upload attempt: {uploaded_file.name}")
                return HttpResponseBadRequest("Invalid file upload")
        
        return None
    
    def _is_upload_rate_limited(self, request):
        """Check upload-specific rate limiting."""
        if not request.user.is_authenticated:
            return True  # Require authentication for uploads
        
        cache_key = f"upload_rate_limit_{request.user.id}"
        upload_count = cache.get(cache_key, 0)
        
        if upload_count >= 10:  # 10 uploads per minute
            return True
        
        cache.set(cache_key, upload_count + 1, 60)
        return False
    
    def _validate_upload_request(self, request, uploaded_file):
        """Validate individual file upload."""
        
        # Check file size
        if uploaded_file.size > 50 * 1024 * 1024:  # 50MB max
            return False
        
        # Check filename for suspicious patterns
        if not uploaded_file.name or '..' in uploaded_file.name:
            return False
        
        # Additional checks can be added here
        return True
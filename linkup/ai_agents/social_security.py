"""
Security utilities for AI Agent Social Platform.

Provides input validation, sanitization, and security helpers.
"""
import re
import html
import logging
from typing import Optional, Any
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, EmailValidator

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Input validation utilities for social platform.
    
    Provides validation for common input types with security in mind.
    """
    
    # Regex patterns
    PATTERN_ALPHANUMERIC = re.compile(r'^[a-zA-Z0-9_-]+$')
    PATTERN_DISPLAY_NAME = re.compile(r'^[a-zA-Z0-9\s_-]+$')
    PATTERN_TAG = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    # Dangerous patterns to block
    PATTERN_SQL_INJECTION = re.compile(
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
        re.IGNORECASE
    )
    PATTERN_XSS = re.compile(
        r'(<script|javascript:|onerror=|onload=)',
        re.IGNORECASE
    )
    
    @staticmethod
    def validate_display_name(display_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate display name.
        
        Args:
            display_name: Display name to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not display_name:
            return False, "Display name is required"
        
        if len(display_name) < 3:
            return False, "Display name must be at least 3 characters"
        
        if len(display_name) > 100:
            return False, "Display name cannot exceed 100 characters"
        
        if not InputValidator.PATTERN_DISPLAY_NAME.match(display_name):
            return False, "Display name can only contain letters, numbers, spaces, hyphens, and underscores"
        
        # Check for dangerous patterns
        if InputValidator.PATTERN_XSS.search(display_name):
            return False, "Display name contains invalid characters"
        
        return True, None
    
    @staticmethod
    def validate_content(content: str, max_length: int = 5000) -> tuple[bool, Optional[str]]:
        """
        Validate content (posts, comments, etc.).
        
        Args:
            content: Content to validate
            max_length: Maximum allowed length
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content:
            return False, "Content is required"
        
        if len(content) > max_length:
            return False, f"Content cannot exceed {max_length} characters"
        
        # Check for SQL injection patterns
        if InputValidator.PATTERN_SQL_INJECTION.search(content):
            logger.warning(f"Potential SQL injection attempt detected in content")
            return False, "Content contains invalid patterns"
        
        return True, None
    
    @staticmethod
    def validate_tags(tags: list, max_count: int = 10, max_length: int = 30) -> tuple[bool, Optional[str]]:
        """
        Validate tags list.
        
        Args:
            tags: List of tags
            max_count: Maximum number of tags
            max_length: Maximum length per tag
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(tags, list):
            return False, "Tags must be a list"
        
        if len(tags) > max_count:
            return False, f"Maximum {max_count} tags allowed"
        
        for tag in tags:
            if not isinstance(tag, str):
                return False, "All tags must be strings"
            
            if len(tag) > max_length:
                return False, f"Each tag must be max {max_length} characters"
            
            if not InputValidator.PATTERN_TAG.match(tag):
                return False, "Tags can only contain letters, numbers, hyphens, and underscores"
        
        return True, None
    
    @staticmethod
    def validate_url(url: str) -> tuple[bool, Optional[str]]:
        """
        Validate URL.
        
        Args:
            url: URL to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return True, None  # Empty URL is valid (optional field)
        
        validator = URLValidator()
        try:
            validator(url)
            
            # Additional security checks
            if 'javascript:' in url.lower():
                return False, "Invalid URL protocol"
            
            return True, None
        except ValidationError:
            return False, "Invalid URL format"
    
    @staticmethod
    def validate_json_field(data: Any, field_name: str, expected_type: type) -> tuple[bool, Optional[str]]:
        """
        Validate JSON field type.
        
        Args:
            data: Data to validate
            field_name: Name of the field (for error messages)
            expected_type: Expected Python type (dict or list)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, expected_type):
            type_name = expected_type.__name__
            return False, f"{field_name} must be a {type_name}"
        
        return True, None


class ContentSanitizer:
    """
    Content sanitization utilities.
    
    Provides methods to sanitize user input to prevent XSS and other attacks.
    """
    
    @staticmethod
    def sanitize_html(content: str) -> str:
        """
        Sanitize HTML content by escaping special characters.
        
        Args:
            content: Content to sanitize
        
        Returns:
            Sanitized content
        """
        return html.escape(content)
    
    @staticmethod
    def sanitize_display_name(display_name: str) -> str:
        """
        Sanitize display name.
        
        Args:
            display_name: Display name to sanitize
        
        Returns:
            Sanitized display name
        """
        # Remove any HTML tags
        sanitized = re.sub(r'<[^>]+>', '', display_name)
        
        # Escape HTML entities
        sanitized = html.escape(sanitized)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        return sanitized
    
    @staticmethod
    def sanitize_tags(tags: list) -> list:
        """
        Sanitize tags list.
        
        Args:
            tags: List of tags
        
        Returns:
            Sanitized tags list
        """
        sanitized_tags = []
        for tag in tags:
            if isinstance(tag, str):
                # Remove special characters
                sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', tag)
                if sanitized:
                    sanitized_tags.append(sanitized.lower())
        
        return sanitized_tags
    
    @staticmethod
    def sanitize_metadata(metadata: dict) -> dict:
        """
        Sanitize metadata dictionary.
        
        Args:
            metadata: Metadata dict
        
        Returns:
            Sanitized metadata dict
        """
        sanitized = {}
        for key, value in metadata.items():
            # Sanitize key
            safe_key = re.sub(r'[^a-zA-Z0-9_-]', '', str(key))
            
            # Sanitize value based on type
            if isinstance(value, str):
                safe_value = html.escape(value)
            elif isinstance(value, (int, float, bool)):
                safe_value = value
            elif isinstance(value, (list, dict)):
                # Recursively sanitize nested structures
                if isinstance(value, list):
                    safe_value = [html.escape(str(v)) if isinstance(v, str) else v for v in value]
                else:
                    safe_value = ContentSanitizer.sanitize_metadata(value)
            else:
                safe_value = html.escape(str(value))
            
            sanitized[safe_key] = safe_value
        
        return sanitized


class SecurityHeaders:
    """
    Security headers for HTTP responses.
    """
    
    @staticmethod
    def get_security_headers() -> dict:
        """
        Get recommended security headers.
        
        Returns:
            Dict of security headers
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }


class RateLimitHelper:
    """
    Helper for rate limiting with exponential backoff.
    """
    
    @staticmethod
    def calculate_backoff(attempt: int, base_delay: int = 1, max_delay: int = 3600) -> int:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        
        Returns:
            Delay in seconds
        """
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
    
    @staticmethod
    def get_retry_after(remaining_tokens: float, refill_rate: float) -> int:
        """
        Calculate retry-after time for rate limiting.
        
        Args:
            remaining_tokens: Remaining tokens in bucket
            refill_rate: Token refill rate per second
        
        Returns:
            Seconds until retry
        """
        if remaining_tokens >= 1:
            return 0
        
        tokens_needed = 1 - remaining_tokens
        seconds = int(tokens_needed / refill_rate) + 1
        
        return seconds

"""
Authentication service for AI Agent Social Platform.

Provides JWT token generation, validation, and API key management
for agent authentication and authorization.
"""
import jwt
import time
import secrets
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password
from .models import AIAgent, AgentAPIKey
import logging

logger = logging.getLogger(__name__)


class SocialAuthService:
    """Authentication service for social platform."""
    
    # Token expiration times
    ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY = 604800  # 7 days
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure API key.
        
        Returns:
            32-character hexadecimal API key
        """
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key using bcrypt.
        
        Args:
            api_key: Plain text API key
        
        Returns:
            Hashed API key
        """
        return make_password(api_key)
    
    @staticmethod
    def verify_api_key(api_key: str, api_key_hash: str) -> bool:
        """
        Verify an API key against its hash.
        
        Args:
            api_key: Plain text API key
            api_key_hash: Hashed API key
        
        Returns:
            True if API key matches hash
        """
        return check_password(api_key, api_key_hash)
    
    @classmethod
    def generate_access_token(cls, agent_id: str, scopes: Optional[List[str]] = None) -> str:
        """
        Generate a JWT access token for an agent.
        
        Args:
            agent_id: UUID of the agent
            scopes: List of permission scopes
        
        Returns:
            JWT access token
        """
        now = int(time.time())
        payload = {
            'agent_id': str(agent_id),
            'scopes': scopes or ['read', 'write', 'communicate'],
            'type': 'access',
            'iat': now,
            'exp': now + cls.ACCESS_TOKEN_EXPIRY,
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        logger.info(f"Generated access token for agent {agent_id}")
        return token
    
    @classmethod
    def generate_refresh_token(cls, agent_id: str) -> str:
        """
        Generate a JWT refresh token for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            JWT refresh token
        """
        now = int(time.time())
        payload = {
            'agent_id': str(agent_id),
            'type': 'refresh',
            'iat': now,
            'exp': now + cls.REFRESH_TOKEN_EXPIRY,
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        logger.info(f"Generated refresh token for agent {agent_id}")
        return token
    
    @classmethod
    def validate_token(cls, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token to validate
        
        Returns:
            Dict with validation result and payload
        """
        try:
            # Check if token is revoked
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if cache.get(f'revoked_token:{token_hash}'):
                return {
                    'valid': False,
                    'error': 'Token has been revoked'
                }
            
            # Decode and validate token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Check expiration
            if payload.get('exp', 0) < time.time():
                return {
                    'valid': False,
                    'error': 'Token has expired'
                }
            
            return {
                'valid': True,
                'agent_id': payload.get('agent_id'),
                'scopes': payload.get('scopes', []),
                'type': payload.get('type'),
                'expires_at': payload.get('exp'),
            }
        
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Token has expired'
            }
        except jwt.InvalidTokenError as e:
            return {
                'valid': False,
                'error': f'Invalid token: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate a new access token using a refresh token.
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            Dict with new access token or None if invalid
        """
        validation = cls.validate_token(refresh_token)
        
        if not validation.get('valid'):
            return None
        
        if validation.get('type') != 'refresh':
            return None
        
        agent_id = validation.get('agent_id')
        
        # Generate new access token
        access_token = cls.generate_access_token(agent_id)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': cls.ACCESS_TOKEN_EXPIRY,
        }
    
    @staticmethod
    def revoke_token(token: str) -> bool:
        """
        Revoke a JWT token by adding it to the revocation list.
        
        Args:
            token: Token to revoke
        
        Returns:
            True if token was revoked
        """
        try:
            # Hash the token
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Add to revocation list in Redis with expiration
            cache.set(f'revoked_token:{token_hash}', True, timeout=86400)  # 24 hours
            
            logger.info(f"Revoked token: {token_hash[:16]}...")
            return True
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return False
    
    @staticmethod
    def authenticate_agent(agent_id: str, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate an agent using API key.
        
        Args:
            agent_id: UUID of the agent
            api_key: Plain text API key
        
        Returns:
            Dict with tokens if authentication successful, None otherwise
        """
        try:
            agent = AIAgent.objects.get(id=agent_id)
            
            # Check if agent is active
            if not agent.is_active:
                logger.warning(f"Authentication attempt for inactive agent: {agent_id}")
                return None
            
            # Check if agent is suspended
            if agent.is_suspended:
                logger.warning(f"Authentication attempt for suspended agent: {agent_id}")
                return None
            
            # Verify API key
            if not SocialAuthService.verify_api_key(api_key, agent.api_key_hash):
                logger.warning(f"Invalid API key for agent: {agent_id}")
                return None
            
            # Generate tokens
            access_token = SocialAuthService.generate_access_token(str(agent.id))
            refresh_token = SocialAuthService.generate_refresh_token(str(agent.id))
            
            # Update last active timestamp
            agent.last_active_at = datetime.now()
            agent.save(update_fields=['last_active_at'])
            
            logger.info(f"Agent authenticated successfully: {agent.name}")
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': SocialAuthService.ACCESS_TOKEN_EXPIRY,
                'agent_id': str(agent.id),
                'agent_name': agent.name,
            }
        
        except AIAgent.DoesNotExist:
            logger.warning(f"Authentication attempt for non-existent agent: {agent_id}")
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None


class RateLimiter:
    """Rate limiting service using token bucket algorithm."""
    
    @staticmethod
    def check_rate_limit(agent_id: str, limit: int = 1000, window: int = 60) -> Dict[str, Any]:
        """
        Check if agent has exceeded rate limit.
        
        Args:
            agent_id: UUID of the agent
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            Dict with allowed status and remaining requests
        """
        cache_key = f'rate_limit:{agent_id}'
        
        # Get current count
        current = cache.get(cache_key, 0)
        
        if current >= limit:
            # Calculate retry after
            ttl = cache.ttl(cache_key)
            retry_after = ttl if ttl > 0 else window
            
            return {
                'allowed': False,
                'limit': limit,
                'remaining': 0,
                'retry_after': retry_after,
            }
        
        # Increment counter
        if current == 0:
            cache.set(cache_key, 1, timeout=window)
        else:
            cache.incr(cache_key)
        
        return {
            'allowed': True,
            'limit': limit,
            'remaining': limit - current - 1,
            'reset_at': int(time.time()) + window,
        }
    
    @staticmethod
    def get_rate_limit_for_operation(operation_type: str) -> int:
        """
        Get rate limit for specific operation type.
        
        Args:
            operation_type: Type of operation (read, write, etc.)
        
        Returns:
            Rate limit per minute
        """
        limits = {
            'read': 2000,
            'write': 500,
            'communicate': 1000,
            'default': 1000,
        }
        return limits.get(operation_type, limits['default'])

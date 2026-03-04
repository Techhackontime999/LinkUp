"""
Authentication Service for AI Agent Social Platform.

Provides JWT token management, API key handling, and token revocation.
"""
import jwt
import time
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password
from .models import AIAgent, AgentAPIKey
import logging

logger = logging.getLogger(__name__)


class SocialAuthService:
    """
    Authentication service for AI agents on the social platform.
    
    Handles:
    - JWT token generation and validation
    - API key management
    - Token refresh
    - Token revocation
    """
    
    # Token expiration times
    ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY = 604800  # 7 days
    
    @classmethod
    def generate_api_key(cls) -> str:
        """
        Generate a secure API key.
        
        Returns:
            32-character hexadecimal API key
        """
        return secrets.token_hex(32)
    
    @classmethod
    def hash_api_key(cls, api_key: str) -> str:
        """
        Hash an API key using bcrypt.
        
        Args:
            api_key: Plain text API key
        
        Returns:
            Hashed API key
        """
        return make_password(api_key)
    
    @classmethod
    def verify_api_key(cls, api_key: str, api_key_hash: str) -> bool:
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
    def create_api_key(cls, agent: AIAgent, name: str, scopes: List[str], 
                      rate_limit: int = 1000, expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Create a new API key for an agent.
        
        Args:
            agent: AIAgent instance
            name: Descriptive name for the key
            scopes: List of allowed scopes
            rate_limit: Requests per minute limit
            expires_at: Optional expiration datetime
        
        Returns:
            Dict with api_key (plain text) and key info
        """
        # Generate API key
        api_key = cls.generate_api_key()
        key_hash = cls.hash_api_key(api_key)
        key_prefix = api_key[:8]
        
        # Create API key record
        api_key_obj = AgentAPIKey.objects.create(
            agent=agent,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=scopes,
            rate_limit=rate_limit,
            expires_at=expires_at
        )
        
        logger.info(f"Created API key {key_prefix}... for agent {agent.name}")
        
        return {
            'api_key': api_key,  # Only returned once!
            'key_id': str(api_key_obj.id),
            'key_prefix': key_prefix,
            'name': name,
            'scopes': scopes,
            'rate_limit': rate_limit,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'created_at': api_key_obj.created_at.isoformat()
        }
    
    @classmethod
    def generate_access_token(cls, agent_id: str, scopes: List[str]) -> str:
        """
        Generate a JWT access token.
        
        Args:
            agent_id: UUID of the agent
            scopes: List of allowed scopes
        
        Returns:
            JWT access token
        """
        now = int(time.time())
        payload = {
            'agent_id': agent_id,
            'scopes': scopes,
            'token_type': 'access',
            'issued_at': now,
            'expires_at': now + cls.ACCESS_TOKEN_EXPIRY
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        logger.debug(f"Generated access token for agent {agent_id}")
        return token
    
    @classmethod
    def generate_refresh_token(cls, agent_id: str) -> str:
        """
        Generate a JWT refresh token.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            JWT refresh token
        """
        now = int(time.time())
        payload = {
            'agent_id': agent_id,
            'token_type': 'refresh',
            'issued_at': now,
            'expires_at': now + cls.REFRESH_TOKEN_EXPIRY
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        logger.debug(f"Generated refresh token for agent {agent_id}")
        return token
    
    @classmethod
    def validate_token(cls, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token string
        
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
            
            # Decode token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Check expiration
            if time.time() > payload.get('expires_at', 0):
                return {
                    'valid': False,
                    'error': 'Token has expired'
                }
            
            return {
                'valid': True,
                'agent_id': payload.get('agent_id'),
                'scopes': payload.get('scopes', []),
                'token_type': payload.get('token_type'),
                'expires_at': payload.get('expires_at')
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
            logger.error(f"Token validation error: {e}", exc_info=True)
            return {
                'valid': False,
                'error': str(e)
            }
    
    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: JWT refresh token
        
        Returns:
            Dict with new access token or error
        """
        # Validate refresh token
        validation = cls.validate_token(refresh_token)
        
        if not validation['valid']:
            return {
                'success': False,
                'error': validation['error']
            }
        
        if validation['token_type'] != 'refresh':
            return {
                'success': False,
                'error': 'Invalid token type. Expected refresh token.'
            }
        
        # Get agent to retrieve scopes
        try:
            agent = AIAgent.objects.get(id=validation['agent_id'])
            
            # Get agent's API key scopes (use first active key)
            api_key = agent.api_keys.filter(is_active=True).first()
            scopes = api_key.scopes if api_key else ['read', 'write']
            
            # Generate new access token
            access_token = cls.generate_access_token(
                agent_id=str(agent.id),
                scopes=scopes
            )
            
            return {
                'success': True,
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': cls.ACCESS_TOKEN_EXPIRY
            }
            
        except AIAgent.DoesNotExist:
            return {
                'success': False,
                'error': 'Agent not found'
            }
    
    @classmethod
    def revoke_token(cls, token: str) -> bool:
        """
        Revoke a JWT token by adding it to the revocation list.
        
        Args:
            token: JWT token to revoke
        
        Returns:
            True if token was revoked successfully
        """
        try:
            # Validate token first to get expiration
            validation = cls.validate_token(token)
            
            if not validation['valid']:
                # Token is already invalid, no need to revoke
                return True
            
            # Calculate TTL (time until token expires)
            expires_at = validation['expires_at']
            ttl = max(0, expires_at - int(time.time()))
            
            # Add to revocation list in Redis
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            cache.set(f'revoked_token:{token_hash}', True, timeout=ttl)
            
            logger.info(f"Revoked token for agent {validation['agent_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Token revocation error: {e}", exc_info=True)
            return False
    
    @classmethod
    def authenticate_with_api_key(cls, api_key: str) -> Dict[str, Any]:
        """
        Authenticate an agent using an API key and generate tokens.
        
        Args:
            api_key: Plain text API key
        
        Returns:
            Dict with tokens and agent info or error
        """
        try:
            # Get key prefix for lookup
            key_prefix = api_key[:8]
            
            # Find API key by prefix
            api_key_obj = AgentAPIKey.objects.filter(
                key_prefix=key_prefix,
                is_active=True
            ).select_related('agent').first()
            
            if not api_key_obj:
                return {
                    'success': False,
                    'error': 'Invalid API key'
                }
            
            # Verify API key hash
            if not cls.verify_api_key(api_key, api_key_obj.key_hash):
                return {
                    'success': False,
                    'error': 'Invalid API key'
                }
            
            # Check if key is expired
            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now():
                return {
                    'success': False,
                    'error': 'API key has expired'
                }
            
            # Check if agent is active
            agent = api_key_obj.agent
            if not agent.is_active or agent.is_suspended:
                return {
                    'success': False,
                    'error': 'Agent is not active'
                }
            
            # Update API key usage
            api_key_obj.last_used_at = datetime.now()
            api_key_obj.usage_count = api_key_obj.usage_count + 1
            api_key_obj.save(update_fields=['last_used_at', 'usage_count'])
            
            # Generate tokens
            access_token = cls.generate_access_token(
                agent_id=str(agent.id),
                scopes=api_key_obj.scopes
            )
            refresh_token = cls.generate_refresh_token(agent_id=str(agent.id))
            
            return {
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': cls.ACCESS_TOKEN_EXPIRY,
                'agent_id': str(agent.id),
                'agent_name': agent.name,
                'scopes': api_key_obj.scopes
            }
            
        except Exception as e:
            logger.error(f"API key authentication error: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'Authentication failed'
            }
    
    @classmethod
    def has_scope(cls, token_data: Dict[str, Any], required_scope: str) -> bool:
        """
        Check if a token has a required scope.
        
        Args:
            token_data: Validated token data
            required_scope: Required scope string
        
        Returns:
            True if token has the required scope
        """
        scopes = token_data.get('scopes', [])
        return required_scope in scopes or '*' in scopes

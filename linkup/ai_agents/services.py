"""
AI Agents services for managing agent registration, profiles, and discovery.
"""
import uuid
import secrets
import base64
from typing import Dict, List, Optional, Any
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction, models
from django.utils import timezone
from .models import AIAgent, AgentAPIKey


class AgentRegistryService:
    """
    Service for managing AI agent registration, profiles, and discovery.
    
    This service handles:
    - Agent registration with validation
    - Agent profile management
    - Agent discovery and filtering
    """
    
    @staticmethod
    def register_agent(
        name: str,
        description: str,
        capabilities: Dict[str, Any],
        owner_email: str,
        agent_type: str = 'CONVERSATIONAL',
        version: str = '1.0.0',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new AI agent with unique identifier and API key.
        
        Args:
            name: Unique agent name (3-100 characters)
            description: Description of agent's purpose and capabilities
            capabilities: JSON object describing agent capabilities
            owner_email: Email address of the agent owner
            agent_type: Type of agent (CONVERSATIONAL, TASK_BASED, RESEARCH, CUSTOM)
            version: Agent version (default: '1.0.0')
            metadata: Additional metadata (optional)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - agent_id: UUID of created agent (on success)
                - api_key: Plain text API key (only returned once)
                - key_prefix: First 8 characters of API key for identification
                - message: Success or error message
                - error: Error details (on failure)
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Step 1: Check for duplicate name
            if AIAgent.objects.filter(name=name).exists():
                return {
                    'status': 'FAILED',
                    'error': 'Agent name already exists'
                }
            
            # Step 2: Validate owner email
            try:
                validate_email(owner_email)
            except ValidationError:
                return {
                    'status': 'FAILED',
                    'error': 'Invalid email address'
                }
            
            # Step 3: Validate name length
            if len(name) < 3 or len(name) > 100:
                return {
                    'status': 'FAILED',
                    'error': 'Agent name must be between 3 and 100 characters'
                }
            
            # Step 4: Validate agent_type
            valid_types = ['CONVERSATIONAL', 'TASK_BASED', 'RESEARCH', 'CUSTOM']
            if agent_type not in valid_types:
                return {
                    'status': 'FAILED',
                    'error': f'Invalid agent type. Must be one of: {", ".join(valid_types)}'
                }
            
            # Step 5: Validate capabilities is a dict
            if not isinstance(capabilities, dict):
                return {
                    'status': 'FAILED',
                    'error': 'Capabilities must be a valid JSON object'
                }
            
            # Step 6: Generate unique agent ID
            agent_id = uuid.uuid4()
            
            # Step 7: Generate API key
            api_key = AgentRegistryService._generate_secure_api_key(32)
            api_key_hash = AgentRegistryService._hash_api_key(api_key)
            key_prefix = api_key[:8]
            
            # Step 8: Create agent and API key records in a transaction
            with transaction.atomic():
                # Create agent record
                agent = AIAgent.objects.create(
                    id=agent_id,
                    name=name,
                    agent_type=agent_type,
                    description=description,
                    capabilities=capabilities,
                    version=version,
                    owner_email=owner_email,
                    api_key_hash=api_key_hash,
                    is_active=True,
                    is_suspended=False,
                    metadata=metadata or {},
                    total_interactions=0
                )
                
                # Create API key record
                api_key_record = AgentAPIKey.objects.create(
                    agent=agent,
                    key_hash=api_key_hash,
                    key_prefix=key_prefix,
                    name='Primary Key',
                    scopes=['read', 'write', 'communicate'],
                    rate_limit=1000,  # requests per minute
                    is_active=True
                )
            
            # Step 9: Return success with API key (only time it's visible)
            return {
                'status': 'SUCCESS',
                'agent_id': str(agent_id),
                'api_key': api_key,
                'key_prefix': key_prefix,
                'message': 'Agent registered successfully'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def update_agent_profile(
        agent_id: str,
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an agent's profile with field validation.
        
        Args:
            agent_id: UUID of the agent to update
            profile_data: Dictionary containing fields to update
                Allowed fields: description, capabilities, metadata, version, agent_type
                Immutable fields: id, name, created_at, api_key_hash, owner_email
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - message: Success or error message
                - updated_fields: List of fields that were updated (on success)
        """
        try:
            # Step 1: Validate agent ID
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Step 2: Define immutable fields
            immutable_fields = ['id', 'name', 'created_at', 'api_key_hash', 'owner_email']
            
            # Step 3: Check for attempts to update immutable fields
            for field in immutable_fields:
                if field in profile_data:
                    return {
                        'status': 'FAILED',
                        'error': f'Cannot update immutable field: {field}'
                    }
            
            # Step 4: Validate and update allowed fields
            updated_fields = []
            
            if 'description' in profile_data:
                agent.description = profile_data['description']
                updated_fields.append('description')
            
            if 'capabilities' in profile_data:
                if not isinstance(profile_data['capabilities'], dict):
                    return {
                        'status': 'FAILED',
                        'error': 'Capabilities must be a valid JSON object'
                    }
                agent.capabilities = profile_data['capabilities']
                updated_fields.append('capabilities')
            
            if 'metadata' in profile_data:
                if not isinstance(profile_data['metadata'], dict):
                    return {
                        'status': 'FAILED',
                        'error': 'Metadata must be a valid JSON object'
                    }
                agent.metadata = profile_data['metadata']
                updated_fields.append('metadata')
            
            if 'version' in profile_data:
                agent.version = profile_data['version']
                updated_fields.append('version')
            
            if 'agent_type' in profile_data:
                valid_types = ['CONVERSATIONAL', 'TASK_BASED', 'RESEARCH', 'CUSTOM']
                if profile_data['agent_type'] not in valid_types:
                    return {
                        'status': 'FAILED',
                        'error': f'Invalid agent type. Must be one of: {", ".join(valid_types)}'
                    }
                agent.agent_type = profile_data['agent_type']
                updated_fields.append('agent_type')
            
            # Step 5: Save the agent
            agent.save()
            
            return {
                'status': 'SUCCESS',
                'message': 'Agent profile updated successfully',
                'updated_fields': updated_fields
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def deactivate_agent(agent_id: str) -> Dict[str, Any]:
        """
        Deactivate an agent, preventing new authentication requests.
        
        Args:
            agent_id: UUID of the agent to deactivate
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - message: Success or error message
        """
        try:
            # Step 1: Validate agent ID
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Step 2: Mark agent as inactive
            agent.is_active = False
            agent.save()
            
            return {
                'status': 'SUCCESS',
                'message': 'Agent deactivated successfully'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def get_agent_profile(agent_id: str) -> Dict[str, Any]:
        """
        Retrieve an agent's profile information.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - agent: Agent profile data (on success)
                - error: Error message (on failure)
        """
        try:
            # Step 1: Retrieve agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Step 2: Return agent profile
            return {
                'status': 'SUCCESS',
                'agent': {
                    'id': str(agent.id),
                    'name': agent.name,
                    'agent_type': agent.agent_type,
                    'description': agent.description,
                    'capabilities': agent.capabilities,
                    'version': agent.version,
                    'owner_email': agent.owner_email,
                    'is_active': agent.is_active,
                    'is_suspended': agent.is_suspended,
                    'created_at': agent.created_at.isoformat(),
                    'last_active_at': agent.last_active_at.isoformat() if agent.last_active_at else None,
                    'total_interactions': agent.total_interactions,
                    'metadata': agent.metadata
                }
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def list_active_agents(
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        List active agents with optional filtering.
        
        Args:
            filters: Optional dictionary containing:
                - capabilities: Filter by specific capabilities (dict or list of keys)
                - agent_type: Filter by agent type
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - agents: List of agent profiles (on success)
                - count: Number of agents returned
                - error: Error message (on failure)
        """
        try:
            # Step 1: Start with active, non-suspended agents
            queryset = AIAgent.objects.filter(
                is_active=True,
                is_suspended=False
            )
            
            # Step 2: Apply filters if provided
            if filters:
                # Filter by agent_type
                if 'agent_type' in filters:
                    queryset = queryset.filter(agent_type=filters['agent_type'])
                
                # Filter by capabilities
                if 'capabilities' in filters:
                    capabilities_filter = filters['capabilities']
                    
                    # If capabilities_filter is a dict, check for matching key-value pairs
                    if isinstance(capabilities_filter, dict):
                        for key, value in capabilities_filter.items():
                            queryset = queryset.filter(
                                capabilities__contains={key: value}
                            )
                    # If it's a list, check for presence of keys
                    elif isinstance(capabilities_filter, list):
                        for key in capabilities_filter:
                            queryset = queryset.filter(
                                capabilities__has_key=key
                            )
            
            # Step 3: Build agent list
            agents = []
            for agent in queryset:
                agents.append({
                    'id': str(agent.id),
                    'name': agent.name,
                    'agent_type': agent.agent_type,
                    'description': agent.description,
                    'capabilities': agent.capabilities,
                    'version': agent.version,
                    'created_at': agent.created_at.isoformat(),
                    'last_active_at': agent.last_active_at.isoformat() if agent.last_active_at else None
                })
            
            return {
                'status': 'SUCCESS',
                'agents': agents,
                'count': len(agents)
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def _generate_secure_api_key(length: int = 32) -> str:
        """
        Generate a cryptographically secure API key.
        
        Args:
            length: Number of random bytes to generate (default: 32)
        
        Returns:
            Base64-encoded API key with 'agnt_' prefix
        """
        # Generate cryptographically secure random bytes
        random_bytes = secrets.token_bytes(length)
        
        # Encode to base64 for safe string representation
        api_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        
        # Add prefix for identification
        api_key = f"agnt_{api_key}"
        
        return api_key
    
    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """
        Hash an API key using Django's password hashing.
        
        Args:
            api_key: Plain text API key
        
        Returns:
            Hashed API key
        """
        from django.contrib.auth.hashers import make_password
        return make_password(api_key)



class AgentAuthenticationService:
    """
    Service for managing AI agent authentication, JWT tokens, and access control.
    
    This service handles:
    - API key generation and validation
    - JWT token issuance and refresh
    - Authentication validation and error handling
    - Token refresh mechanism
    """
    
    @staticmethod
    def generate_api_key(agent_id: str) -> Dict[str, Any]:
        """
        Generate a new API key for an existing agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - api_key: Plain text API key (only returned once)
                - key_prefix: First 8 characters for identification
                - key_id: UUID of the API key record
                - message: Success or error message
        """
        try:
            # Step 1: Validate agent exists
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Step 2: Generate cryptographically secure API key
            api_key = AgentAuthenticationService._generate_secure_api_key(32)
            api_key_hash = AgentAuthenticationService._hash_api_key(api_key)
            key_prefix = api_key[:8]
            
            # Step 3: Create API key record
            api_key_record = AgentAPIKey.objects.create(
                agent=agent,
                key_hash=api_key_hash,
                key_prefix=key_prefix,
                name=f'API Key {timezone.now().strftime("%Y-%m-%d %H:%M")}',
                scopes=['read', 'write', 'communicate'],
                rate_limit=1000,  # requests per minute
                is_active=True
            )
            
            return {
                'status': 'SUCCESS',
                'api_key': api_key,
                'key_prefix': key_prefix,
                'key_id': str(api_key_record.id),
                'message': 'API key generated successfully'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def validate_api_key(agent_id: str, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key for an agent.
        
        Args:
            agent_id: UUID of the agent
            api_key: Plain text API key to validate
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - valid: Boolean indicating if key is valid
                - api_key_record: API key record data (on success)
                - error: Error message (on failure)
        """
        try:
            # Step 1: Retrieve agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'valid': False,
                    'error': 'Agent not found'
                }
            
            # Step 2: Check agent status
            if not agent.is_active:
                return {
                    'status': 'FAILED',
                    'valid': False,
                    'error': 'Agent is inactive'
                }
            
            if agent.is_suspended:
                return {
                    'status': 'FAILED',
                    'valid': False,
                    'error': 'Agent is suspended'
                }
            
            # Step 3: Get active API keys for this agent
            api_keys = AgentAPIKey.objects.filter(
                agent=agent,
                is_active=True
            )
            
            # Step 4: Verify API key against stored hashes
            from django.contrib.auth.hashers import check_password
            
            for api_key_record in api_keys:
                if check_password(api_key, api_key_record.key_hash):
                    # Step 5: Check API key expiration
                    if api_key_record.expires_at:
                        if timezone.now() > api_key_record.expires_at:
                            return {
                                'status': 'FAILED',
                                'valid': False,
                                'error': 'API key expired'
                            }
                    
                    # API key is valid
                    return {
                        'status': 'SUCCESS',
                        'valid': True,
                        'api_key_record': {
                            'id': str(api_key_record.id),
                            'key_prefix': api_key_record.key_prefix,
                            'scopes': api_key_record.scopes,
                            'rate_limit': api_key_record.rate_limit
                        }
                    }
            
            # No matching API key found
            return {
                'status': 'FAILED',
                'valid': False,
                'error': 'Invalid API key'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'valid': False,
                'error': str(e)
            }
    
    @staticmethod
    def authenticate_agent(agent_id: str, api_key: str) -> Dict[str, Any]:
        """
        Authenticate an agent and issue JWT tokens.
        
        Args:
            agent_id: UUID of the agent
            api_key: Plain text API key
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - access_token: JWT access token (on success)
                - refresh_token: Refresh token (on success)
                - expires_in: Token expiration time in seconds
                - token_type: 'Bearer'
                - error: Error message (on failure)
        """
        try:
            # Step 1: Validate API key
            validation_result = AgentAuthenticationService.validate_api_key(agent_id, api_key)
            
            if not validation_result.get('valid', False):
                # Log failed authentication attempt
                AgentAuthenticationService._log_failed_authentication(
                    agent_id,
                    validation_result.get('error', 'Unknown error')
                )
                return {
                    'status': 'FAILED',
                    'error': validation_result.get('error', 'Authentication failed')
                }
            
            # Step 2: Get agent and API key record
            agent = AIAgent.objects.get(id=agent_id)
            api_key_record = AgentAPIKey.objects.get(
                id=validation_result['api_key_record']['id']
            )
            
            # Step 3: Generate JWT token
            jwt_token = AgentAuthenticationService._generate_jwt_token(
                agent=agent,
                scopes=api_key_record.scopes
            )
            
            # Step 4: Generate refresh token
            refresh_token = AgentAuthenticationService._generate_refresh_token(agent.id)
            
            # Step 5: Update API key usage
            api_key_record.last_used_at = timezone.now()
            api_key_record.usage_count += 1
            api_key_record.save()
            
            # Step 6: Update agent last active
            agent.last_active_at = timezone.now()
            agent.save()
            
            # Step 7: Log successful authentication
            AgentAuthenticationService._log_authentication_event(
                agent_id=str(agent.id),
                event_type='AGENT_AUTHENTICATED',
                success=True
            )
            
            return {
                'status': 'SUCCESS',
                'access_token': jwt_token,
                'refresh_token': refresh_token,
                'expires_in': 3600,  # 1 hour
                'token_type': 'Bearer'
            }
            
        except Exception as e:
            AgentAuthenticationService._log_failed_authentication(
                agent_id,
                str(e)
            )
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def refresh_token(refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: The refresh token
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - access_token: New JWT access token (on success)
                - refresh_token: New refresh token (on success)
                - expires_in: Token expiration time in seconds
                - token_type: 'Bearer'
                - error: Error message (on failure)
        """
        try:
            # Step 1: Validate and decode refresh token
            token_data = AgentAuthenticationService._validate_refresh_token(refresh_token)
            
            if not token_data.get('valid', False):
                return {
                    'status': 'FAILED',
                    'error': token_data.get('error', 'Invalid refresh token')
                }
            
            agent_id = token_data['agent_id']
            
            # Step 2: Get agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Step 3: Check agent status
            if not agent.is_active:
                return {
                    'status': 'FAILED',
                    'error': 'Agent is inactive'
                }
            
            if agent.is_suspended:
                return {
                    'status': 'FAILED',
                    'error': 'Agent is suspended'
                }
            
            # Step 4: Get agent's API key for scopes
            api_key_record = AgentAPIKey.objects.filter(
                agent=agent,
                is_active=True
            ).first()
            
            if not api_key_record:
                return {
                    'status': 'FAILED',
                    'error': 'No active API key found'
                }
            
            # Step 5: Generate new JWT token
            new_jwt_token = AgentAuthenticationService._generate_jwt_token(
                agent=agent,
                scopes=api_key_record.scopes
            )
            
            # Step 6: Generate new refresh token (invalidates old one)
            new_refresh_token = AgentAuthenticationService._generate_refresh_token(agent.id)
            
            # Step 7: Invalidate old refresh token
            AgentAuthenticationService._invalidate_refresh_token(refresh_token)
            
            # Step 8: Update agent last active
            agent.last_active_at = timezone.now()
            agent.save()
            
            return {
                'status': 'SUCCESS',
                'access_token': new_jwt_token,
                'refresh_token': new_refresh_token,
                'expires_in': 3600,  # 1 hour
                'token_type': 'Bearer'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def revoke_token(token: str) -> Dict[str, Any]:
        """
        Revoke an access or refresh token.
        
        Args:
            token: The token to revoke
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - message: Success or error message
        """
        try:
            # Invalidate the token
            AgentAuthenticationService._invalidate_refresh_token(token)
            
            return {
                'status': 'SUCCESS',
                'message': 'Token revoked successfully'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def check_permissions(agent_id: str, resource: str, action: str) -> Dict[str, Any]:
        """
        Check if an agent has permission to perform an action on a resource.
        
        Args:
            agent_id: UUID of the agent
            resource: Resource identifier
            action: Action to perform (e.g., 'read', 'write', 'delete')
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - allowed: Boolean indicating if action is allowed
                - error: Error message (on failure)
        """
        try:
            # Step 1: Get agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'allowed': False,
                    'error': 'Agent not found'
                }
            
            # Step 2: Check agent status
            if not agent.is_active or agent.is_suspended:
                return {
                    'status': 'SUCCESS',
                    'allowed': False,
                    'error': 'Agent is not active'
                }
            
            # Step 3: Get agent's API key scopes
            api_key_record = AgentAPIKey.objects.filter(
                agent=agent,
                is_active=True
            ).first()
            
            if not api_key_record:
                return {
                    'status': 'SUCCESS',
                    'allowed': False,
                    'error': 'No active API key found'
                }
            
            # Step 4: Check if action is in scopes
            scopes = api_key_record.scopes
            
            # Map actions to scopes
            action_scope_map = {
                'read': 'read',
                'write': 'write',
                'send_message': 'communicate',
                'receive_message': 'communicate'
            }
            
            required_scope = action_scope_map.get(action, action)
            
            if required_scope in scopes or '*' in scopes:
                return {
                    'status': 'SUCCESS',
                    'allowed': True
                }
            else:
                return {
                    'status': 'SUCCESS',
                    'allowed': False,
                    'error': f'Missing required scope: {required_scope}'
                }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'allowed': False,
                'error': str(e)
            }
    
    # Private helper methods
    
    @staticmethod
    def _generate_secure_api_key(length: int = 32) -> str:
        """
        Generate a cryptographically secure API key.
        
        Args:
            length: Number of random bytes to generate (default: 32)
        
        Returns:
            Base64-encoded API key with 'agnt_' prefix
        """
        # Generate cryptographically secure random bytes
        random_bytes = secrets.token_bytes(length)
        
        # Encode to base64 for safe string representation
        api_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        
        # Add prefix for identification
        api_key = f"agnt_{api_key}"
        
        return api_key
    
    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """
        Hash an API key using Django's password hashing.
        
        Args:
            api_key: Plain text API key
        
        Returns:
            Hashed API key
        """
        from django.contrib.auth.hashers import make_password
        return make_password(api_key)
    
    @staticmethod
    def _generate_jwt_token(agent: AIAgent, scopes: List[str]) -> str:
        """
        Generate a JWT token for an agent.
        
        Args:
            agent: AIAgent instance
            scopes: List of allowed scopes
        
        Returns:
            JWT token string
        """
        import jwt
        from django.conf import settings
        
        # Token payload
        payload = {
            'agent_id': str(agent.id),
            'agent_name': agent.name,
            'scopes': scopes,
            'issued_at': timezone.now().timestamp(),
            'expires_at': (timezone.now() + timezone.timedelta(hours=1)).timestamp()
        }
        
        # Generate JWT token
        secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        return token
    
    @staticmethod
    def _generate_refresh_token(agent_id: uuid.UUID) -> str:
        """
        Generate a refresh token for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Refresh token string
        """
        import jwt
        from django.conf import settings
        from django.core.cache import cache
        
        # Generate unique token ID
        token_id = str(uuid.uuid4())
        
        # Token payload
        payload = {
            'token_id': token_id,
            'agent_id': str(agent_id),
            'issued_at': timezone.now().timestamp(),
            'expires_at': (timezone.now() + timezone.timedelta(days=7)).timestamp()
        }
        
        # Generate refresh token
        secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # Store token in cache with 7-day expiration
        cache_key = f'refresh_token:{token_id}'
        cache.set(cache_key, str(agent_id), timeout=7*24*60*60)  # 7 days
        
        return token
    
    @staticmethod
    def _validate_refresh_token(refresh_token: str) -> Dict[str, Any]:
        """
        Validate a refresh token.
        
        Args:
            refresh_token: The refresh token to validate
        
        Returns:
            Dictionary containing validation result
        """
        try:
            import jwt
            from django.conf import settings
            from django.core.cache import cache
            
            # Decode token
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
            payload = jwt.decode(refresh_token, secret_key, algorithms=['HS256'])
            
            # Check expiration
            expires_at = payload.get('expires_at')
            if expires_at and timezone.now().timestamp() > expires_at:
                return {
                    'valid': False,
                    'error': 'Refresh token expired'
                }
            
            # Check if token is in cache (not invalidated)
            token_id = payload.get('token_id')
            cache_key = f'refresh_token:{token_id}'
            cached_agent_id = cache.get(cache_key)
            
            if not cached_agent_id:
                return {
                    'valid': False,
                    'error': 'Refresh token has been invalidated or expired'
                }
            
            return {
                'valid': True,
                'agent_id': payload.get('agent_id'),
                'token_id': token_id
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Refresh token expired'
            }
        except jwt.InvalidTokenError:
            return {
                'valid': False,
                'error': 'Invalid refresh token'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    @staticmethod
    def _invalidate_refresh_token(refresh_token: str) -> None:
        """
        Invalidate a refresh token by removing it from cache.
        
        Args:
            refresh_token: The refresh token to invalidate
        """
        try:
            import jwt
            from django.conf import settings
            from django.core.cache import cache
            
            # Decode token to get token_id
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
            payload = jwt.decode(refresh_token, secret_key, algorithms=['HS256'])
            
            token_id = payload.get('token_id')
            if token_id:
                cache_key = f'refresh_token:{token_id}'
                cache.delete(cache_key)
                
        except Exception:
            # Silently fail if token can't be decoded
            pass
    
    @staticmethod
    def _log_failed_authentication(agent_id: str, reason: str) -> None:
        """
        Log a failed authentication attempt.
        
        Args:
            agent_id: UUID of the agent
            reason: Reason for authentication failure
        """
        from .error_logger import ErrorLogger
        ErrorLogger.log_authentication_failure(
            agent_id=agent_id,
            reason=reason
        )
    
    @staticmethod
    def _log_authentication_event(agent_id: str, event_type: str, success: bool) -> None:
        """
        Log an authentication event.
        
        Args:
            agent_id: UUID of the agent
            event_type: Type of event
            success: Whether the event was successful
        """
        import logging
        logger = logging.getLogger('ai_agents.authentication')
        
        if success:
            logger.info(
                f'Authentication event - Type: {event_type}, Agent ID: {agent_id}'
            )
        else:
            logger.warning(
                f'Authentication event failed - Type: {event_type}, Agent ID: {agent_id}'
            )



class AgentRateLimitService:
    """
    Service for managing rate limiting for AI agents.
    
    This service handles:
    - Sliding window rate limit tracking
    - Request count management with Redis/Django cache
    - Rate limit checking and enforcement
    - Rate limit violation logging
    """
    
    @staticmethod
    def check_rate_limit(agent_id: str) -> Dict[str, Any]:
        """
        Check if an agent has exceeded their rate limit.
        
        Uses a sliding window approach to track requests per minute.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - allowed: Boolean indicating if request is allowed
                - current_count: Current number of requests in window
                - limit: Maximum allowed requests per minute
                - reset_at: Timestamp when the rate limit window resets
                - error: Error message (on failure)
        """
        try:
            from django.core.cache import cache
            
            # Step 1: Get agent and their rate limit
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'allowed': False,
                    'error': 'Agent not found'
                }
            
            # Step 2: Check agent status
            if not agent.is_active:
                return {
                    'status': 'FAILED',
                    'allowed': False,
                    'error': 'Agent is inactive'
                }
            
            if agent.is_suspended:
                return {
                    'status': 'FAILED',
                    'allowed': False,
                    'error': 'Agent is suspended'
                }
            
            # Step 3: Get agent's rate limit from API key
            api_key_record = AgentAPIKey.objects.filter(
                agent=agent,
                is_active=True
            ).first()
            
            if not api_key_record:
                return {
                    'status': 'FAILED',
                    'allowed': False,
                    'error': 'No active API key found'
                }
            
            rate_limit = api_key_record.rate_limit  # requests per minute
            
            # Step 4: Get current minute window
            current_window = AgentRateLimitService._get_current_minute_window()
            
            # Step 5: Check current request count
            cache_key = f"agent_rate_limit:{agent_id}:{current_window}"
            current_count = cache.get(cache_key, 0)
            
            # Step 6: Determine if rate limit is exceeded
            if current_count >= rate_limit:
                # Log rate limit violation
                AgentRateLimitService._log_rate_limit_violation(
                    agent_id=agent_id,
                    current_count=current_count,
                    limit=rate_limit
                )
                
                return {
                    'status': 'SUCCESS',
                    'allowed': False,
                    'current_count': current_count,
                    'limit': rate_limit,
                    'reset_at': AgentRateLimitService._get_window_reset_time(current_window),
                    'error': 'Rate limit exceeded'
                }
            
            # Rate limit not exceeded
            return {
                'status': 'SUCCESS',
                'allowed': True,
                'current_count': current_count,
                'limit': rate_limit,
                'reset_at': AgentRateLimitService._get_window_reset_time(current_window)
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'allowed': False,
                'error': str(e)
            }
    
    @staticmethod
    def increment_rate_limit(agent_id: str) -> Dict[str, Any]:
        """
        Increment the rate limit counter for an agent.
        
        Should be called after a request is processed successfully.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - current_count: Updated request count
                - limit: Maximum allowed requests per minute
                - error: Error message (on failure)
        """
        try:
            from django.core.cache import cache
            
            # Step 1: Get agent's rate limit
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            api_key_record = AgentAPIKey.objects.filter(
                agent=agent,
                is_active=True
            ).first()
            
            if not api_key_record:
                return {
                    'status': 'FAILED',
                    'error': 'No active API key found'
                }
            
            rate_limit = api_key_record.rate_limit
            
            # Step 2: Get current minute window
            current_window = AgentRateLimitService._get_current_minute_window()
            
            # Step 3: Increment counter in cache with 60-second TTL
            cache_key = f"agent_rate_limit:{agent_id}:{current_window}"
            
            # Get current count
            current_count = cache.get(cache_key, 0)
            
            # Increment
            new_count = current_count + 1
            
            # Set with 60-second TTL
            cache.set(cache_key, new_count, timeout=60)
            
            return {
                'status': 'SUCCESS',
                'current_count': new_count,
                'limit': rate_limit
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def reset_rate_limit(agent_id: str) -> Dict[str, Any]:
        """
        Reset the rate limit counter for an agent.
        
        Useful for testing or administrative purposes.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - message: Success or error message
        """
        try:
            from django.core.cache import cache
            
            # Get current minute window
            current_window = AgentRateLimitService._get_current_minute_window()
            
            # Delete cache key
            cache_key = f"agent_rate_limit:{agent_id}:{current_window}"
            cache.delete(cache_key)
            
            return {
                'status': 'SUCCESS',
                'message': 'Rate limit reset successfully'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def get_rate_limit_status(agent_id: str) -> Dict[str, Any]:
        """
        Get the current rate limit status for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - current_count: Current number of requests in window
                - limit: Maximum allowed requests per minute
                - remaining: Number of requests remaining
                - reset_at: Timestamp when the rate limit window resets
                - error: Error message (on failure)
        """
        try:
            from django.core.cache import cache
            
            # Step 1: Get agent's rate limit
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            api_key_record = AgentAPIKey.objects.filter(
                agent=agent,
                is_active=True
            ).first()
            
            if not api_key_record:
                return {
                    'status': 'FAILED',
                    'error': 'No active API key found'
                }
            
            rate_limit = api_key_record.rate_limit
            
            # Step 2: Get current minute window
            current_window = AgentRateLimitService._get_current_minute_window()
            
            # Step 3: Get current request count
            cache_key = f"agent_rate_limit:{agent_id}:{current_window}"
            current_count = cache.get(cache_key, 0)
            
            # Step 4: Calculate remaining requests
            remaining = max(0, rate_limit - current_count)
            
            return {
                'status': 'SUCCESS',
                'current_count': current_count,
                'limit': rate_limit,
                'remaining': remaining,
                'reset_at': AgentRateLimitService._get_window_reset_time(current_window)
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    # Private helper methods
    
    @staticmethod
    def _get_current_minute_window() -> str:
        """
        Get the current minute window identifier.
        
        Returns:
            String representing the current minute (e.g., '2024-01-15-14:30')
        """
        now = timezone.now()
        # Format: YYYY-MM-DD-HH:MM
        return now.strftime('%Y-%m-%d-%H:%M')
    
    @staticmethod
    def _get_window_reset_time(window: str) -> str:
        """
        Calculate when the rate limit window will reset.
        
        Args:
            window: Window identifier (e.g., '2024-01-15-14:30')
        
        Returns:
            ISO format timestamp of when the window resets
        """
        from datetime import datetime, timedelta
        
        # Parse window string
        window_time = datetime.strptime(window, '%Y-%m-%d-%H:%M')
        
        # Add 1 minute to get reset time
        reset_time = window_time + timedelta(minutes=1)
        
        return reset_time.isoformat()
    
    @staticmethod
    def _log_rate_limit_violation(agent_id: str, current_count: int, limit: int) -> None:
        """
        Log a rate limit violation.
        
        Args:
            agent_id: UUID of the agent
            current_count: Current request count
            limit: Rate limit threshold
        """
        from .error_logger import ErrorLogger
        ErrorLogger.log_rate_limit_violation(
            agent_id=agent_id,
            current_count=current_count,
            limit=limit
        )



class AgentCommunicationService:
    """
    Service for facilitating message exchange between AI agents.
    
    This service handles:
    - Message sending with sender/recipient validation
    - Message routing (WebSocket for online, queue for offline)
    - Message retrieval with filtering
    - Conversation threading support
    - Message status tracking
    """
    
    @staticmethod
    def send_message(
        sender_id: str,
        recipient_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        message_type: str = 'TEXT',
        priority: int = 3,
        parent_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message from one agent to another.
        
        Validates sender and recipient, creates message record, and routes
        the message via WebSocket (if online) or queues it (if offline).
        
        Args:
            sender_id: UUID of the sending agent
            recipient_id: UUID of the receiving agent
            content: Message content (max 100KB)
            metadata: Optional message metadata
            message_type: Type of message (TEXT, JSON, STRUCTURED)
            priority: Message priority (1=highest, 5=lowest)
            parent_message_id: Optional parent message ID for threading
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - message_id: UUID of created message (on success)
                - delivery_status: Message delivery status
                - timestamp: Message creation timestamp
                - error: Error message (on failure)
        
        Requirements: 4.1, 4.4, 4.5, 4.6, 14.1, 17.1
        """
        try:
            # Step 1: Validate message data
            validation_result = AgentCommunicationService._validate_message_data(
                sender_id=sender_id,
                recipient_id=recipient_id,
                content=content
            )
            
            if not validation_result['valid']:
                return {
                    'status': 'FAILED',
                    'error': validation_result['error']
                }
            
            # Step 2: Authenticate sender
            try:
                sender_agent = AIAgent.objects.get(id=sender_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Invalid or inactive sender'
                }
            
            if not sender_agent.is_active or sender_agent.is_suspended:
                return {
                    'status': 'FAILED',
                    'error': 'Sender agent is not active'
                }
            
            # Step 3: Validate recipient
            try:
                recipient_agent = AIAgent.objects.get(id=recipient_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Invalid or inactive recipient'
                }
            
            if not recipient_agent.is_active or recipient_agent.is_suspended:
                return {
                    'status': 'FAILED',
                    'error': 'Recipient agent is not active'
                }
            
            # Step 4: Check rate limits
            rate_limit_result = AgentRateLimitService.check_rate_limit(sender_id)
            if not rate_limit_result.get('allowed', False):
                return {
                    'status': 'FAILED',
                    'error': 'Rate limit exceeded'
                }
            
            # Step 5: Validate parent message if provided
            parent_message = None
            if parent_message_id:
                try:
                    parent_message = AgentMessage.objects.get(id=parent_message_id)
                except AgentMessage.DoesNotExist:
                    return {
                        'status': 'FAILED',
                        'error': 'Parent message not found'
                    }
            
            # Step 6: Calculate message size
            size_bytes = len(content.encode('utf-8'))
            
            # Step 7: Create message record
            from .models import AgentMessage
            
            message = AgentMessage.objects.create(
                sender=sender_agent,
                recipient=recipient_agent,
                content=content,
                message_type=message_type,
                metadata=metadata or {},
                status='PENDING',
                priority=priority,
                parent_message=parent_message,
                size_bytes=size_bytes
            )
            
            # Step 8: Log interaction
            from .services import InteractionLogger
            InteractionLogger.log_interaction(
                agent_1=sender_agent,
                agent_2=recipient_agent,
                message=message,
                timestamp=timezone.now()
            )
            
            # Step 9: Route message
            routing_result = AgentCommunicationService._route_message(
                message=message,
                recipient_agent=recipient_agent
            )
            
            # Step 10: Update metrics
            AgentCommunicationService._update_agent_metrics(
                sender_agent=sender_agent,
                recipient_agent=recipient_agent,
                message=message
            )
            
            # Step 11: Increment rate limit counter
            AgentRateLimitService.increment_rate_limit(sender_id)
            
            return {
                'status': 'SUCCESS',
                'message_id': str(message.id),
                'delivery_status': message.status,
                'timestamp': message.created_at.isoformat()
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.communication')
            logger.error(f'Error sending message: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def receive_messages(
        agent_id: str,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve messages for an agent with optional filtering.
        
        Args:
            agent_id: UUID of the agent
            filters: Optional filters:
                - sender_id: Filter by sender
                - date_from: Filter by start date
                - date_to: Filter by end date
                - status: Filter by message status
            pagination: Optional pagination:
                - page: Page number (default: 1)
                - page_size: Items per page (default: 50)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - messages: List of message objects
                - count: Total number of messages
                - page: Current page number
                - total_pages: Total number of pages
                - error: Error message (on failure)
        
        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
        """
        try:
            # Step 1: Validate agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Step 2: Start with messages where agent is recipient
            from .models import AgentMessage
            queryset = AgentMessage.objects.filter(recipient=agent)
            
            # Step 3: Apply filters if provided
            if filters:
                # Filter by sender
                if 'sender_id' in filters:
                    queryset = queryset.filter(sender_id=filters['sender_id'])
                
                # Filter by date range
                if 'date_from' in filters:
                    queryset = queryset.filter(created_at__gte=filters['date_from'])
                
                if 'date_to' in filters:
                    queryset = queryset.filter(created_at__lte=filters['date_to'])
                
                # Filter by status
                if 'status' in filters:
                    queryset = queryset.filter(status=filters['status'])
            
            # Step 4: Order by creation time (newest first)
            queryset = queryset.order_by('-created_at')
            
            # Step 5: Apply pagination
            page = 1
            page_size = 50
            
            if pagination:
                page = pagination.get('page', 1)
                page_size = pagination.get('page_size', 50)
            
            # Calculate pagination
            total_count = queryset.count()
            total_pages = (total_count + page_size - 1) // page_size
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            messages_page = queryset[start_index:end_index]
            
            # Step 6: Build message list
            messages = []
            for message in messages_page:
                messages.append({
                    'id': str(message.id),
                    'sender_id': str(message.sender.id),
                    'sender_name': message.sender.name,
                    'recipient_id': str(message.recipient.id),
                    'content': message.content,
                    'message_type': message.message_type,
                    'metadata': message.metadata,
                    'status': message.status,
                    'priority': message.priority,
                    'parent_message_id': str(message.parent_message.id) if message.parent_message else None,
                    'created_at': message.created_at.isoformat(),
                    'sent_at': message.sent_at.isoformat() if message.sent_at else None,
                    'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
                    'read_at': message.read_at.isoformat() if message.read_at else None,
                    'latency_ms': message.latency_ms,
                    'size_bytes': message.size_bytes
                })
            
            return {
                'status': 'SUCCESS',
                'messages': messages,
                'count': total_count,
                'page': page,
                'total_pages': total_pages
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def broadcast_message(
        sender_id: str,
        recipient_ids: List[str],
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Broadcast a message to multiple recipients.
        
        Args:
            sender_id: UUID of the sending agent
            recipient_ids: List of recipient agent UUIDs
            content: Message content
            metadata: Optional message metadata
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - results: List of send results for each recipient
                - successful: Number of successful sends
                - failed: Number of failed sends
        """
        try:
            results = []
            successful = 0
            failed = 0
            
            for recipient_id in recipient_ids:
                result = AgentCommunicationService.send_message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    content=content,
                    metadata=metadata
                )
                
                results.append({
                    'recipient_id': recipient_id,
                    'result': result
                })
                
                if result['status'] == 'SUCCESS':
                    successful += 1
                else:
                    failed += 1
            
            return {
                'status': 'SUCCESS',
                'results': results,
                'successful': successful,
                'failed': failed
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def get_conversation_history(
        agent_id_1: str,
        agent_id_2: str,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get conversation history between two agents.
        
        Args:
            agent_id_1: UUID of first agent
            agent_id_2: UUID of second agent
            pagination: Optional pagination parameters
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - messages: List of messages in conversation
                - count: Total number of messages
                - error: Error message (on failure)
        
        Requirements: 10.6
        """
        try:
            from .models import AgentMessage
            from django.db.models import Q
            
            # Step 1: Validate both agents exist
            try:
                agent_1 = AIAgent.objects.get(id=agent_id_1)
                agent_2 = AIAgent.objects.get(id=agent_id_2)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'One or both agents not found'
                }
            
            # Step 2: Query messages between the two agents (both directions)
            queryset = AgentMessage.objects.filter(
                Q(sender=agent_1, recipient=agent_2) |
                Q(sender=agent_2, recipient=agent_1)
            ).order_by('created_at')
            
            # Step 3: Apply pagination
            page = 1
            page_size = 50
            
            if pagination:
                page = pagination.get('page', 1)
                page_size = pagination.get('page_size', 50)
            
            total_count = queryset.count()
            total_pages = (total_count + page_size - 1) // page_size
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            messages_page = queryset[start_index:end_index]
            
            # Step 4: Build message list
            messages = []
            for message in messages_page:
                messages.append({
                    'id': str(message.id),
                    'sender_id': str(message.sender.id),
                    'sender_name': message.sender.name,
                    'recipient_id': str(message.recipient.id),
                    'recipient_name': message.recipient.name,
                    'content': message.content,
                    'message_type': message.message_type,
                    'metadata': message.metadata,
                    'status': message.status,
                    'priority': message.priority,
                    'parent_message_id': str(message.parent_message.id) if message.parent_message else None,
                    'created_at': message.created_at.isoformat(),
                    'sent_at': message.sent_at.isoformat() if message.sent_at else None,
                    'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
                    'read_at': message.read_at.isoformat() if message.read_at else None
                })
            
            return {
                'status': 'SUCCESS',
                'messages': messages,
                'count': total_count,
                'page': page,
                'total_pages': total_pages
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def mark_message_as_read(message_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Mark a message as read by the recipient.
        
        Args:
            message_id: UUID of the message
            agent_id: UUID of the agent marking as read (must be recipient)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - message: Success or error message
        
        Requirements: 14.4
        """
        try:
            from .models import AgentMessage
            
            # Step 1: Get message
            try:
                message = AgentMessage.objects.get(id=message_id)
            except AgentMessage.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Message not found'
                }
            
            # Step 2: Verify agent is the recipient
            if str(message.recipient.id) != agent_id:
                return {
                    'status': 'FAILED',
                    'error': 'Only the recipient can mark a message as read'
                }
            
            # Step 3: Update message status
            message.status = 'READ'
            message.read_at = timezone.now()
            message.save()
            
            return {
                'status': 'SUCCESS',
                'message': 'Message marked as read'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def get_conversation_thread(
        message_id: str,
        include_children: bool = True
    ) -> Dict[str, Any]:
        """
        Get all messages in a conversation thread.
        
        Args:
            message_id: UUID of a message in the thread
            include_children: Whether to include child messages (replies)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - thread: List of messages in thread
                - thread_depth: Maximum depth of the thread
                - error: Error message (on failure)
        
        Requirements: 17.2, 17.3
        """
        try:
            from .models import AgentMessage
            
            # Step 1: Get the message
            try:
                message = AgentMessage.objects.get(id=message_id)
            except AgentMessage.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Message not found'
                }
            
            # Step 2: Find the root message of the thread
            root_message = message
            while root_message.parent_message:
                root_message = root_message.parent_message
            
            # Step 3: Collect all messages in the thread
            thread_messages = []
            max_depth = 0
            
            def collect_thread_messages(msg, depth=0):
                nonlocal max_depth
                max_depth = max(max_depth, depth)
                
                thread_messages.append({
                    'id': str(msg.id),
                    'sender_id': str(msg.sender.id),
                    'sender_name': msg.sender.name,
                    'recipient_id': str(msg.recipient.id),
                    'recipient_name': msg.recipient.name,
                    'content': msg.content,
                    'message_type': msg.message_type,
                    'metadata': msg.metadata,
                    'status': msg.status,
                    'priority': msg.priority,
                    'parent_message_id': str(msg.parent_message.id) if msg.parent_message else None,
                    'created_at': msg.created_at.isoformat(),
                    'depth': depth
                })
                
                # Recursively collect child messages
                if include_children:
                    child_messages = AgentMessage.objects.filter(parent_message=msg).order_by('created_at')
                    for child in child_messages:
                        collect_thread_messages(child, depth + 1)
            
            # Start collecting from root
            collect_thread_messages(root_message)
            
            return {
                'status': 'SUCCESS',
                'thread': thread_messages,
                'thread_depth': max_depth,
                'message_count': len(thread_messages)
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    # Private helper methods
    
    @staticmethod
    def _validate_message_data(
        sender_id: str,
        recipient_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Validate message data before sending.
        
        Args:
            sender_id: UUID of sender
            recipient_id: UUID of recipient
            content: Message content
        
        Returns:
            Dictionary with 'valid' boolean and optional 'error' message
        
        Requirements: 4.4
        """
        # Check if sender and recipient are provided
        if not sender_id or not recipient_id:
            return {
                'valid': False,
                'error': 'Sender and recipient IDs are required'
            }
        
        # Check if sender and recipient are different
        if sender_id == recipient_id:
            return {
                'valid': False,
                'error': 'Sender and recipient must be different agents'
            }
        
        # Check if content is provided
        if not content:
            return {
                'valid': False,
                'error': 'Message content is required'
            }
        
        # Check content size (100KB = 102400 bytes)
        content_size = len(content.encode('utf-8'))
        if content_size > 102400:
            return {
                'valid': False,
                'error': 'Message content cannot exceed 100KB'
            }
        
        return {'valid': True}
    
    @staticmethod
    def _route_message(
        message,
        recipient_agent: AIAgent
    ) -> Dict[str, Any]:
        """
        Route a message to the recipient (WebSocket or queue).
        
        Args:
            message: AgentMessage instance
            recipient_agent: Recipient AIAgent instance
        
        Returns:
            Dictionary with routing result
        
        Requirements: 4.2, 4.3, 4.7, 4.8, 4.9, 4.10, 14.2, 14.3, 14.5
        """
        try:
            # Check if recipient is online (has active WebSocket connection)
            is_online = AgentCommunicationService._is_agent_online(recipient_agent)
            
            start_time = timezone.now()
            
            if is_online:
                # Deliver via WebSocket
                delivery_result = AgentCommunicationService._send_via_websocket(
                    recipient_agent=recipient_agent,
                    message=message
                )
                
                if delivery_result['success']:
                    message.status = 'DELIVERED'
                    message.sent_at = start_time
                    message.delivered_at = timezone.now()
                    
                    # Calculate latency
                    latency = (message.delivered_at - message.created_at).total_seconds() * 1000
                    message.latency_ms = int(latency)
                else:
                    message.status = 'FAILED'
                    
                    # Log delivery failure
                    from .error_logger import ErrorLogger
                    ErrorLogger.log_message_delivery_failure(
                        message_id=str(message.id),
                        sender_id=str(message.sender.id),
                        recipient_id=str(recipient_agent.id),
                        error_details=delivery_result.get('error', 'Unknown error')
                    )
            else:
                # Queue for offline delivery
                message.status = 'SENT'
                message.sent_at = start_time
                
                # Add message to offline queue
                from .offline_queue_manager import OfflineQueueManager
                queue_success = OfflineQueueManager.queue_message(message)
                
                if not queue_success:
                    from .error_logger import ErrorLogger
                    ErrorLogger.log_system_error(
                        error_type='queue_failure',
                        error_message=f'Failed to queue message for offline agent',
                        component='AgentCommunicationService',
                        additional_context={
                            'message_id': str(message.id),
                            'agent_id': str(recipient_agent.id)
                        }
                    )
            
            message.save()
            
            return {
                'success': True,
                'status': message.status
            }
            
        except Exception as e:
            message.status = 'FAILED'
            message.save()
            
            from .error_logger import ErrorLogger
            ErrorLogger.log_system_error(
                error_type='message_routing_error',
                error_message=str(e),
                component='AgentCommunicationService',
                additional_context={
                    'message_id': str(message.id),
                    'recipient_id': str(recipient_agent.id)
                }
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _is_agent_online(agent: AIAgent) -> bool:
        """
        Check if an agent has an active WebSocket connection.
        
        Args:
            agent: AIAgent instance
        
        Returns:
            Boolean indicating if agent is online
        """
        from django.core.cache import cache
        
        # Check if agent has an active WebSocket connection
        # WebSocket connections are tracked in cache with key pattern: agent_online:{agent_id}
        cache_key = f'agent_online:{agent.id}'
        return cache.get(cache_key, False)
    
    @staticmethod
    def _send_via_websocket(
        recipient_agent: AIAgent,
        message
    ) -> Dict[str, Any]:
        """
        Send a message via WebSocket to an online recipient.
        
        Args:
            recipient_agent: Recipient AIAgent instance
            message: AgentMessage instance
        
        Returns:
            Dictionary with success status and optional error
        
        Requirements: 4.2, 13.3, 14.3
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            
            if not channel_layer:
                return {
                    'success': False,
                    'error': 'Channel layer not configured'
                }
            
            # Get recipient's WebSocket channel
            channel_name = f'agent_{recipient_agent.id}'
            
            # Prepare message payload
            payload = {
                'type': 'agent_message',
                'message_id': str(message.id),
                'sender_id': str(message.sender.id),
                'sender_name': message.sender.name,
                'content': message.content,
                'metadata': message.metadata,
                'message_type': message.message_type,
                'priority': message.priority,
                'parent_message_id': str(message.parent_message.id) if message.parent_message else None,
                'timestamp': message.created_at.isoformat()
            }
            
            # Send via channel layer
            async_to_sync(channel_layer.group_send)(
                channel_name,
                payload
            )
            
            return {
                'success': True,
                'delivered_at': timezone.now()
            }
            
        except Exception as e:
            from .error_logger import ErrorLogger
            ErrorLogger.log_websocket_connection_failure(
                agent_id=str(recipient_agent.id),
                error_details=str(e),
                additional_context={
                    'message_id': str(message.id)
                }
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _update_agent_metrics(
        sender_agent: AIAgent,
        recipient_agent: AIAgent,
        message
    ) -> None:
        """
        Update metrics for both agents after message is sent.
        
        Args:
            sender_agent: Sending AIAgent instance
            recipient_agent: Receiving AIAgent instance
            message: AgentMessage instance
        """
        try:
            # Update sender's total interactions
            sender_agent.total_interactions += 1
            sender_agent.save()
            
            # Update recipient's total interactions
            recipient_agent.total_interactions += 1
            recipient_agent.save()
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.communication')
            logger.warning(f'Failed to update agent metrics: {str(e)}')



class InteractionLogger:
    """
    Service for logging AI-to-AI interactions for research analysis.

    This service handles:
    - Logging all agent communications with timestamps
    - Recording agent actions and behaviors
    - Storing interaction metadata
    - Supporting data export for external analysis
    - Data anonymization for privacy

    Requirements: 6.1-6.7, 11.1-11.6, 12.1-12.5
    """

    @staticmethod
    def log_interaction(
        agent_1: AIAgent,
        agent_2: AIAgent,
        message,
        timestamp: timezone.datetime,
        interaction_type: str = 'CONVERSATION',
        tags: Optional[List[str]] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log an interaction between two agents.

        Args:
            agent_1: First AIAgent instance (typically sender)
            agent_2: Second AIAgent instance (typically recipient)
            message: AgentMessage instance
            timestamp: Timestamp of the interaction
            interaction_type: Type of interaction (CONVERSATION, COLLABORATION, etc.)
            tags: Optional list of tags for categorization
            custom_metrics: Optional custom metrics in JSON format

        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - interaction_id: UUID of logged interaction
                - session_id: Session ID for grouping related exchanges
                - error: Error message (on failure)

        Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7
        """
        try:
            from .models import AgentInteraction

            # Try to find an existing active interaction session between these agents
            # An interaction is considered active if it ended less than 5 minutes ago or hasn't ended
            five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)

            existing_interaction = AgentInteraction.objects.filter(
                agent_1=agent_1,
                agent_2=agent_2,
                interaction_type=interaction_type
            ).filter(
                models.Q(ended_at__isnull=True) | models.Q(ended_at__gte=five_minutes_ago)
            ).first()

            if existing_interaction:
                # Update existing interaction
                existing_interaction.message_count += 1

                # Merge tags if provided
                if tags:
                    existing_tags = set(existing_interaction.tags)
                    existing_tags.update(tags)
                    existing_interaction.tags = list(existing_tags)

                # Merge custom metrics if provided
                if custom_metrics:
                    existing_interaction.metrics.update(custom_metrics)

                existing_interaction.save()

                return {
                    'status': 'SUCCESS',
                    'interaction_id': str(existing_interaction.id),
                    'session_id': str(existing_interaction.session_id)
                }
            else:
                # Create new interaction with session ID
                interaction = AgentInteraction.objects.create(
                    agent_1=agent_1,
                    agent_2=agent_2,
                    interaction_type=interaction_type,
                    started_at=timestamp,
                    message_count=1,
                    tags=tags or [],
                    metrics=custom_metrics or {
                        'first_message_id': str(message.id)
                    }
                )

                return {
                    'status': 'SUCCESS',
                    'interaction_id': str(interaction.id),
                    'session_id': str(interaction.session_id)
                }

        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to log interaction: {str(e)}')

            return {
                'status': 'FAILED',
                'error': str(e)
            }

    @staticmethod
    def log_agent_action(
        agent_id: str,
        action_type: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Log an agent action for research analysis.

        Args:
            agent_id: UUID of the agent performing the action
            action_type: Type of action (e.g., 'message_sent', 'profile_updated')
            details: Dictionary containing action details

        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - metric_id: UUID of created metric record
                - error: Error message (on failure)

        Requirements: 6.1, 6.2
        """
        try:
            from .models import ResearchMetric

            # Get agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }

            # Create metric record for the action
            metric = ResearchMetric.objects.create(
                metric_name=f'agent_action_{action_type}',
                metric_type='COUNTER',
                agent=agent,
                value=1.0,
                unit='count',
                dimensions={
                    'action_type': action_type,
                    'details': details
                },
                timestamp=timezone.now()
            )

            return {
                'status': 'SUCCESS',
                'metric_id': str(metric.id)
            }

        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to log agent action: {str(e)}')

            return {
                'status': 'FAILED',
                'error': str(e)
            }

    @staticmethod
    def query_interactions(
        filters: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query interactions with filters and time range.

        Args:
            filters: Optional filters:
                - agent_id: Filter by specific agent (either agent_1 or agent_2)
                - interaction_type: Filter by interaction type
                - tags: Filter by tags (list)
                - session_id: Filter by session ID
            time_range: Optional time range:
                - start_time: Start timestamp
                - end_time: End timestamp
            pagination: Optional pagination:
                - page: Page number (default: 1)
                - page_size: Items per page (default: 50)

        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - interactions: List of interaction objects
                - count: Total number of interactions
                - page: Current page number
                - total_pages: Total number of pages
                - error: Error message (on failure)

        Requirements: 11.1, 11.2
        """
        try:
            from .models import AgentInteraction

            # Start with all interactions
            queryset = AgentInteraction.objects.all()

            # Apply filters if provided
            if filters:
                # Filter by agent (either agent_1 or agent_2)
                if 'agent_id' in filters:
                    queryset = queryset.filter(
                        models.Q(agent_1_id=filters['agent_id']) |
                        models.Q(agent_2_id=filters['agent_id'])
                    )

                # Filter by interaction type
                if 'interaction_type' in filters:
                    queryset = queryset.filter(interaction_type=filters['interaction_type'])

                # Filter by tags
                if 'tags' in filters:
                    for tag in filters['tags']:
                        queryset = queryset.filter(tags__contains=[tag])

                # Filter by session ID
                if 'session_id' in filters:
                    queryset = queryset.filter(session_id=filters['session_id'])

            # Apply time range if provided
            if time_range:
                if 'start_time' in time_range:
                    queryset = queryset.filter(started_at__gte=time_range['start_time'])

                if 'end_time' in time_range:
                    queryset = queryset.filter(started_at__lte=time_range['end_time'])

            # Order by start time (newest first)
            queryset = queryset.order_by('-started_at')

            # Apply pagination
            page = 1
            page_size = 50

            if pagination:
                page = pagination.get('page', 1)
                page_size = pagination.get('page_size', 50)

            # Calculate pagination
            total_count = queryset.count()
            total_pages = (total_count + page_size - 1) // page_size

            start_index = (page - 1) * page_size
            end_index = start_index + page_size

            # Get paginated results
            interactions_page = queryset[start_index:end_index]

            # Build interaction list
            interactions = []
            for interaction in interactions_page:
                interactions.append({
                    'id': str(interaction.id),
                    'session_id': str(interaction.session_id),
                    'agent_1': {
                        'id': str(interaction.agent_1.id),
                        'name': interaction.agent_1.name
                    },
                    'agent_2': {
                        'id': str(interaction.agent_2.id),
                        'name': interaction.agent_2.name
                    },
                    'interaction_type': interaction.interaction_type,
                    'started_at': interaction.started_at.isoformat(),
                    'ended_at': interaction.ended_at.isoformat() if interaction.ended_at else None,
                    'message_count': interaction.message_count,
                    'total_duration_seconds': interaction.total_duration_seconds,
                    'outcome': interaction.outcome,
                    'tags': interaction.tags,
                    'metrics': interaction.metrics,
                    'is_archived': interaction.is_archived
                })

            return {
                'status': 'SUCCESS',
                'interactions': interactions,
                'count': total_count,
                'page': page,
                'total_pages': total_pages
            }

        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to query interactions: {str(e)}')

            return {
                'status': 'FAILED',
                'error': str(e)
            }

    @staticmethod
    def export_interaction_data(
        format: str,
        filters: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export interaction data in specified format.

        Args:
            format: Export format ('json' or 'csv')
            filters: Optional filters (same as query_interactions)
            time_range: Optional time range (same as query_interactions)

        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - data: Exported data (string)
                - format: Export format
                - count: Number of interactions exported
                - error: Error message (on failure)

        Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
        """
        try:
            # Query interactions without pagination to get all results
            query_result = InteractionLogger.query_interactions(
                filters=filters,
                time_range=time_range,
                pagination={'page': 1, 'page_size': 999999}  # Get all
            )

            if query_result['status'] != 'SUCCESS':
                return query_result

            interactions = query_result['interactions']

            if format.lower() == 'json':
                import json
                data = json.dumps(interactions, indent=2)
            elif format.lower() == 'csv':
                import csv
                import io

                output = io.StringIO()
                if interactions:
                    # Define CSV columns
                    fieldnames = [
                        'id', 'session_id', 'agent_1_id', 'agent_1_name',
                        'agent_2_id', 'agent_2_name', 'interaction_type',
                        'started_at', 'ended_at', 'message_count',
                        'total_duration_seconds', 'outcome', 'tags', 'metrics'
                    ]

                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()

                    for interaction in interactions:
                        import json
                        writer.writerow({
                            'id': interaction['id'],
                            'session_id': interaction['session_id'],
                            'agent_1_id': interaction['agent_1']['id'],
                            'agent_1_name': interaction['agent_1']['name'],
                            'agent_2_id': interaction['agent_2']['id'],
                            'agent_2_name': interaction['agent_2']['name'],
                            'interaction_type': interaction['interaction_type'],
                            'started_at': interaction['started_at'],
                            'ended_at': interaction['ended_at'] or '',
                            'message_count': interaction['message_count'],
                            'total_duration_seconds': interaction['total_duration_seconds'],
                            'outcome': interaction['outcome'],
                            'tags': json.dumps(interaction['tags']),
                            'metrics': json.dumps(interaction['metrics'])
                        })

                data = output.getvalue()
            else:
                return {
                    'status': 'FAILED',
                    'error': f'Unsupported format: {format}. Use "json" or "csv".'
                }

            return {
                'status': 'SUCCESS',
                'data': data,
                'format': format,
                'count': len(interactions)
            }

        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to export interaction data: {str(e)}')

            return {
                'status': 'FAILED',
                'error': str(e)
            }

    @staticmethod
    def anonymize_data(
        interaction_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Anonymize interaction data by replacing agent identifiers with pseudonyms.

        Args:
            interaction_ids: List of interaction IDs to anonymize

        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - anonymized_count: Number of interactions anonymized
                - pseudonym_map: Mapping of original agent IDs to pseudonyms
                - error: Error message (on failure)

        Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
        """
        try:
            from .models import AgentInteraction

            # Get interactions
            interactions = AgentInteraction.objects.filter(
                id__in=interaction_ids
            )

            if not interactions.exists():
                return {
                    'status': 'FAILED',
                    'error': 'No interactions found with provided IDs'
                }

            # Create pseudonym mapping
            pseudonym_map = {}
            pseudonym_counter = 1

            def get_pseudonym(agent_id: str) -> str:
                nonlocal pseudonym_counter
                if agent_id not in pseudonym_map:
                    pseudonym_map[agent_id] = f'Agent_{pseudonym_counter:03d}'
                    pseudonym_counter += 1
                return pseudonym_map[agent_id]

            # Anonymize interactions
            anonymized_count = 0

            for interaction in interactions:
                # Replace agent identifiers with pseudonyms in metrics
                if interaction.metrics:
                    # Store pseudonyms in metrics
                    interaction.metrics['anonymized'] = True
                    interaction.metrics['agent_1_pseudonym'] = get_pseudonym(str(interaction.agent_1_id))
                    interaction.metrics['agent_2_pseudonym'] = get_pseudonym(str(interaction.agent_2_id))

                # Mark as archived (anonymized data)
                interaction.is_archived = True
                interaction.save()

                anonymized_count += 1

            return {
                'status': 'SUCCESS',
                'anonymized_count': anonymized_count,
                'pseudonym_map': pseudonym_map
            }

        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to anonymize data: {str(e)}')

            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def end_interaction_session(
        interaction_id: str
    ) -> Dict[str, Any]:
        """
        End an interaction session and calculate total duration and message count.
        
        Args:
            interaction_id: UUID of the interaction to end
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - interaction_id: UUID of the interaction
                - total_duration_seconds: Total duration in seconds
                - message_count: Total number of messages
                - error: Error message (on failure)
        
        Requirements: 6.5
        """
        try:
            from .models import AgentInteraction
            
            # Get interaction
            try:
                interaction = AgentInteraction.objects.get(id=interaction_id)
            except AgentInteraction.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Interaction not found'
                }
            
            # Check if already ended
            if interaction.ended_at:
                return {
                    'status': 'FAILED',
                    'error': 'Interaction already ended'
                }
            
            # Set end time
            interaction.ended_at = timezone.now()
            
            # Calculate total duration in seconds
            duration = interaction.ended_at - interaction.started_at
            interaction.total_duration_seconds = int(duration.total_seconds())
            
            # Save the interaction
            interaction.save()
            
            return {
                'status': 'SUCCESS',
                'interaction_id': str(interaction.id),
                'total_duration_seconds': interaction.total_duration_seconds,
                'message_count': interaction.message_count
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to end interaction session: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }




    @staticmethod
    def log_agent_action(
        agent_id: str,
        action_type: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Log an agent action for research analysis.
        
        Args:
            agent_id: UUID of the agent performing the action
            action_type: Type of action (e.g., 'message_sent', 'profile_updated')
            details: Dictionary containing action details
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - metric_id: UUID of created metric record
                - error: Error message (on failure)
        
        Requirements: 6.1, 6.2
        """
        try:
            from .models import ResearchMetric
            
            # Get agent
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Create metric record for the action
            metric = ResearchMetric.objects.create(
                metric_name=f'agent_action_{action_type}',
                metric_type='COUNTER',
                agent=agent,
                value=1.0,
                unit='count',
                dimensions={
                    'action_type': action_type,
                    'details': details
                },
                timestamp=timezone.now()
            )
            
            return {
                'status': 'SUCCESS',
                'metric_id': str(metric.id)
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to log agent action: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def query_interactions(
        filters: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query interactions with filters and time range.
        
        Args:
            filters: Optional filters:
                - agent_id: Filter by specific agent (either agent_1 or agent_2)
                - interaction_type: Filter by interaction type
                - tags: Filter by tags (list)
                - session_id: Filter by session ID
            time_range: Optional time range:
                - start_time: Start timestamp
                - end_time: End timestamp
            pagination: Optional pagination:
                - page: Page number (default: 1)
                - page_size: Items per page (default: 50)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - interactions: List of interaction objects
                - count: Total number of interactions
                - page: Current page number
                - total_pages: Total number of pages
                - error: Error message (on failure)
        
        Requirements: 11.1, 11.2
        """
        try:
            from .models import AgentInteraction
            
            # Start with all interactions
            queryset = AgentInteraction.objects.all()
            
            # Apply filters if provided
            if filters:
                # Filter by agent (either agent_1 or agent_2)
                if 'agent_id' in filters:
                    queryset = queryset.filter(
                        models.Q(agent_1_id=filters['agent_id']) | 
                        models.Q(agent_2_id=filters['agent_id'])
                    )
                
                # Filter by interaction type
                if 'interaction_type' in filters:
                    queryset = queryset.filter(interaction_type=filters['interaction_type'])
                
                # Filter by tags
                if 'tags' in filters:
                    for tag in filters['tags']:
                        queryset = queryset.filter(tags__contains=[tag])
                
                # Filter by session ID
                if 'session_id' in filters:
                    queryset = queryset.filter(session_id=filters['session_id'])
            
            # Apply time range if provided
            if time_range:
                if 'start_time' in time_range:
                    queryset = queryset.filter(started_at__gte=time_range['start_time'])
                
                if 'end_time' in time_range:
                    queryset = queryset.filter(started_at__lte=time_range['end_time'])
            
            # Order by start time (newest first)
            queryset = queryset.order_by('-started_at')
            
            # Apply pagination
            page = 1
            page_size = 50
            
            if pagination:
                page = pagination.get('page', 1)
                page_size = pagination.get('page_size', 50)
            
            # Calculate pagination
            total_count = queryset.count()
            total_pages = (total_count + page_size - 1) // page_size
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            # Get paginated results
            interactions_page = queryset[start_index:end_index]
            
            # Build interaction list
            interactions = []
            for interaction in interactions_page:
                interactions.append({
                    'id': str(interaction.id),
                    'session_id': str(interaction.session_id),
                    'agent_1': {
                        'id': str(interaction.agent_1.id),
                        'name': interaction.agent_1.name
                    },
                    'agent_2': {
                        'id': str(interaction.agent_2.id),
                        'name': interaction.agent_2.name
                    },
                    'interaction_type': interaction.interaction_type,
                    'started_at': interaction.started_at.isoformat(),
                    'ended_at': interaction.ended_at.isoformat() if interaction.ended_at else None,
                    'message_count': interaction.message_count,
                    'total_duration_seconds': interaction.total_duration_seconds,
                    'outcome': interaction.outcome,
                    'tags': interaction.tags,
                    'metrics': interaction.metrics,
                    'is_archived': interaction.is_archived
                })
            
            return {
                'status': 'SUCCESS',
                'interactions': interactions,
                'count': total_count,
                'page': page,
                'total_pages': total_pages
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to query interactions: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def export_interaction_data(
        format: str,
        filters: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export interaction data in specified format.
        
        Args:
            format: Export format ('json' or 'csv')
            filters: Optional filters (same as query_interactions)
            time_range: Optional time range (same as query_interactions)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - data: Exported data (string)
                - format: Export format
                - count: Number of interactions exported
                - error: Error message (on failure)
        
        Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
        """
        try:
            # Query interactions without pagination to get all results
            query_result = InteractionLogger.query_interactions(
                filters=filters,
                time_range=time_range,
                pagination={'page': 1, 'page_size': 999999}  # Get all
            )
            
            if query_result['status'] != 'SUCCESS':
                return query_result
            
            interactions = query_result['interactions']
            
            if format.lower() == 'json':
                import json
                data = json.dumps(interactions, indent=2)
            elif format.lower() == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                if interactions:
                    # Define CSV columns
                    fieldnames = [
                        'id', 'session_id', 'agent_1_id', 'agent_1_name',
                        'agent_2_id', 'agent_2_name', '
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to anonymize data: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    }
            
        except Exception as e:mized_count': anonymized_count,
                'pseudonym_map': pseudonym_map
        
                    interaction.metrics['agent_1_pseudonym'] = get_pseudonym(str(interaction.agent_1_id))
                    interaction.metrics['agent_2_pseudonym'] = get_pseudonym(str(interaction.agent_2_id))
                
                # Mark as archived (anonymized data)
                interaction.is_archived = True
                interaction.save()
                
                anonymized_count += 1
            
            return {
                'status': 'SUCCESS',
                'anony              # Store pseudonyms in metrics
                    interaction.metrics['anonymized'] = True                nonlocal pseudonym_counter
                if agent_id not in pseudonym_map:
                    pseudonym_map[agent_id] = f'Agent_{pseudonym_counter:03d}'
                    pseudonym_counter += 1
                return pseudonym_map[agent_id]
            
            # Anonymize interactions
            anonymized_count = 0
            
            for interaction in interactions:
                # Replace agent identifiers with pseudonyms in metrics
                if interaction.metrics:
      r:
nteractions
            interactions = AgentInteraction.objects.filter(
                id__in=interaction_ids
            )
            
            if not interactions.exists():
                return {
                    'status': 'FAILED',
                    'error': 'No interactions found with provided IDs'
                }
            
            # Create pseudonym mapping
            pseudonym_map = {}
            pseudonym_counter = 1
            
            def get_pseudonym(agent_id: str) -> st 12.3, 12.4, 12.5
        """
        try:
            from .models import AgentInteraction
            
            # Get i   Anonymize interaction data by replacing agent identifiers with pseudonyms.
        
        Args:
            interaction_ids: List of interaction IDs to anonymize
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - anonymized_count: Number of interactions anonymized
                - pseudonym_map: Mapping of original agent IDs to pseudonyms
                - error: Error message (on failure)
        
        Requirements: 12.1, 12.2,nteraction_ids: List[str]
    ) -> Dict[str, Any]:
        """
     ESS',
                'data': data,
                'format': format,
                'count': len(interactions)
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.interaction_logger')
            logger.error(f'Failed to export interaction data: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def anonymize_data(
        i       
            return {
                'status': 'SUCCaction['total_duration_seconds'],
                            'outcome': interaction['outcome'],
                            'tags': json.dumps(interaction['tags']),
                            'metrics': json.dumps(interaction['metrics'])
                        })
                
                data = output.getvalue()
            else:
                return {
                    'status': 'FAILED',
                    'error': f'Unsupported format: {format}. Use "json" or "csv".'
                }
     count': interaction['message_count'],
                            'total_duration_seconds': inter': interaction['agent_1']['id'],
                            'agent_1_name': interaction['agent_1']['name'],
                            'agent_2_id': interaction['agent_2']['id'],
                            'agent_2_name': interaction['agent_2']['name'],
                            'interaction_type': interaction['interaction_type'],
                            'started_at': interaction['started_at'],
                            'ended_at': interaction['ended_at'] or '',
                            'message_n['id'],
                            'session_id': interaction['session_id'],
                            'agent_1_idinteraction_type',
                        'started_at', 'ended_at', 'message_count',
                        'total_duration_seconds', 'outcome', 'tags', 'metrics'
                    ]
                    
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for interaction in interactions:
                        import json
                        writer.writerow({
                            'id': interactio
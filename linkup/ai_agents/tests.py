"""
Unit tests for AI Agents services.
"""
import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import AIAgent, AgentAPIKey
from .services import AgentRegistryService


class AgentRegistryServiceTests(TestCase):
    """Test cases for AgentRegistryService."""
    
    def setUp(self):
        """Set up test data."""
        self.valid_registration_data = {
            'name': 'TestAgent',
            'description': 'A test agent for unit testing',
            'capabilities': {'natural_language': True, 'task_execution': False},
            'owner_email': 'test@example.com',
            'agent_type': 'CONVERSATIONAL',
            'version': '1.0.0'
        }
    
    def tearDown(self):
        """Clean up test data."""
        AIAgent.objects.all().delete()
        AgentAPIKey.objects.all().delete()
    
    # Test: Agent Registration
    
    def test_register_agent_with_valid_data(self):
        """Test registering an agent with valid data succeeds."""
        result = AgentRegistryService.register_agent(**self.valid_registration_data)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('agent_id', result)
        self.assertIn('api_key', result)
        self.assertIn('key_prefix', result)
        self.assertTrue(result['api_key'].startswith('agnt_'))
        
        # Verify agent was created in database
        agent = AIAgent.objects.get(id=result['agent_id'])
        self.assertEqual(agent.name, 'TestAgent')
        self.assertEqual(agent.agent_type, 'CONVERSATIONAL')
        self.assertTrue(agent.is_active)
        self.assertFalse(agent.is_suspended)
    
    def test_register_agent_with_duplicate_name(self):
        """Test that registering an agent with duplicate name fails."""
        # Register first agent
        AgentRegistryService.register_agent(**self.valid_registration_data)
        
        # Try to register second agent with same name
        result = AgentRegistryService.register_agent(**self.valid_registration_data)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('already exists', result['error'])
    
    def test_register_agent_with_invalid_email(self):
        """Test that registering an agent with invalid email fails."""
        data = self.valid_registration_data.copy()
        data['owner_email'] = 'invalid-email'
        
        result = AgentRegistryService.register_agent(**data)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('Invalid email', result['error'])
    
    def test_register_agent_with_short_name(self):
        """Test that registering an agent with name < 3 characters fails."""
        data = self.valid_registration_data.copy()
        data['name'] = 'AB'
        
        result = AgentRegistryService.register_agent(**data)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('between 3 and 100 characters', result['error'])
    
    def test_register_agent_with_long_name(self):
        """Test that registering an agent with name > 100 characters fails."""
        data = self.valid_registration_data.copy()
        data['name'] = 'A' * 101
        
        result = AgentRegistryService.register_agent(**data)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('between 3 and 100 characters', result['error'])
    
    def test_register_agent_with_invalid_agent_type(self):
        """Test that registering an agent with invalid type fails."""
        data = self.valid_registration_data.copy()
        data['agent_type'] = 'INVALID_TYPE'
        
        result = AgentRegistryService.register_agent(**data)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('Invalid agent type', result['error'])
    
    def test_register_agent_with_invalid_capabilities(self):
        """Test that registering an agent with non-dict capabilities fails."""
        data = self.valid_registration_data.copy()
        data['capabilities'] = ['not', 'a', 'dict']
        
        result = AgentRegistryService.register_agent(**data)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('valid JSON object', result['error'])
    
    def test_register_agent_creates_api_key(self):
        """Test that registering an agent creates an API key record."""
        result = AgentRegistryService.register_agent(**self.valid_registration_data)
        
        self.assertEqual(result['status'], 'SUCCESS')
        
        # Verify API key was created
        agent = AIAgent.objects.get(id=result['agent_id'])
        api_keys = AgentAPIKey.objects.filter(agent=agent)
        
        self.assertEqual(api_keys.count(), 1)
        api_key = api_keys.first()
        self.assertEqual(api_key.name, 'Primary Key')
        self.assertEqual(api_key.key_prefix, result['key_prefix'])
        self.assertTrue(api_key.is_active)
        self.assertEqual(api_key.rate_limit, 1000)
        self.assertIn('read', api_key.scopes)
        self.assertIn('write', api_key.scopes)
        self.assertIn('communicate', api_key.scopes)
    
    # Test: Agent Profile Management
    
    def test_update_agent_profile_with_valid_data(self):
        """Test updating agent profile with valid data succeeds."""
        # Create agent
        reg_result = AgentRegistryService.register_agent(**self.valid_registration_data)
        agent_id = reg_result['agent_id']
        
        # Update profile
        update_data = {
            'description': 'Updated description',
            'capabilities': {'new_capability': True},
            'version': '2.0.0'
        }
        
        result = AgentRegistryService.update_agent_profile(agent_id, update_data)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('description', result['updated_fields'])
        self.assertIn('capabilities', result['updated_fields'])
        self.assertIn('version', result['updated_fields'])
        
        # Verify updates in database
        agent = AIAgent.objects.get(id=agent_id)
        self.assertEqual(agent.description, 'Updated description')
        self.assertEqual(agent.capabilities, {'new_capability': True})
        self.assertEqual(agent.version, '2.0.0')
    
    def test_update_agent_profile_with_invalid_agent_id(self):
        """Test updating profile with invalid agent ID fails."""
        fake_id = str(uuid.uuid4())
        
        result = AgentRegistryService.update_agent_profile(
            fake_id,
            {'description': 'New description'}
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('not found', result['error'])
    
    def test_update_agent_profile_immutable_fields(self):
        """Test that updating immutable fields fails."""
        # Create agent
        reg_result = AgentRegistryService.register_agent(**self.valid_registration_data)
        agent_id = reg_result['agent_id']
        
        # Try to update immutable field
        result = AgentRegistryService.update_agent_profile(
            agent_id,
            {'name': 'NewName'}
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('immutable', result['error'])
    
    def test_update_agent_profile_with_invalid_capabilities(self):
        """Test updating profile with invalid capabilities fails."""
        # Create agent
        reg_result = AgentRegistryService.register_agent(**self.valid_registration_data)
        agent_id = reg_result['agent_id']
        
        # Try to update with invalid capabilities
        result = AgentRegistryService.update_agent_profile(
            agent_id,
            {'capabilities': 'not a dict'}
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('valid JSON object', result['error'])
    
    def test_update_agent_profile_with_invalid_agent_type(self):
        """Test updating profile with invalid agent type fails."""
        # Create agent
        reg_result = AgentRegistryService.register_agent(**self.valid_registration_data)
        agent_id = reg_result['agent_id']
        
        # Try to update with invalid agent type
        result = AgentRegistryService.update_agent_profile(
            agent_id,
            {'agent_type': 'INVALID'}
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('Invalid agent type', result['error'])
    
    # Test: Agent Deactivation
    
    def test_deactivate_agent_success(self):
        """Test deactivating an agent succeeds."""
        # Create agent
        reg_result = AgentRegistryService.register_agent(**self.valid_registration_data)
        agent_id = reg_result['agent_id']
        
        # Deactivate agent
        result = AgentRegistryService.deactivate_agent(agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        
        # Verify agent is inactive
        agent = AIAgent.objects.get(id=agent_id)
        self.assertFalse(agent.is_active)
    
    def test_deactivate_agent_with_invalid_id(self):
        """Test deactivating agent with invalid ID fails."""
        fake_id = str(uuid.uuid4())
        
        result = AgentRegistryService.deactivate_agent(fake_id)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('not found', result['error'])
    
    # Test: Get Agent Profile
    
    def test_get_agent_profile_success(self):
        """Test retrieving agent profile succeeds."""
        # Create agent
        reg_result = AgentRegistryService.register_agent(**self.valid_registration_data)
        agent_id = reg_result['agent_id']
        
        # Get profile
        result = AgentRegistryService.get_agent_profile(agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('agent', result)
        
        agent_data = result['agent']
        self.assertEqual(agent_data['name'], 'TestAgent')
        self.assertEqual(agent_data['agent_type'], 'CONVERSATIONAL')
        self.assertEqual(agent_data['owner_email'], 'test@example.com')
        self.assertTrue(agent_data['is_active'])
        self.assertFalse(agent_data['is_suspended'])
    
    def test_get_agent_profile_with_invalid_id(self):
        """Test retrieving profile with invalid ID fails."""
        fake_id = str(uuid.uuid4())
        
        result = AgentRegistryService.get_agent_profile(fake_id)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('not found', result['error'])
    
    # Test: Agent Discovery
    
    def test_list_active_agents_no_filters(self):
        """Test listing all active agents without filters."""
        # Create multiple agents
        for i in range(3):
            data = self.valid_registration_data.copy()
            data['name'] = f'TestAgent{i}'
            AgentRegistryService.register_agent(**data)
        
        # List agents
        result = AgentRegistryService.list_active_agents()
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 3)
        self.assertEqual(len(result['agents']), 3)
    
    def test_list_active_agents_excludes_inactive(self):
        """Test that listing agents excludes inactive agents."""
        # Create active agent
        reg_result1 = AgentRegistryService.register_agent(**self.valid_registration_data)
        
        # Create and deactivate second agent
        data2 = self.valid_registration_data.copy()
        data2['name'] = 'TestAgent2'
        reg_result2 = AgentRegistryService.register_agent(**data2)
        AgentRegistryService.deactivate_agent(reg_result2['agent_id'])
        
        # List agents
        result = AgentRegistryService.list_active_agents()
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['agents'][0]['name'], 'TestAgent')
    
    def test_list_active_agents_excludes_suspended(self):
        """Test that listing agents excludes suspended agents."""
        # Create active agent
        reg_result1 = AgentRegistryService.register_agent(**self.valid_registration_data)
        
        # Create and suspend second agent
        data2 = self.valid_registration_data.copy()
        data2['name'] = 'TestAgent2'
        reg_result2 = AgentRegistryService.register_agent(**data2)
        agent2 = AIAgent.objects.get(id=reg_result2['agent_id'])
        agent2.is_suspended = True
        agent2.save()
        
        # List agents
        result = AgentRegistryService.list_active_agents()
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['agents'][0]['name'], 'TestAgent')
    
    def test_list_active_agents_filter_by_agent_type(self):
        """Test filtering agents by agent type."""
        # Create agents with different types
        data1 = self.valid_registration_data.copy()
        data1['name'] = 'ConversationalAgent'
        data1['agent_type'] = 'CONVERSATIONAL'
        AgentRegistryService.register_agent(**data1)
        
        data2 = self.valid_registration_data.copy()
        data2['name'] = 'TaskAgent'
        data2['agent_type'] = 'TASK_BASED'
        AgentRegistryService.register_agent(**data2)
        
        # Filter by CONVERSATIONAL
        result = AgentRegistryService.list_active_agents(
            filters={'agent_type': 'CONVERSATIONAL'}
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['agents'][0]['agent_type'], 'CONVERSATIONAL')
    
    def test_list_active_agents_filter_by_capabilities_dict(self):
        """Test filtering agents by capabilities (dict filter)."""
        # Create agents with different capabilities
        data1 = self.valid_registration_data.copy()
        data1['name'] = 'Agent1'
        data1['capabilities'] = {'natural_language': True, 'vision': False}
        AgentRegistryService.register_agent(**data1)
        
        data2 = self.valid_registration_data.copy()
        data2['name'] = 'Agent2'
        data2['capabilities'] = {'natural_language': False, 'vision': True}
        AgentRegistryService.register_agent(**data2)
        
        # Filter by natural_language: True
        result = AgentRegistryService.list_active_agents(
            filters={'capabilities': {'natural_language': True}}
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['agents'][0]['name'], 'Agent1')
    
    def test_list_active_agents_filter_by_capabilities_list(self):
        """Test filtering agents by capabilities (list filter)."""
        # Create agents with different capabilities
        data1 = self.valid_registration_data.copy()
        data1['name'] = 'Agent1'
        data1['capabilities'] = {'natural_language': True, 'vision': False}
        AgentRegistryService.register_agent(**data1)
        
        data2 = self.valid_registration_data.copy()
        data2['name'] = 'Agent2'
        data2['capabilities'] = {'audio': True}
        AgentRegistryService.register_agent(**data2)
        
        # Filter by presence of 'vision' key
        result = AgentRegistryService.list_active_agents(
            filters={'capabilities': ['vision']}
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['agents'][0]['name'], 'Agent1')
    
    # Test: API Key Generation
    
    def test_generate_secure_api_key_format(self):
        """Test that generated API keys have correct format."""
        api_key = AgentRegistryService._generate_secure_api_key(32)
        
        self.assertTrue(api_key.startswith('agnt_'))
        self.assertGreater(len(api_key), 40)  # Should be longer than just prefix
    
    def test_generate_secure_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = set()
        for _ in range(100):
            key = AgentRegistryService._generate_secure_api_key(32)
            keys.add(key)
        
        # All 100 keys should be unique
        self.assertEqual(len(keys), 100)
    
    def test_hash_api_key(self):
        """Test that API key hashing works correctly."""
        api_key = 'test_api_key_12345'
        hashed = AgentRegistryService._hash_api_key(api_key)
        
        # Hash should be different from original
        self.assertNotEqual(hashed, api_key)
        
        # Hash should be consistent
        hashed2 = AgentRegistryService._hash_api_key(api_key)
        # Note: Django's make_password includes salt, so hashes will differ
        # We just verify it produces a hash
        self.assertIsNotNone(hashed2)
        self.assertGreater(len(hashed2), 20)



class AgentAuthenticationServiceTests(TestCase):
    """Test cases for AgentAuthenticationService."""
    
    def setUp(self):
        """Set up test data."""
        from .services import AgentAuthenticationService
        
        # Create a test agent
        self.registration_data = {
            'name': 'AuthTestAgent',
            'description': 'Agent for authentication testing',
            'capabilities': {'natural_language': True},
            'owner_email': 'auth@example.com',
            'agent_type': 'CONVERSATIONAL'
        }
        
        reg_result = AgentRegistryService.register_agent(**self.registration_data)
        self.agent_id = reg_result['agent_id']
        self.api_key = reg_result['api_key']
        self.agent = AIAgent.objects.get(id=self.agent_id)
    
    def tearDown(self):
        """Clean up test data."""
        AIAgent.objects.all().delete()
        AgentAPIKey.objects.all().delete()
    
    # Test: API Key Generation
    
    def test_generate_api_key_success(self):
        """Test generating a new API key for an agent."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.generate_api_key(self.agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('api_key', result)
        self.assertIn('key_prefix', result)
        self.assertIn('key_id', result)
        self.assertTrue(result['api_key'].startswith('agnt_'))
        
        # Verify API key was created in database
        api_keys = AgentAPIKey.objects.filter(agent=self.agent)
        self.assertEqual(api_keys.count(), 2)  # Primary key + new key
    
    def test_generate_api_key_invalid_agent(self):
        """Test generating API key for non-existent agent fails."""
        from .services import AgentAuthenticationService
        
        fake_id = str(uuid.uuid4())
        result = AgentAuthenticationService.generate_api_key(fake_id)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('not found', result['error'])
    
    # Test: API Key Validation
    
    def test_validate_api_key_success(self):
        """Test validating a correct API key."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.validate_api_key(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertTrue(result['valid'])
        self.assertIn('api_key_record', result)
        self.assertIn('scopes', result['api_key_record'])
    
    def test_validate_api_key_invalid_key(self):
        """Test validating an incorrect API key fails."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.validate_api_key(
            self.agent_id,
            'agnt_invalid_key_12345'
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['valid'])
        self.assertIn('Invalid API key', result['error'])
    
    def test_validate_api_key_inactive_agent(self):
        """Test validating API key for inactive agent fails."""
        from .services import AgentAuthenticationService
        
        # Deactivate agent
        self.agent.is_active = False
        self.agent.save()
        
        result = AgentAuthenticationService.validate_api_key(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['valid'])
        self.assertIn('inactive', result['error'])
    
    def test_validate_api_key_suspended_agent(self):
        """Test validating API key for suspended agent fails."""
        from .services import AgentAuthenticationService
        
        # Suspend agent
        self.agent.is_suspended = True
        self.agent.save()
        
        result = AgentAuthenticationService.validate_api_key(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['valid'])
        self.assertIn('suspended', result['error'])
    
    def test_validate_api_key_expired_key(self):
        """Test validating an expired API key fails."""
        from .services import AgentAuthenticationService
        from django.utils import timezone
        from datetime import timedelta
        
        # Set API key to expired
        api_key_record = AgentAPIKey.objects.filter(agent=self.agent).first()
        api_key_record.expires_at = timezone.now() - timedelta(days=1)
        api_key_record.save()
        
        result = AgentAuthenticationService.validate_api_key(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['valid'])
        self.assertIn('expired', result['error'])
    
    def test_validate_api_key_nonexistent_agent(self):
        """Test validating API key for non-existent agent fails."""
        from .services import AgentAuthenticationService
        
        fake_id = str(uuid.uuid4())
        result = AgentAuthenticationService.validate_api_key(fake_id, self.api_key)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['valid'])
        self.assertIn('not found', result['error'])
    
    # Test: Agent Authentication
    
    def test_authenticate_agent_success(self):
        """Test authenticating an agent with valid credentials."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.authenticate_agent(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('access_token', result)
        self.assertIn('refresh_token', result)
        self.assertEqual(result['expires_in'], 3600)
        self.assertEqual(result['token_type'], 'Bearer')
        
        # Verify agent last_active_at was updated
        self.agent.refresh_from_db()
        self.assertIsNotNone(self.agent.last_active_at)
        
        # Verify API key usage was incremented
        api_key_record = AgentAPIKey.objects.filter(agent=self.agent).first()
        self.assertEqual(api_key_record.usage_count, 1)
        self.assertIsNotNone(api_key_record.last_used_at)
    
    def test_authenticate_agent_invalid_credentials(self):
        """Test authenticating with invalid credentials fails."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.authenticate_agent(
            self.agent_id,
            'agnt_invalid_key'
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('error', result)
    
    def test_authenticate_agent_inactive_agent(self):
        """Test authenticating inactive agent fails."""
        from .services import AgentAuthenticationService
        
        # Deactivate agent
        self.agent.is_active = False
        self.agent.save()
        
        result = AgentAuthenticationService.authenticate_agent(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('inactive', result['error'])
    
    def test_authenticate_agent_suspended_agent(self):
        """Test authenticating suspended agent fails."""
        from .services import AgentAuthenticationService
        
        # Suspend agent
        self.agent.is_suspended = True
        self.agent.save()
        
        result = AgentAuthenticationService.authenticate_agent(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('suspended', result['error'])
    
    # Test: Token Refresh
    
    def test_refresh_token_success(self):
        """Test refreshing a valid token."""
        from .services import AgentAuthenticationService
        
        # First authenticate to get tokens
        auth_result = AgentAuthenticationService.authenticate_agent(
            self.agent_id,
            self.api_key
        )
        refresh_token = auth_result['refresh_token']
        
        # Refresh the token
        result = AgentAuthenticationService.refresh_token(refresh_token)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('access_token', result)
        self.assertIn('refresh_token', result)
        self.assertEqual(result['expires_in'], 3600)
        
        # New tokens should be different from old ones
        self.assertNotEqual(result['access_token'], auth_result['access_token'])
        self.assertNotEqual(result['refresh_token'], refresh_token)
    
    def test_refresh_token_invalid_token(self):
        """Test refreshing with invalid token fails."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.refresh_token('invalid_token')
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('error', result)
    
    def test_refresh_token_inactive_agent(self):
        """Test refreshing token for inactive agent fails."""
        from .services import AgentAuthenticationService
        
        # First authenticate to get tokens
        auth_result = AgentAuthenticationService.authenticate_agent(
            self.agent_id,
            self.api_key
        )
        refresh_token = auth_result['refresh_token']
        
        # Deactivate agent
        self.agent.is_active = False
        self.agent.save()
        
        # Try to refresh
        result = AgentAuthenticationService.refresh_token(refresh_token)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('inactive', result['error'])
    
    def test_refresh_token_suspended_agent(self):
        """Test refreshing token for suspended agent fails."""
        from .services import AgentAuthenticationService
        
        # First authenticate to get tokens
        auth_result = AgentAuthenticationService.authenticate_agent(
            self.agent_id,
            self.api_key
        )
        refresh_token = auth_result['refresh_token']
        
        # Suspend agent
        self.agent.is_suspended = True
        self.agent.save()
        
        # Try to refresh
        result = AgentAuthenticationService.refresh_token(refresh_token)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('suspended', result['error'])
    
    def test_refresh_token_reuse_fails(self):
        """Test that reusing a refresh token fails."""
        from .services import AgentAuthenticationService
        
        # First authenticate to get tokens
        auth_result = AgentAuthenticationService.authenticate_agent(
            self.agent_id,
            self.api_key
        )
        refresh_token = auth_result['refresh_token']
        
        # Refresh the token (first time should succeed)
        result1 = AgentAuthenticationService.refresh_token(refresh_token)
        self.assertEqual(result1['status'], 'SUCCESS')
        
        # Try to reuse the same refresh token (should fail)
        result2 = AgentAuthenticationService.refresh_token(refresh_token)
        self.assertEqual(result2['status'], 'FAILED')
    
    # Test: Token Revocation
    
    def test_revoke_token_success(self):
        """Test revoking a token."""
        from .services import AgentAuthenticationService
        
        # First authenticate to get tokens
        auth_result = AgentAuthenticationService.authenticate_agent(
            self.agent_id,
            self.api_key
        )
        refresh_token = auth_result['refresh_token']
        
        # Revoke the token
        result = AgentAuthenticationService.revoke_token(refresh_token)
        
        self.assertEqual(result['status'], 'SUCCESS')
        
        # Try to use the revoked token (should fail)
        refresh_result = AgentAuthenticationService.refresh_token(refresh_token)
        self.assertEqual(refresh_result['status'], 'FAILED')
    
    # Test: Permission Checking
    
    def test_check_permissions_allowed(self):
        """Test checking permissions for allowed action."""
        from .services import AgentAuthenticationService
        
        result = AgentAuthenticationService.check_permissions(
            self.agent_id,
            'messages',
            'read'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertTrue(result['allowed'])
    
    def test_check_permissions_denied(self):
        """Test checking permissions for denied action."""
        from .services import AgentAuthenticationService
        
        # Update API key to have limited scopes
        api_key_record = AgentAPIKey.objects.filter(agent=self.agent).first()
        api_key_record.scopes = ['read']  # Only read permission
        api_key_record.save()
        
        result = AgentAuthenticationService.check_permissions(
            self.agent_id,
            'messages',
            'write'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertFalse(result['allowed'])
    
    def test_check_permissions_inactive_agent(self):
        """Test checking permissions for inactive agent."""
        from .services import AgentAuthenticationService
        
        # Deactivate agent
        self.agent.is_active = False
        self.agent.save()
        
        result = AgentAuthenticationService.check_permissions(
            self.agent_id,
            'messages',
            'read'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertFalse(result['allowed'])
    
    def test_check_permissions_nonexistent_agent(self):
        """Test checking permissions for non-existent agent."""
        from .services import AgentAuthenticationService
        
        fake_id = str(uuid.uuid4())
        result = AgentAuthenticationService.check_permissions(
            fake_id,
            'messages',
            'read'
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['allowed'])
    
    # Test: JWT Token Generation
    
    def test_generate_jwt_token_format(self):
        """Test that JWT tokens are generated correctly."""
        from .services import AgentAuthenticationService
        
        # Authenticate to get a token
        result = AgentAuthenticationService.authenticate_agent(self.agent_id, self.api_key)
        
        self.assertEqual(result['status'], 'SUCCESS')
        token = result['access_token']
        
        # Decode and verify token
        import jwt
        from django.conf import settings
        
        secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        self.assertEqual(payload['agent_id'], str(self.agent_id))
        self.assertEqual(payload['agent_name'], 'AuthTestAgent')
        self.assertIn('scopes', payload)
        self.assertIn('issued_at', payload)
        self.assertIn('expires_at', payload)
    
    # Test: Secure API Key Generation
    
    def test_generate_secure_api_key_entropy(self):
        """Test that generated API keys have sufficient entropy."""
        from .services import AgentAuthenticationService
        
        keys = set()
        for _ in range(100):
            key = AgentAuthenticationService._generate_secure_api_key(32)
            keys.add(key)
        
        # All keys should be unique
        self.assertEqual(len(keys), 100)
        
        # All keys should start with prefix
        for key in keys:
            self.assertTrue(key.startswith('agnt_'))
    
    def test_hash_api_key_security(self):
        """Test that API key hashing is secure."""
        from .services import AgentAuthenticationService
        from django.contrib.auth.hashers import check_password
        
        api_key = 'agnt_test_key_12345'
        hashed = AgentAuthenticationService._hash_api_key(api_key)
        
        # Hash should be different from original
        self.assertNotEqual(hashed, api_key)
        
        # Should be able to verify with check_password
        self.assertTrue(check_password(api_key, hashed))
        self.assertFalse(check_password('wrong_key', hashed))



class AgentRateLimitServiceTests(TestCase):
    """Test cases for AgentRateLimitService."""
    
    def setUp(self):
        """Set up test data."""
        from .services import AgentRateLimitService
        
        # Create a test agent
        registration_result = AgentRegistryService.register_agent(
            name='RateLimitTestAgent',
            description='Agent for rate limit testing',
            capabilities={'test': True},
            owner_email='ratelimit@example.com',
            agent_type='CONVERSATIONAL'
        )
        
        self.agent_id = registration_result['agent_id']
        self.agent = AIAgent.objects.get(id=self.agent_id)
        
        # Get the API key record and set a low rate limit for testing
        self.api_key = AgentAPIKey.objects.get(agent=self.agent)
        self.api_key.rate_limit = 5  # 5 requests per minute for testing
        self.api_key.save()
    
    def tearDown(self):
        """Clean up test data."""
        from django.core.cache import cache
        from .services import AgentRateLimitService
        
        # Clear rate limit cache
        AgentRateLimitService.reset_rate_limit(self.agent_id)
        cache.clear()
        
        # Delete test data
        AIAgent.objects.all().delete()
        AgentAPIKey.objects.all().delete()
    
    def test_check_rate_limit_allows_requests_within_limit(self):
        """Test that requests within rate limit are allowed."""
        from .services import AgentRateLimitService
        
        result = AgentRateLimitService.check_rate_limit(self.agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertTrue(result['allowed'])
        self.assertEqual(result['current_count'], 0)
        self.assertEqual(result['limit'], 5)
    
    def test_check_rate_limit_blocks_requests_exceeding_limit(self):
        """Test that requests exceeding rate limit are blocked."""
        from .services import AgentRateLimitService
        
        # Make requests up to the limit
        for i in range(5):
            increment_result = AgentRateLimitService.increment_rate_limit(self.agent_id)
            self.assertEqual(increment_result['status'], 'SUCCESS')
        
        # Next check should indicate rate limit exceeded
        result = AgentRateLimitService.check_rate_limit(self.agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertFalse(result['allowed'])
        self.assertEqual(result['current_count'], 5)
        self.assertEqual(result['limit'], 5)
        self.assertIn('error', result)
    
    def test_increment_rate_limit_increases_counter(self):
        """Test that incrementing rate limit increases the counter."""
        from .services import AgentRateLimitService
        
        # Increment counter
        result = AgentRateLimitService.increment_rate_limit(self.agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['current_count'], 1)
        self.assertEqual(result['limit'], 5)
        
        # Increment again
        result = AgentRateLimitService.increment_rate_limit(self.agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['current_count'], 2)
    
    def test_reset_rate_limit_clears_counter(self):
        """Test that resetting rate limit clears the counter."""
        from .services import AgentRateLimitService
        
        # Increment counter multiple times
        for i in range(3):
            AgentRateLimitService.increment_rate_limit(self.agent_id)
        
        # Verify counter is at 3
        check_result = AgentRateLimitService.check_rate_limit(self.agent_id)
        self.assertEqual(check_result['current_count'], 3)
        
        # Reset rate limit
        reset_result = AgentRateLimitService.reset_rate_limit(self.agent_id)
        self.assertEqual(reset_result['status'], 'SUCCESS')
        
        # Verify counter is back to 0
        check_result = AgentRateLimitService.check_rate_limit(self.agent_id)
        self.assertEqual(check_result['current_count'], 0)
    
    def test_get_rate_limit_status_returns_correct_info(self):
        """Test that get_rate_limit_status returns correct information."""
        from .services import AgentRateLimitService
        
        # Increment counter twice
        AgentRateLimitService.increment_rate_limit(self.agent_id)
        AgentRateLimitService.increment_rate_limit(self.agent_id)
        
        # Get status
        result = AgentRateLimitService.get_rate_limit_status(self.agent_id)
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['current_count'], 2)
        self.assertEqual(result['limit'], 5)
        self.assertEqual(result['remaining'], 3)
        self.assertIn('reset_at', result)
    
    def test_rate_limit_for_inactive_agent_fails(self):
        """Test that rate limit check fails for inactive agent."""
        from .services import AgentRateLimitService
        
        # Deactivate agent
        self.agent.is_active = False
        self.agent.save()
        
        # Check rate limit
        result = AgentRateLimitService.check_rate_limit(self.agent_id)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['allowed'])
        self.assertIn('error', result)
    
    def test_rate_limit_for_suspended_agent_fails(self):
        """Test that rate limit check fails for suspended agent."""
        from .services import AgentRateLimitService
        
        # Suspend agent
        self.agent.is_suspended = True
        self.agent.save()
        
        # Check rate limit
        result = AgentRateLimitService.check_rate_limit(self.agent_id)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['allowed'])
        self.assertIn('error', result)
    
    def test_rate_limit_for_nonexistent_agent_fails(self):
        """Test that rate limit check fails for non-existent agent."""
        from .services import AgentRateLimitService
        
        fake_agent_id = str(uuid.uuid4())
        
        result = AgentRateLimitService.check_rate_limit(fake_agent_id)
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(result['allowed'])
        self.assertIn('error', result)

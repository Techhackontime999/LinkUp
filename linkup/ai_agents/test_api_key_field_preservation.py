"""
Preservation Property Tests for API Key Form Field Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests MUST PASS on unfixed code to establish baseline behavior.
The tests validate Property 2: Preservation - Existing Form and Metadata Behavior.

EXPECTED OUTCOME ON UNFIXED CODE: Tests PASS (confirms baseline behavior to preserve)
EXPECTED OUTCOME AFTER FIX: Tests PASS (confirms no regressions)
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import AIAgent, AgentAPIKey
from .social_models import AgentSocialProfile

User = get_user_model()


class APIKeyFieldPreservationTest(TestCase):
    """
    Preservation tests to ensure existing functionality remains unchanged after fix.
    
    These tests capture the baseline behavior on unfixed code.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        
        # Create a test agent for edit testing
        self.test_agent = AIAgent.objects.create(
            name='PreservationTestAgent',
            description='Test agent for preservation testing',
            agent_type='CONVERSATIONAL',
            capabilities={'nlp': True, 'reasoning': True},
            version='1.0.0',
            owner_email='preservation@example.com',
            api_key_hash='preservation_hash',
            metadata={
                'provider': 'google',
                'endpoint_url': 'https://api.example.com',
                'existing_field': 'should_be_preserved'
            },
            is_active=True
        )
        
        AgentSocialProfile.objects.create(
            agent=self.test_agent,
            display_name='Preservation Test Agent',
            bio='Test bio',
            is_public=True
        )
    
    def tearDown(self):
        """Clean up test data."""
        AIAgent.objects.all().delete()
        AgentAPIKey.objects.all().delete()
        User.objects.all().delete()
    
    def test_basic_form_submission_creates_agent(self):
        """
        Test that basic form submission (name, agent_type, owner_email only) 
        creates agent successfully.
        
        PRESERVATION: This behavior must remain unchanged after fix.
        """
        response = self.client.post(reverse('ai_agents:add_ai_model'), {
            'name': 'BasicAgent',
            'agent_type': 'conversational',
            'owner_email': 'basic@example.com',
            'version': '1.0.0',
            'cap_nlp': 'true',
            'is_public': 'true',
        })
        
        # Check that agent was created
        agent = AIAgent.objects.filter(name='BasicAgent').first()
        self.assertIsNotNone(agent, "Agent should be created with basic fields only")
        self.assertEqual(agent.owner_email, 'basic@example.com')
        self.assertEqual(agent.version, '1.0.0')
        self.assertTrue(agent.capabilities.get('nlp', False))
    
    def test_provider_and_endpoint_stored_in_metadata(self):
        """
        Test that provider and endpoint_url are stored in 
        agent.metadata['provider'] and agent.metadata['endpoint_url'].
        
        PRESERVATION: This behavior must remain unchanged after fix.
        Validates Requirements 3.1, 3.2
        """
        response = self.client.post(reverse('ai_agents:add_ai_model'), {
            'name': 'ProviderTestAgent',
            'agent_type': 'conversational',
            'owner_email': 'provider@example.com',
            'version': '1.0.0',
            'provider': 'openai',
            'endpoint_url': 'https://api.openai.com/v1',
            'cap_nlp': 'true',
            'is_public': 'true',
        })
        
        agent = AIAgent.objects.filter(name='ProviderTestAgent').first()
        self.assertIsNotNone(agent)
        
        # Verify provider and endpoint_url in metadata
        self.assertIn('provider', agent.metadata)
        self.assertEqual(agent.metadata['provider'], 'openai')
        self.assertIn('endpoint_url', agent.metadata)
        self.assertEqual(agent.metadata['endpoint_url'], 'https://api.openai.com/v1')
    
    def test_platform_api_key_generation_unchanged(self):
        """
        Test that platform API key generation (api_key_hash) and 
        AgentAPIKey creation work correctly.
        
        PRESERVATION: This behavior must remain unchanged after fix.
        Validates Requirement 3.4
        """
        response = self.client.post(reverse('ai_agents:add_ai_model'), {
            'name': 'PlatformKeyAgent',
            'agent_type': 'conversational',
            'owner_email': 'platformkey@example.com',
            'version': '1.0.0',
            'cap_nlp': 'true',
            'is_public': 'true',
        })
        
        agent = AIAgent.objects.filter(name='PlatformKeyAgent').first()
        self.assertIsNotNone(agent)
        
        # Verify platform API key hash is generated
        self.assertIsNotNone(agent.api_key_hash)
        self.assertTrue(len(agent.api_key_hash) > 0)
        
        # Verify AgentAPIKey record is created
        api_keys = AgentAPIKey.objects.filter(agent=agent)
        self.assertTrue(api_keys.exists(), "AgentAPIKey record should be created")
        self.assertEqual(api_keys.count(), 1)
        self.assertTrue(api_keys.first().is_active)
    
    def test_empty_optional_fields_allowed(self):
        """
        Test that empty/missing optional fields do not affect form submission 
        or agent creation.
        
        PRESERVATION: This behavior must remain unchanged after fix.
        Validates Requirement 3.3
        """
        response = self.client.post(reverse('ai_agents:add_ai_model'), {
            'name': 'MinimalAgent',
            'agent_type': 'conversational',
            'owner_email': 'minimal@example.com',
            'version': '1.0.0',
            # No provider, endpoint_url, or other optional fields
            'cap_nlp': 'true',
            'is_public': 'true',
        })
        
        agent = AIAgent.objects.filter(name='MinimalAgent').first()
        self.assertIsNotNone(agent, "Agent should be created without optional fields")
        
        # Metadata should exist but may be empty or have only default fields
        self.assertIsNotNone(agent.metadata)
    
    def test_existing_metadata_preserved_on_update(self):
        """
        Test that existing metadata fields are preserved during updates.
        
        PRESERVATION: This behavior must remain unchanged after fix.
        Validates Requirement 3.5
        """
        # Update agent with new provider
        response = self.client.post(
            reverse('ai_agents:edit_ai_model', kwargs={'agent_id': self.test_agent.id}),
            {
                'description': 'Updated description',
                'version': '1.0.1',
                'provider': 'anthropic',
                'endpoint_url': 'https://api.anthropic.com/v1',
                'cap_nlp': 'true',
                'cap_reasoning': 'true',
                'display_name': 'Preservation Test Agent',
                'bio': 'Test bio',
                'is_public': 'true',
            }
        )
        
        # Refresh agent from database
        self.test_agent.refresh_from_db()
        
        # Verify existing metadata field is preserved
        self.assertIn('existing_field', self.test_agent.metadata,
                     "Existing metadata fields should be preserved")
        self.assertEqual(self.test_agent.metadata['existing_field'], 'should_be_preserved')
        
        # Verify new metadata is added
        self.assertEqual(self.test_agent.metadata['provider'], 'anthropic')
        self.assertEqual(self.test_agent.metadata['endpoint_url'], 
                        'https://api.anthropic.com/v1')
    
    def test_capabilities_processing_unchanged(self):
        """
        Test that capabilities checkbox processing remains unchanged.
        
        PRESERVATION: This behavior must remain unchanged after fix.
        """
        response = self.client.post(reverse('ai_agents:add_ai_model'), {
            'name': 'CapabilitiesAgent',
            'agent_type': 'conversational',
            'owner_email': 'capabilities@example.com',
            'version': '1.0.0',
            'cap_nlp': 'true',
            'cap_reasoning': 'true',
            'cap_code': 'true',
            # cap_data, cap_image, cap_multimodal not checked
            'is_public': 'true',
        })
        
        agent = AIAgent.objects.filter(name='CapabilitiesAgent').first()
        self.assertIsNotNone(agent)
        
        # Verify capabilities are correctly stored
        self.assertTrue(agent.capabilities.get('nlp', False))
        self.assertTrue(agent.capabilities.get('reasoning', False))
        self.assertTrue(agent.capabilities.get('code_generation', False))
        self.assertFalse(agent.capabilities.get('data_analysis', False))
        self.assertFalse(agent.capabilities.get('image_generation', False))
        self.assertFalse(agent.capabilities.get('multimodal', False))
    
    def test_social_profile_creation_unchanged(self):
        """
        Test that social profile creation remains unchanged.
        
        PRESERVATION: This behavior must remain unchanged after fix.
        """
        response = self.client.post(reverse('ai_agents:add_ai_model'), {
            'name': 'SocialAgent',
            'agent_type': 'conversational',
            'owner_email': 'social@example.com',
            'version': '1.0.0',
            'display_name': 'Social Test Agent',
            'bio': 'This is a test bio',
            'tags': 'python, ai, test',
            'is_public': 'true',
            'cap_nlp': 'true',
        })
        
        agent = AIAgent.objects.filter(name='SocialAgent').first()
        self.assertIsNotNone(agent)
        
        # Verify social profile was created
        try:
            profile = agent.social_profile
            self.assertEqual(profile.display_name, 'Social Test Agent')
            self.assertEqual(profile.bio, 'This is a test bio')
            self.assertEqual(profile.tags, ['python', 'ai', 'test'])
            self.assertTrue(profile.is_public)
        except AgentSocialProfile.DoesNotExist:
            self.fail("Social profile should be created")

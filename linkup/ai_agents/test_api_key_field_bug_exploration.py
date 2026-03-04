"""
Bug Condition Exploration Test for API Key Form Field Missing

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

This test MUST FAIL on unfixed code to confirm the bug exists.
The test validates Property 1: Fault Condition - API Key Field Display and Storage.

EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS (this is correct - it proves the bug exists)
EXPECTED OUTCOME AFTER FIX: Test PASSES (confirms bug is fixed)
"""
import os
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import AIAgent, AgentAPIKey
from .social_models import AgentSocialProfile

User = get_user_model()


class APIKeyFieldBugExplorationTest(TestCase):
    """
    Bug condition exploration test for missing API key field.
    
    This test encodes the expected behavior and will validate the fix when it passes.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create admin user for staff_member_required decorator
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        
        # Create a test agent for edit form testing
        self.test_agent = AIAgent.objects.create(
            name='TestAgent',
            description='Test agent for API key field testing',
            agent_type='CONVERSATIONAL',
            capabilities={'nlp': True},
            version='1.0.0',
            owner_email='test@example.com',
            api_key_hash='test_hash',
            metadata={
                'provider': 'google',
                'endpoint_url': 'https://api.example.com',
                'api_key': 'existing_test_key_12345'
            },
            is_active=True
        )
        
        # Create social profile for the test agent
        AgentSocialProfile.objects.create(
            agent=self.test_agent,
            display_name='Test Agent',
            bio='Test bio',
            is_public=True
        )
    
    def tearDown(self):
        """Clean up test data."""
        AIAgent.objects.all().delete()
        AgentAPIKey.objects.all().delete()
        User.objects.all().delete()
    
    def test_add_form_contains_api_key_field(self):
        """
        Test that add_ai_model.html contains an input field with name="api_key" 
        in the Provider Configuration section.
        
        EXPECTED ON UNFIXED CODE: FAIL (field does not exist)
        EXPECTED AFTER FIX: PASS (field exists)
        """
        # Read the add_ai_model.html template
        template_path = os.path.join('templates', 'ai_agents', 'add_ai_model.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check that the template contains an input field with name="api_key"
        self.assertIn('name="api_key"', template_content,
                     "add_ai_model.html should contain an input field with name='api_key'")
        
        # Verify it's in the Provider Configuration section
        # Look for the section and then the field
        self.assertIn('Provider Configuration', template_content,
                     "Template should have Provider Configuration section")
        
        # Check for password input type (to mask the key)
        self.assertIn('type="password"', template_content,
                     "API key field should use type='password' to mask the key")
    
    def test_edit_form_contains_api_key_field(self):
        """
        Test that edit_ai_model.html contains an input field with name="api_key" 
        in the Provider Configuration section.
        
        EXPECTED ON UNFIXED CODE: FAIL (field does not exist)
        EXPECTED AFTER FIX: PASS (field exists)
        """
        # Read the edit_ai_model.html template
        template_path = os.path.join('templates', 'ai_agents', 'edit_ai_model.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check that the template contains an input field with name="api_key"
        self.assertIn('name="api_key"', template_content,
                     "edit_ai_model.html should contain an input field with name='api_key'")
        
        # Verify it's in the Provider Configuration section
        self.assertIn('Provider Configuration', template_content,
                     "Template should have Provider Configuration section")
    
    def test_edit_form_populates_api_key_value(self):
        """
        Test that edit form populates the api_key field with value from 
        agent.metadata.get('api_key', '').
        
        EXPECTED ON UNFIXED CODE: FAIL (field does not exist or value not populated)
        EXPECTED AFTER FIX: PASS (field exists and value is populated)
        """
        # Read the edit_ai_model.html template
        template_path = os.path.join('templates', 'ai_agents', 'edit_ai_model.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check that the template uses agent.metadata.api_key to populate the value
        # The template should have something like: value="{{ agent.metadata.api_key|default:'' }}"
        self.assertTrue(
            'agent.metadata.api_key' in template_content or 
            'agent.metadata.get' in template_content,
            "edit_ai_model.html should populate api_key field from agent.metadata"
        )
    
    def test_add_ai_model_post_handler_stores_api_key(self):
        """
        Test that add_ai_model POST handler extracts api_key from request.POST 
        and stores in agent.metadata['api_key'].
        
        EXPECTED ON UNFIXED CODE: FAIL (api_key not stored in metadata)
        EXPECTED AFTER FIX: PASS (api_key stored in metadata)
        """
        # Submit form with API key
        response = self.client.post('/ai-agents/admin/models/add/', {
            'name': 'NewTestAgent',
            'description': 'Test agent with API key',
            'agent_type': 'conversational',
            'version': '1.0.0',
            'owner_email': 'newtest@example.com',
            'provider': 'google',
            'endpoint_url': 'https://generativelanguage.googleapis.com/v1beta',
            'api_key': 'test_google_api_key_12345',
            'cap_nlp': 'true',
            'is_public': 'true',
        })
        
        # Check that agent was created
        agent = AIAgent.objects.filter(name='NewTestAgent').first()
        self.assertIsNotNone(agent, "Agent should be created")
        
        # Check that api_key is stored in metadata
        self.assertIn('api_key', agent.metadata,
                     "agent.metadata should contain 'api_key' key")
        self.assertEqual(agent.metadata['api_key'], 'test_google_api_key_12345',
                        "agent.metadata['api_key'] should contain the submitted API key")
    
    def test_edit_ai_model_post_handler_updates_api_key(self):
        """
        Test that edit_ai_model POST handler extracts api_key from request.POST 
        and updates agent.metadata['api_key'].
        
        EXPECTED ON UNFIXED CODE: FAIL (api_key not updated in metadata)
        EXPECTED AFTER FIX: PASS (api_key updated in metadata)
        """
        # Submit edit form with updated API key
        response = self.client.post(f'/ai-agents/admin/models/{self.test_agent.id}/edit/', {
            'description': 'Updated description',
            'version': '1.0.1',
            'provider': 'google',
            'endpoint_url': 'https://generativelanguage.googleapis.com/v1beta',
            'api_key': 'updated_google_api_key_67890',
            'cap_nlp': 'true',
            'display_name': 'Test Agent',
            'bio': 'Test bio',
            'is_public': 'true',
        })
        
        # Refresh agent from database
        self.test_agent.refresh_from_db()
        
        # Check that api_key is updated in metadata
        self.assertIn('api_key', self.test_agent.metadata,
                     "agent.metadata should contain 'api_key' key after update")
        self.assertEqual(self.test_agent.metadata['api_key'], 'updated_google_api_key_67890',
                        "agent.metadata['api_key'] should contain the updated API key")
    
    def test_empty_api_key_does_not_create_metadata_entry(self):
        """
        Test that submitting form with empty api_key does not create metadata['api_key'] entry.
        This validates that API key is optional.
        
        EXPECTED ON UNFIXED CODE: PASS (no api_key field exists, so no entry created)
        EXPECTED AFTER FIX: PASS (empty api_key does not create entry)
        """
        # Submit form without API key
        response = self.client.post('/ai-agents/admin/models/add/', {
            'name': 'AgentWithoutAPIKey',
            'description': 'Test agent without API key',
            'agent_type': 'conversational',
            'version': '1.0.0',
            'owner_email': 'nokey@example.com',
            'provider': 'google',
            'endpoint_url': 'https://api.example.com',
            'api_key': '',  # Empty API key
            'cap_nlp': 'true',
            'is_public': 'true',
        })
        
        # Check that agent was created
        agent = AIAgent.objects.filter(name='AgentWithoutAPIKey').first()
        self.assertIsNotNone(agent, "Agent should be created even without API key")
        
        # Check that api_key is NOT in metadata (optional field)
        self.assertNotIn('api_key', agent.metadata,
                        "agent.metadata should NOT contain 'api_key' key when empty")

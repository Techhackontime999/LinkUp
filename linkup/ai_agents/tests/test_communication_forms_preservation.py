"""
Preservation property tests for AI Agent Communication page.

These tests verify that existing functionality continues to work correctly
after the bug fix is applied. They test user interactions that occur AFTER
the page has fully loaded.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""
from django.test import TestCase, Client
from django.urls import reverse
from hypothesis import given, strategies as st, settings, HealthCheck
from users.models import User
from ai_agents.models import AIAgent, AgentMessage
import json


class CommunicationPagePreservationTest(TestCase):
    """
    Property-based tests that verify existing functionality is preserved.
    
    These tests observe behavior on UNFIXED code for non-buggy inputs
    (user interactions that occur AFTER page has fully loaded).
    
    **EXPECTED OUTCOME**: Tests PASS on unfixed code (confirms baseline behavior)
    """
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_tab_switching_structure_preserved(self):
        """
        Test that tab switching structure is preserved.
        
        Property: Tab buttons should have onclick handlers that call showTab()
        
        Expected: All tab buttons should have onclick="showTab(...)" attributes
        """
        response = self.client.get('/api/communicate/')
        
        # Verify tab buttons have onclick handlers
        self.assertContains(response, 'onclick="showTab(\'register\')"')
        self.assertContains(response, 'onclick="showTab(\'agents\')"')
        self.assertContains(response, 'onclick="showTab(\'communicate\')"')
        self.assertContains(response, 'onclick="showTab(\'conversations\')"')
    
    def test_form_submission_structure_preserved(self):
        """
        Test that form submission structure is preserved.
        
        Property: Forms should have submit event listeners
        
        Expected: JavaScript should contain addEventListener('submit') for forms
        """
        response = self.client.get('/api/communicate/')
        
        # Verify form submission handlers exist
        self.assertContains(response, "addEventListener('submit'")
        self.assertContains(response, "document.getElementById('register-form')")
        self.assertContains(response, "document.getElementById('message-form')")
    
    def test_api_endpoint_references_preserved(self):
        """
        Test that API endpoint references are preserved.
        
        Property: JavaScript should reference correct API endpoints
        
        Expected: API endpoints should be present in JavaScript
        """
        response = self.client.get('/api/communicate/')
        
        # Verify API endpoint references
        self.assertContains(response, '/api/agents/register/')
        self.assertContains(response, '/api/agents/authenticate/')
        self.assertContains(response, '/api/messages/')
        self.assertContains(response, '/api/messages/list/')
        self.assertContains(response, '/api/agents/')
    
    def test_success_message_elements_preserved(self):
        """
        Test that success message elements are preserved.
        
        Property: Success message divs should exist in DOM
        
        Expected: Success message elements should be present
        """
        response = self.client.get('/api/communicate/')
        
        # Verify success message elements
        self.assertContains(response, 'id="register-success"')
        self.assertContains(response, 'id="message-success"')
        self.assertContains(response, 'id="success-agent-id"')
        self.assertContains(response, 'id="success-api-key"')
    
    def test_localstorage_operations_preserved(self):
        """
        Test that LocalStorage operations are preserved.
        
        Property: JavaScript should use localStorage for storing agent info
        
        Expected: localStorage operations should be present in JavaScript
        """
        response = self.client.get('/api/communicate/')
        
        # Verify localStorage operations
        self.assertContains(response, 'localStorage.getItem')
        self.assertContains(response, 'localStorage.setItem')
        self.assertContains(response, "'myAgents'")
    
    def test_csrf_token_usage_preserved(self):
        """
        Test that CSRF token usage is preserved.
        
        Property: JavaScript should retrieve and use CSRF tokens
        
        Expected: getCSRFToken() function should be defined and used
        """
        response = self.client.get('/api/communicate/')
        
        # Verify CSRF token function
        self.assertContains(response, 'function getCSRFToken')
        self.assertContains(response, 'getCSRFToken()')
        self.assertContains(response, "'X-CSRFToken'")
    
    def test_dark_mode_styling_preserved(self):
        """
        Test that dark mode styling is preserved.
        
        Property: Elements should have dark mode classes
        
        Expected: Dark mode classes should be present
        """
        response = self.client.get('/api/communicate/')
        
        # Verify dark mode classes
        self.assertContains(response, 'dark:bg-gray-800')
        self.assertContains(response, 'dark:text-white')
        self.assertContains(response, 'dark:border-gray-700')
    
    def test_form_validation_structure_preserved(self):
        """
        Test that form validation structure is preserved.
        
        Property: Required fields should have required attribute
        
        Expected: Required fields should be marked as required
        """
        response = self.client.get('/api/communicate/')
        
        # Verify required fields
        self.assertContains(response, 'id="agent-name" name="name" required')
        self.assertContains(response, 'id="agent-type" name="agent_type" required')
        self.assertContains(response, 'id="owner-email" name="owner_email" required')
    
    @given(st.just(None))
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_tab_switching_functionality_preserved(self, _):
        """
        Property: Tab switching between all four tabs should work correctly.
        
        Expected: All tab buttons and content divs should be present
        """
        response = self.client.get('/api/communicate/')
        
        # Verify all tabs exist
        tabs = ['register', 'agents', 'communicate', 'conversations']
        for tab in tabs:
            self.assertContains(response, f'id="tab-{tab}"')
            self.assertContains(response, f'id="content-{tab}"')
            self.assertContains(response, f'showTab(\'{tab}\')')
    
    @given(st.just(None))
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_form_submission_api_calls_preserved(self, _):
        """
        Property: Form submission should call correct API endpoints.
        
        Expected: JavaScript should contain fetch calls to API endpoints
        """
        response = self.client.get('/api/communicate/')
        
        # Verify fetch calls to API endpoints
        self.assertContains(response, "fetch('/api/agents/register/'")
        self.assertContains(response, "fetch('/api/agents/authenticate/'")
        self.assertContains(response, "fetch('/api/messages/'")
    
    @given(st.just(None))
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_data_loading_functionality_preserved(self, _):
        """
        Property: Data loading functions should be defined and called.
        
        Expected: loadMyAgents, loadAgentSelectors, loadConversations functions exist
        """
        response = self.client.get('/api/communicate/')
        
        # Verify data loading functions
        self.assertContains(response, 'function loadMyAgents')
        self.assertContains(response, 'function loadAgentSelectors')
        self.assertContains(response, 'function loadConversations')
        self.assertContains(response, 'function loadConversationAgents')
    
    @given(st.just(None))
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_success_error_messages_preserved(self, _):
        """
        Property: Success/error messages should display after form submissions.
        
        Expected: Success message elements should be shown/hidden with classList
        """
        response = self.client.get('/api/communicate/')
        
        # Verify success message handling
        self.assertContains(response, "classList.remove('hidden')")
        self.assertContains(response, "classList.add('hidden')")
        self.assertContains(response, 'register-success')
        self.assertContains(response, 'message-success')
    
    @given(st.just(None))
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_localstorage_agent_storage_preserved(self, _):
        """
        Property: Agent information should be stored in localStorage.
        
        Expected: Agent data should be stored and retrieved from localStorage
        """
        response = self.client.get('/api/communicate/')
        
        # Verify localStorage operations for agents
        self.assertContains(response, "localStorage.getItem('myAgents')")
        self.assertContains(response, "localStorage.setItem('myAgents'")
        self.assertContains(response, 'JSON.parse')
        self.assertContains(response, 'JSON.stringify')
    
    @given(st.just(None))
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_csrf_token_retrieval_preserved(self, _):
        """
        Property: CSRF token should be correctly retrieved and used in API calls.
        
        Expected: getCSRFToken() should be called in fetch requests
        """
        response = self.client.get('/api/communicate/')
        
        # Verify CSRF token usage in API calls
        self.assertContains(response, 'getCSRFToken()')
        self.assertContains(response, "'X-CSRFToken': getCSRFToken()")


class CommunicationPageUIPreservationTest(TestCase):
    """
    Tests that verify UI elements and styling are preserved.
    """
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_page_title_preserved(self):
        """Test that page title is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'AI Agent Communication')
    
    def test_page_subtitle_preserved(self):
        """Test that page subtitle is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'Register AI agents and enable them to communicate')
    
    def test_tab_navigation_structure_preserved(self):
        """Test that tab navigation structure is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'class="tab-button')
        self.assertContains(response, 'class="tab-content')
    
    def test_form_styling_preserved(self):
        """Test that form styling is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'class="space-y-4"')
        self.assertContains(response, 'class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6"')
    
    def test_button_styling_preserved(self):
        """Test that button styling is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'bg-purple-600')
        self.assertContains(response, 'hover:bg-purple-700')
    
    def test_input_field_styling_preserved(self):
        """Test that input field styling is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'rounded-md border-gray-300')
        self.assertContains(response, 'focus:border-purple-500')
    
    def test_success_message_styling_preserved(self):
        """Test that success message styling is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'bg-green-50 dark:bg-green-900')
        self.assertContains(response, 'text-green-800 dark:text-green-200')
    
    def test_agent_card_styling_preserved(self):
        """Test that agent card styling is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'class="agent-card')
    
    def test_capability_tags_preserved(self):
        """Test that capability tags are preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'name="capability_natural_language"')
        self.assertContains(response, 'name="capability_task_execution"')
        self.assertContains(response, 'name="capability_learning"')
        self.assertContains(response, 'name="capability_reasoning"')
    
    def test_provider_selection_preserved(self):
        """Test that provider selection is preserved."""
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="provider"')
        self.assertContains(response, 'id="provider-api-key"')
        self.assertContains(response, 'value="google"')
        self.assertContains(response, 'value="openai"')
        self.assertContains(response, 'value="anthropic"')

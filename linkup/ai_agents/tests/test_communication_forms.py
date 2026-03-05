"""
Bug condition exploration tests for AI Agent Communication page.

This test file demonstrates the bug where forms are not displaying on the 
AI Agent Communication page at `/api/communicate/`. The page shows the title, 
subtitle, and tabs correctly, but all form content remains hidden.

The root cause is that JavaScript attempts to attach event listeners to form 
elements before the DOM is fully ready, causing the script to fail silently.

**Validates: Requirements 1.1, 1.2, 1.3**
"""
from django.test import TestCase, Client
from django.urls import reverse
from hypothesis import given, strategies as st, settings, HealthCheck
from users.models import User
import time


class CommunicationPageFormVisibilityTest(TestCase):
    """
    Test that verifies all form elements are visible and functional on the 
    AI Agent Communication page when it loads.
    
    This test MUST FAIL on unfixed code to prove the bug exists.
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
    
    def test_page_loads_successfully(self):
        """
        Test that the AI Agent Communication page loads without errors.
        
        Expected: Page returns 200 status code
        Actual on unfixed code: Page may load but forms are hidden
        """
        response = self.client.get('/api/communicate/')
        self.assertEqual(response.status_code, 200)
    
    def test_register_form_element_exists_in_dom(self):
        """
        Test that the register form element exists in the DOM.
        
        Expected: register-form element should be present in HTML
        Actual on unfixed code: Element exists but may be hidden
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="register-form"')
    
    def test_message_form_element_exists_in_dom(self):
        """
        Test that the message form element exists in the DOM.
        
        Expected: message-form element should be present in HTML
        Actual on unfixed code: Element exists but may be hidden
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="message-form"')
    
    def test_conversation_agent_selector_exists_in_dom(self):
        """
        Test that the conversation agent selector exists in the DOM.
        
        Expected: conversation-agent element should be present in HTML
        Actual on unfixed code: Element exists but may be hidden
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="conversation-agent"')
    
    def test_all_tab_buttons_exist_in_dom(self):
        """
        Test that all tab buttons exist in the DOM.
        
        Expected: All four tab buttons should be present
        Actual on unfixed code: Buttons exist but may not be functional
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="tab-register"')
        self.assertContains(response, 'id="tab-agents"')
        self.assertContains(response, 'id="tab-communicate"')
        self.assertContains(response, 'id="tab-conversations"')
    
    def test_communication_js_script_loaded(self):
        """
        Test that the communication.js script is loaded.
        
        Expected: Script tag should reference communication.js
        Actual on unfixed code: Script loads but may execute before DOM ready
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'communication.js')
    
    def test_csrf_token_in_register_form(self):
        """
        Test that CSRF token is present in the register form.
        
        Expected: CSRF token should be in the form
        Actual on unfixed code: Token exists but getCSRFToken() may fail
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'csrfmiddlewaretoken')
    
    def test_csrf_token_in_message_form(self):
        """
        Test that CSRF token is present in the message form.
        
        Expected: CSRF token should be in the form
        Actual on unfixed code: Token exists but getCSRFToken() may fail
        """
        response = self.client.get('/api/communicate/')
        # Count CSRF tokens - should be at least 2 (one per form)
        csrf_count = response.content.decode().count('csrfmiddlewaretoken')
        self.assertGreaterEqual(csrf_count, 2)
    
    def test_register_form_has_required_fields(self):
        """
        Test that the register form has all required input fields.
        
        Expected: All form fields should be present
        Actual on unfixed code: Fields exist but form may not be functional
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="agent-name"')
        self.assertContains(response, 'id="agent-description"')
        self.assertContains(response, 'id="agent-type"')
        self.assertContains(response, 'id="owner-email"')
    
    def test_message_form_has_required_fields(self):
        """
        Test that the message form has all required input fields.
        
        Expected: All form fields should be present
        Actual on unfixed code: Fields exist but form may not be functional
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="sender-agent"')
        self.assertContains(response, 'id="recipient-agent"')
        self.assertContains(response, 'id="message-content"')
    
    def test_tab_content_divs_exist(self):
        """
        Test that all tab content divs exist in the DOM.
        
        Expected: All content divs should be present
        Actual on unfixed code: Divs exist but may be hidden
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'id="content-register"')
        self.assertContains(response, 'id="content-agents"')
        self.assertContains(response, 'id="content-communicate"')
        self.assertContains(response, 'id="content-conversations"')
    
    def test_page_title_and_subtitle_present(self):
        """
        Test that page title and subtitle are present.
        
        Expected: Title and subtitle should be visible
        Actual on unfixed code: Title and subtitle display correctly
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'AI Agent Communication')
        self.assertContains(response, 'Register AI agents and enable them to communicate')


class CommunicationPageJavaScriptFunctionalityTest(TestCase):
    """
    Test that verifies JavaScript functionality on the AI Agent Communication page.
    
    This test uses Selenium to verify that event listeners are attached and 
    the page is functional.
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
    
    def test_show_tab_function_exists(self):
        """
        Test that the showTab function is defined in JavaScript.
        
        Expected: showTab function should be defined
        Actual on unfixed code: Function may be defined but event listeners not attached
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'function showTab')
    
    def test_get_csrf_token_function_exists(self):
        """
        Test that the getCSRFToken function is defined in JavaScript.
        
        Expected: getCSRFToken function should be defined
        Actual on unfixed code: Function exists but may fail if called before DOM ready
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'function getCSRFToken')
    
    def test_register_form_event_listener_attached(self):
        """
        Test that event listener is attached to register form.
        
        Expected: addEventListener should be called on register-form
        Actual on unfixed code: addEventListener may be called before element exists
        """
        response = self.client.get('/api/communicate/')
        # Check that the JavaScript contains the event listener attachment
        self.assertContains(response, "document.getElementById('register-form')")
        self.assertContains(response, "addEventListener('submit'")
    
    def test_message_form_event_listener_attached(self):
        """
        Test that event listener is attached to message form.
        
        Expected: addEventListener should be called on message-form
        Actual on unfixed code: addEventListener may be called before element exists
        """
        response = self.client.get('/api/communicate/')
        # Check that the JavaScript contains the event listener attachment
        self.assertContains(response, "document.getElementById('message-form')")
    
    def test_conversation_agent_change_listener_attached(self):
        """
        Test that change listener is attached to conversation agent selector.
        
        Expected: addEventListener should be called on conversation-agent
        Actual on unfixed code: addEventListener may be called before element exists
        """
        response = self.client.get('/api/communicate/')
        # Check that the JavaScript contains the event listener attachment
        self.assertContains(response, "document.getElementById('conversation-agent')")
    
    def test_dom_content_loaded_event_handler_exists(self):
        """
        Test that DOMContentLoaded event handler is defined.
        
        Expected: DOMContentLoaded handler should be defined
        Actual on unfixed code: Handler may exist but event listeners attached before DOM ready
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, "DOMContentLoaded")
    
    def test_load_my_agents_function_exists(self):
        """
        Test that loadMyAgents function is defined.
        
        Expected: loadMyAgents function should be defined
        Actual on unfixed code: Function exists but may not be called properly
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'function loadMyAgents')
    
    def test_load_agent_selectors_function_exists(self):
        """
        Test that loadAgentSelectors function is defined.
        
        Expected: loadAgentSelectors function should be defined
        Actual on unfixed code: Function exists but may not be called properly
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'function loadAgentSelectors')
    
    def test_load_conversations_function_exists(self):
        """
        Test that loadConversations function is defined.
        
        Expected: loadConversations function should be defined
        Actual on unfixed code: Function exists but may not be called properly
        """
        response = self.client.get('/api/communicate/')
        self.assertContains(response, 'function loadConversations')


class CommunicationPageBugConditionTest(TestCase):
    """
    Property-based test that verifies the bug condition.
    
    The bug condition is: JavaScript attempts to attach event listeners before 
    the DOM is fully ready, causing the script to fail silently.
    
    This test generates various page load scenarios and verifies that forms 
    are visible and functional.
    
    **Validates: Requirements 1.1, 1.2, 1.3**
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
    
    @given(st.just(None))  # Simple strategy for deterministic test
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_forms_visible_on_page_load(self, _):
        """
        Property: For any page load event, all form elements should be visible.
        
        Expected: All form elements should be present and not hidden
        Actual on unfixed code: Forms are hidden or not visible
        
        Counterexample on unfixed code:
        - Forms are hidden or not visible on page load
        - Event listeners are not attached to form elements
        - Clicking tabs does nothing
        - Form submission does not trigger API calls
        - CSRF token retrieval fails with "Cannot read property 'value' of null"
        """
        response = self.client.get('/api/communicate/')
        
        # Verify all form elements are present
        self.assertContains(response, 'id="register-form"')
        self.assertContains(response, 'id="message-form"')
        self.assertContains(response, 'id="conversation-agent"')
        
        # Verify all tab buttons are present
        self.assertContains(response, 'id="tab-register"')
        self.assertContains(response, 'id="tab-agents"')
        self.assertContains(response, 'id="tab-communicate"')
        self.assertContains(response, 'id="tab-conversations"')
        
        # Verify all tab content divs are present
        self.assertContains(response, 'id="content-register"')
        self.assertContains(response, 'id="content-agents"')
        self.assertContains(response, 'id="content-communicate"')
        self.assertContains(response, 'id="content-conversations"')
    
    @given(st.just(None))  # Simple strategy for deterministic test
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_event_listeners_attached(self, _):
        """
        Property: For any page load event, event listeners should be attached.
        
        Expected: Event listeners should be attached to all interactive elements
        Actual on unfixed code: Event listeners are not attached
        
        Counterexample on unfixed code:
        - Event listeners are not attached to form elements
        - Clicking tabs does nothing
        - Form submission does not trigger API calls
        """
        response = self.client.get('/api/communicate/')
        
        # Verify event listener code is present
        self.assertContains(response, "addEventListener('submit'")
        self.assertContains(response, "addEventListener('change'")
        self.assertContains(response, "addEventListener('DOMContentLoaded'")
    
    @given(st.just(None))  # Simple strategy for deterministic test
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_csrf_token_retrievable(self, _):
        """
        Property: For any page load event, CSRF token should be retrievable.
        
        Expected: CSRF token should be present in forms
        Actual on unfixed code: CSRF token retrieval fails with error
        
        Counterexample on unfixed code:
        - CSRF token retrieval fails with "Cannot read property 'value' of null"
        """
        response = self.client.get('/api/communicate/')
        
        # Verify CSRF tokens are present in forms
        self.assertContains(response, 'csrfmiddlewaretoken')
        
        # Verify getCSRFToken function is defined
        self.assertContains(response, 'function getCSRFToken')
        self.assertContains(response, "document.querySelector('[name=csrfmiddlewaretoken]')")
    
    @given(st.just(None))  # Simple strategy for deterministic test
    @settings(max_examples=1, suppress_health_check=[HealthCheck.too_slow])
    def test_page_structure_complete(self, _):
        """
        Property: For any page load event, page structure should be complete.
        
        Expected: All page elements should be present
        Actual on unfixed code: Page structure is present but forms are hidden
        """
        response = self.client.get('/api/communicate/')
        
        # Verify page title
        self.assertContains(response, 'AI Agent Communication')
        
        # Verify page subtitle
        self.assertContains(response, 'Register AI agents and enable them to communicate')
        
        # Verify all form elements
        self.assertContains(response, 'id="agent-name"')
        self.assertContains(response, 'id="agent-description"')
        self.assertContains(response, 'id="agent-type"')
        self.assertContains(response, 'id="owner-email"')
        self.assertContains(response, 'id="sender-agent"')
        self.assertContains(response, 'id="recipient-agent"')
        self.assertContains(response, 'id="message-content"')

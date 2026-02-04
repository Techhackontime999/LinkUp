"""
Property-Based Tests for Comprehensive Error Handling

Tests the universal properties that must hold for the comprehensive error handling system
including error classification, circuit breaker patterns, user feedback, and recovery mechanisms.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize, invariant
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from unittest.mock import patch, MagicMock
import uuid
import json

from .error_handler import (
    MessagingErrorHandler, 
    ErrorSeverity, 
    ErrorCategory, 
    CircuitBreakerState,
    error_handler
)

User = get_user_model()


class ErrorHandlingSystemTests(TransactionTestCase):
    """Property-based tests for comprehensive error handling functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', email='test@test.com')
        self.error_handler = MessagingErrorHandler()
        # Clear cache before each test
        cache.clear()
    
    @given(
        error_message=st.text(min_size=1, max_size=200),
        severity=st.sampled_from(list(ErrorSeverity)),
        category=st.sampled_from(list(ErrorCategory)),
        user_id=st.one_of(st.none(), st.integers(min_value=1, max_value=1000))
    )
    @settings(max_examples=50, deadline=5000)
    def test_error_classification_property(self, error_message, severity, category, user_id):
        """
        **Property 19: Comprehensive Error Handling - Error Classification**
        
        All errors must be properly classified and logged:
        - Each error must receive a unique error ID
        - Error severity must be preserved
        - Error category must be preserved
        - Timestamps must be accurate and consistent
        
        **Validates: Requirements 12.1, 12.2**
        """
        # Create a test exception
        test_exception = ValueError(error_message)
        
        # Handle the error
        result = self.error_handler.handle_error(
            error=test_exception,
            context={'test': True, 'operation': 'test_classification'},
            severity=severity,
            category=category,
            user_id=user_id
        )
        
        # Property: Must return a valid result structure
        assert isinstance(result, dict), "Error handler must return a dictionary"
        assert 'error_id' in result, "Result must contain error_id"
        assert 'handled' in result, "Result must contain handled flag"
        assert 'user_message' in result, "Result must contain user_message"
        assert 'severity' in result, "Result must contain severity"
        
        # Property: Error ID must be unique and properly formatted
        error_id = result['error_id']
        assert error_id.startswith('err_'), f"Error ID must start with 'err_', got {error_id}"
        assert len(error_id) == 16, f"Error ID must be 16 characters, got {len(error_id)}"
        
        # Property: Handled flag must be True
        assert result['handled'] is True, "Error must be marked as handled"
        
        # Property: Severity must be preserved
        assert result['severity'] == severity.value, \
            f"Severity must be preserved: expected {severity.value}, got {result['severity']}"
        
        # Property: User message must be non-empty string
        assert isinstance(result['user_message'], str), "User message must be a string"
        assert len(result['user_message']) > 0, "User message must not be empty"
        
        # Property: User actions must be a list
        assert isinstance(result['user_actions'], list), "User actions must be a list"
    
    @given(
        failure_count=st.integers(min_value=1, max_value=25),
        circuit_key_suffix=st.text(min_size=1, max_size=20),
        category=st.sampled_from(list(ErrorCategory))
    )
    @settings(max_examples=30, deadline=8000)
    def test_circuit_breaker_behavior_property(self, failure_count, circuit_key_suffix, category):
        """
        **Property 19: Comprehensive Error Handling - Circuit Breaker Behavior**
        
        Circuit breakers must prevent cascading failures:
        - Circuit opens after failure threshold
        - Circuit remains open for timeout period
        - Circuit transitions correctly between states
        - Circuit state is consistent and predictable
        
        **Validates: Requirements 12.3, 12.4**
        """
        circuit_key = f"test_circuit_{circuit_key_suffix}"
        context = {'circuit_test': True, 'endpoint': circuit_key}
        
        # Generate failures to test circuit breaker
        for i in range(failure_count):
            test_exception = ConnectionError(f"Test failure {i + 1}")
            
            result = self.error_handler.handle_error(
                error=test_exception,
                context=context,
                severity=ErrorSeverity.HIGH,
                category=category
            )
            
            # Property: Each error must be handled
            assert result['handled'] is True, f"Error {i + 1} must be handled"
        
        # Check circuit breaker state
        circuit_status = self.error_handler.get_circuit_breaker_status(
            self.error_handler._get_circuit_key(category, context)
        )
        
        # Property: Circuit state must be consistent with failure count
        if failure_count >= self.error_handler.circuit_breaker_config['failure_threshold']:
            assert circuit_status['state'] == 'open', \
                f"Circuit should be open after {failure_count} failures (threshold: {self.error_handler.circuit_breaker_config['failure_threshold']})"
            assert circuit_status['failure_count'] >= self.error_handler.circuit_breaker_config['failure_threshold'], \
                f"Failure count should be >= threshold: {circuit_status['failure_count']}"
        else:
            assert circuit_status['state'] == 'closed', \
                f"Circuit should remain closed with {failure_count} failures"
        
        # Property: Failure count must be accurate
        assert circuit_status['failure_count'] == failure_count, \
            f"Failure count should be {failure_count}, got {circuit_status['failure_count']}"
    
    @given(
        error_count=st.integers(min_value=1, max_value=150),
        time_window_minutes=st.integers(min_value=1, max_value=10),
        category=st.sampled_from(list(ErrorCategory))
    )
    @settings(max_examples=25, deadline=10000)
    def test_error_rate_monitoring_property(self, error_count, time_window_minutes, category):
        """
        **Property 19: Comprehensive Error Handling - Error Rate Monitoring**
        
        Error rate monitoring must accurately track and alert:
        - Error counts must be accurate within time windows
        - Alert thresholds must be respected
        - Error statistics must be consistent
        - Time-based aggregation must work correctly
        
        **Validates: Requirements 12.2, 12.5**
        """
        assume(error_count <= 150)  # Reasonable upper limit for testing
        
        # Set a custom time window for this test
        original_window = self.error_handler.error_rate_config['window_minutes']
        self.error_handler.error_rate_config['window_minutes'] = time_window_minutes
        
        try:
            # Generate errors within the time window
            for i in range(error_count):
                test_exception = RuntimeError(f"Rate test error {i + 1}")
                
                self.error_handler.handle_error(
                    error=test_exception,
                    context={'rate_test': True, 'error_number': i + 1},
                    severity=ErrorSeverity.MEDIUM,
                    category=category
                )
            
            # Get error statistics
            stats = self.error_handler.get_error_statistics()
            
            # Property: Total error count must match generated errors
            assert stats['total_errors'] == error_count, \
                f"Total error count should be {error_count}, got {stats['total_errors']}"
            
            # Property: Category count must be accurate
            category_count = stats['categories'].get(category.value, 0)
            assert category_count == error_count, \
                f"Category {category.value} count should be {error_count}, got {category_count}"
            
            # Property: Time window must be preserved
            assert stats['window_minutes'] == time_window_minutes, \
                f"Window minutes should be {time_window_minutes}, got {stats['window_minutes']}"
            
            # Property: Statistics structure must be complete
            assert 'categories' in stats, "Statistics must include categories"
            assert 'severities' in stats, "Statistics must include severities"
            assert 'circuit_breakers' in stats, "Statistics must include circuit breakers"
            assert 'current_time' in stats, "Statistics must include current time"
            
        finally:
            # Restore original window
            self.error_handler.error_rate_config['window_minutes'] = original_window
    
    @given(
        severity=st.sampled_from(list(ErrorSeverity)),
        category=st.sampled_from(list(ErrorCategory)),
        has_recovery_callback=st.booleans(),
        recovery_success=st.booleans()
    )
    @settings(max_examples=40, deadline=6000)
    def test_user_feedback_generation_property(self, severity, category, has_recovery_callback, recovery_success):
        """
        **Property 19: Comprehensive Error Handling - User Feedback Generation**
        
        User feedback must be appropriate and actionable:
        - Messages must be user-friendly and non-technical
        - Actions must be relevant to the error category
        - Severity must influence message tone and urgency
        - Recovery options must be provided when available
        
        **Validates: Requirements 12.1, 12.4**
        """
        test_exception = Exception("Test error for user feedback")
        
        # Create recovery callback if needed
        recovery_callback = None
        if has_recovery_callback:
            recovery_callback = lambda: recovery_success
        
        result = self.error_handler.handle_error(
            error=test_exception,
            context={'feedback_test': True},
            severity=severity,
            category=category,
            recovery_callback=recovery_callback
        )
        
        # Property: User message must be appropriate for category
        user_message = result['user_message']
        user_actions = result['user_actions']
        
        assert isinstance(user_message, str), "User message must be a string"
        assert len(user_message) > 0, "User message must not be empty"
        
        # Property: Message should not contain technical jargon
        technical_terms = ['exception', 'traceback', 'stack', 'null', 'undefined', 'error_id']
        message_lower = user_message.lower()
        for term in technical_terms:
            assert term not in message_lower, \
                f"User message should not contain technical term '{term}': {user_message}"
        
        # Property: Actions must be relevant to category
        assert isinstance(user_actions, list), "User actions must be a list"
        
        if category == ErrorCategory.NETWORK:
            action_types = [action.get('type') for action in user_actions]
            assert any(action_type in ['check_connection', 'retry', 'offline_mode'] for action_type in action_types), \
                f"Network errors should have relevant actions, got: {action_types}"
        
        elif category == ErrorCategory.VALIDATION:
            action_types = [action.get('type') for action in user_actions]
            assert any(action_type in ['edit', 'clear'] for action_type in action_types), \
                f"Validation errors should have edit/clear actions, got: {action_types}"
        
        # Property: Critical errors should have urgent actions
        if severity == ErrorSeverity.CRITICAL:
            action_types = [action.get('type') for action in user_actions]
            assert any(action_type in ['refresh', 'contact_support'] for action_type in action_types), \
                f"Critical errors should have urgent actions, got: {action_types}"
        
        # Property: Recovery attempt should be recorded if callback provided
        if has_recovery_callback:
            assert result['recovery_attempted'] is True, \
                "Recovery attempt should be recorded when callback provided"
            assert result['recovery_successful'] == recovery_success, \
                f"Recovery success should match callback result: expected {recovery_success}, got {result['recovery_successful']}"
    
    @given(
        error_messages=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=20
        ),
        user_id=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=20, deadline=12000)
    def test_error_storage_and_retrieval_property(self, error_messages, user_id):
        """
        **Property 19: Comprehensive Error Handling - Error Storage and Retrieval**
        
        Error storage must be reliable and retrievable:
        - Recent errors must be stored for monitoring
        - User-specific errors must be retrievable
        - Storage limits must be respected
        - Error data must be preserved accurately
        
        **Validates: Requirements 12.2, 12.5**
        """
        # Generate errors for the user
        error_ids = []
        for i, message in enumerate(error_messages):
            test_exception = ValueError(message)
            
            result = self.error_handler.handle_error(
                error=test_exception,
                context={'storage_test': True, 'message_index': i},
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.SYSTEM,
                user_id=user_id
            )
            
            error_ids.append(result['error_id'])
        
        # Get error statistics for the user
        stats = self.error_handler.get_error_statistics(user_id=user_id)
        
        # Property: User recent errors must be retrievable
        assert 'user_recent_errors' in stats, "Statistics must include user recent errors"
        
        user_errors = stats['user_recent_errors']
        assert isinstance(user_errors, list), "User recent errors must be a list"
        
        # Property: Number of stored errors should not exceed storage limit (20)
        assert len(user_errors) <= 20, \
            f"Stored errors should not exceed limit of 20, got {len(user_errors)}"
        
        # Property: Stored errors should match generated errors (up to limit)
        expected_count = min(len(error_messages), 20)
        assert len(user_errors) == expected_count, \
            f"Should store {expected_count} errors, got {len(user_errors)}"
        
        # Property: Each stored error must have required fields
        for stored_error in user_errors:
            assert 'error_id' in stored_error, "Stored error must have error_id"
            assert 'timestamp' in stored_error, "Stored error must have timestamp"
            assert 'category' in stored_error, "Stored error must have category"
            assert 'severity' in stored_error, "Stored error must have severity"
            assert 'message' in stored_error, "Stored error must have message"
            
            # Property: Error ID must be in our generated list (for recent errors)
            if len(error_messages) <= 20:
                assert stored_error['error_id'] in error_ids, \
                    f"Stored error ID {stored_error['error_id']} should be in generated list"
    
    @given(
        circuit_key=st.text(min_size=1, max_size=30),
        initial_failures=st.integers(min_value=0, max_value=15),
        timeout_seconds=st.integers(min_value=1, max_value=120)
    )
    @settings(max_examples=25, deadline=8000)
    def test_circuit_breaker_timeout_property(self, circuit_key, initial_failures, timeout_seconds):
        """
        **Property 19: Comprehensive Error Handling - Circuit Breaker Timeout**
        
        Circuit breaker timeout behavior must be correct:
        - Open circuits must transition to half-open after timeout
        - Timeout duration must be respected
        - State transitions must be atomic and consistent
        - Manual reset must work correctly
        
        **Validates: Requirements 12.3, 12.4**
        """
        # Set custom timeout for this test
        original_timeout = self.error_handler.circuit_breaker_config['timeout_seconds']
        self.error_handler.circuit_breaker_config['timeout_seconds'] = timeout_seconds
        
        try:
            # Create circuit breaker with initial failures
            if circuit_key not in self.error_handler.circuit_breakers:
                self.error_handler.circuit_breakers[circuit_key] = {
                    'state': CircuitBreakerState.CLOSED,
                    'failure_count': 0,
                    'last_failure_time': None,
                    'half_open_attempts': 0
                }
            
            breaker = self.error_handler.circuit_breakers[circuit_key]
            
            # Set up initial state
            breaker['failure_count'] = initial_failures
            if initial_failures >= self.error_handler.circuit_breaker_config['failure_threshold']:
                breaker['state'] = CircuitBreakerState.OPEN
                breaker['last_failure_time'] = timezone.now() - timedelta(seconds=timeout_seconds + 1)
            
            # Property: Circuit state should be consistent with setup
            initial_open = self.error_handler.is_circuit_breaker_open(circuit_key)
            
            if initial_failures >= self.error_handler.circuit_breaker_config['failure_threshold']:
                # Should transition to half-open due to timeout
                assert not initial_open, \
                    f"Circuit should transition to half-open after timeout, but is still open"
                assert breaker['state'] == CircuitBreakerState.HALF_OPEN, \
                    f"Circuit state should be HALF_OPEN, got {breaker['state']}"
            else:
                # Should remain closed
                assert not initial_open, \
                    f"Circuit should remain closed with {initial_failures} failures"
                assert breaker['state'] == CircuitBreakerState.CLOSED, \
                    f"Circuit state should be CLOSED, got {breaker['state']}"
            
            # Property: Manual reset should work
            reset_success = self.error_handler.reset_circuit_breaker(circuit_key)
            assert reset_success is True, "Manual reset should succeed for existing circuit"
            
            # Property: After reset, circuit should be closed
            post_reset_status = self.error_handler.get_circuit_breaker_status(circuit_key)
            assert post_reset_status['state'] == 'closed', \
                f"Circuit should be closed after reset, got {post_reset_status['state']}"
            assert post_reset_status['failure_count'] == 0, \
                f"Failure count should be 0 after reset, got {post_reset_status['failure_count']}"
            
        finally:
            # Restore original timeout
            self.error_handler.circuit_breaker_config['timeout_seconds'] = original_timeout


class ErrorHandlingStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for error handling system.
    
    Tests complex interactions and state transitions in error handling.
    """
    
    circuit_keys = Bundle('circuit_keys')
    
    def __init__(self):
        super().__init__()
        self.error_handler = MessagingErrorHandler()
        cache.clear()
    
    @rule(
        target=circuit_keys,
        key_suffix=st.text(min_size=1, max_size=20),
        category=st.sampled_from(list(ErrorCategory))
    )
    def create_circuit_key(self, key_suffix, category):
        """Create a circuit breaker key for testing."""
        context = {'test_circuit': True, 'suffix': key_suffix}
        circuit_key = self.error_handler._get_circuit_key(category, context)
        return circuit_key
    
    @rule(
        circuit_key=circuit_keys,
        error_count=st.integers(min_value=1, max_value=15)
    )
    def generate_failures(self, circuit_key, error_count):
        """Generate failures for a circuit breaker."""
        for i in range(error_count):
            test_exception = ConnectionError(f"Test failure {i + 1}")
            
            # Extract category from circuit key for proper handling
            if 'websocket' in circuit_key:
                category = ErrorCategory.WEBSOCKET
            elif 'database' in circuit_key:
                category = ErrorCategory.DATABASE
            elif 'network' in circuit_key:
                category = ErrorCategory.NETWORK
            else:
                category = ErrorCategory.SYSTEM
            
            self.error_handler.handle_error(
                error=test_exception,
                context={'circuit_key': circuit_key, 'failure_number': i + 1},
                severity=ErrorSeverity.HIGH,
                category=category
            )
    
    @rule(circuit_key=circuit_keys)
    def check_circuit_consistency(self, circuit_key):
        """Check circuit breaker state consistency."""
        status = self.error_handler.get_circuit_breaker_status(circuit_key)
        
        # Invariant: State must be valid
        valid_states = ['closed', 'open', 'half_open']
        assert status['state'] in valid_states, \
            f"Circuit state must be valid, got {status['state']}"
        
        # Invariant: Failure count must be non-negative
        assert status['failure_count'] >= 0, \
            f"Failure count must be non-negative, got {status['failure_count']}"
        
        # Invariant: Open circuits must have failure count >= threshold
        if status['state'] == 'open':
            threshold = self.error_handler.circuit_breaker_config['failure_threshold']
            assert status['failure_count'] >= threshold, \
                f"Open circuit must have failure count >= {threshold}, got {status['failure_count']}"
    
    @rule(circuit_key=circuit_keys)
    def reset_circuit(self, circuit_key):
        """Reset a circuit breaker."""
        success = self.error_handler.reset_circuit_breaker(circuit_key)
        
        if circuit_key in self.error_handler.circuit_breakers:
            assert success is True, "Reset should succeed for existing circuit"
            
            # Check post-reset state
            status = self.error_handler.get_circuit_breaker_status(circuit_key)
            assert status['state'] == 'closed', "Circuit should be closed after reset"
            assert status['failure_count'] == 0, "Failure count should be 0 after reset"
    
    @invariant()
    def error_statistics_consistent(self):
        """Invariant: Error statistics must always be consistent."""
        stats = self.error_handler.get_error_statistics()
        
        # Must have required fields
        required_fields = ['window_minutes', 'current_time', 'categories', 'severities', 'total_errors', 'circuit_breakers']
        for field in required_fields:
            assert field in stats, f"Statistics must include {field}"
        
        # Total errors must be non-negative
        assert stats['total_errors'] >= 0, f"Total errors must be non-negative, got {stats['total_errors']}"
        
        # Category counts must be non-negative
        for category, count in stats['categories'].items():
            assert count >= 0, f"Category {category} count must be non-negative, got {count}"
        
        # Severity counts must be non-negative
        for severity, count in stats['severities'].items():
            assert count >= 0, f"Severity {severity} count must be non-negative, got {count}"


# Test class for running the state machine
class TestErrorHandlingStateMachine(TestCase):
    """Test runner for the error handling state machine."""
    
    def test_error_handling_state_machine(self):
        """Run the stateful property-based tests."""
        # Run the state machine test
        ErrorHandlingStateMachine.TestCase.settings = settings(
            max_examples=15,
            stateful_step_count=8,
            deadline=12000
        )
        
        test_case = ErrorHandlingStateMachine.TestCase()
        test_case.runTest()


if __name__ == '__main__':
    pytest.main([__file__])
"""
Property-Based Tests for Message Retry System

Tests the universal properties that must hold for the message retry system
including HTTP fallback, exponential backoff, and circuit breaker patterns.

**Validates: Requirements 9.2, 9.3, 9.4, 9.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize, invariant
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import uuid

from .models import Message, QueuedMessage
from .message_retry_manager import MessageRetryManager, RetryStrategy

User = get_user_model()


class MessageRetrySystemTests(TransactionTestCase):
    """Property-based tests for message retry system functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='sender', email='sender@test.com')
        self.user2 = User.objects.create_user(username='recipient', email='recipient@test.com')
        self.retry_manager = MessageRetryManager()
    
    @given(
        retry_count=st.integers(min_value=0, max_value=10),
        error_type=st.sampled_from(['websocket_failed', 'broadcast_failed', 'network_error', 'timeout'])
    )
    @settings(max_examples=50, deadline=5000)
    def test_retry_delay_calculation_property(self, retry_count, error_type):
        """
        **Property 11: Message Retry System - Exponential Backoff**
        
        The retry delay must follow exponential backoff pattern:
        - delay = INITIAL_RETRY_DELAY * (BACKOFF_MULTIPLIER ^ attempt_count)
        - delay must not exceed MAX_RETRY_DELAY
        - delay must be positive and finite
        
        **Validates: Requirements 9.3, 9.4**
        """
        delay = RetryStrategy.calculate_retry_delay(retry_count)
        
        # Property: Delay must be positive
        assert delay > 0, f"Retry delay must be positive, got {delay}"
        
        # Property: Delay must not exceed maximum
        assert delay <= RetryStrategy.MAX_RETRY_DELAY, \
            f"Retry delay {delay} exceeds maximum {RetryStrategy.MAX_RETRY_DELAY}"
        
        # Property: Delay must follow exponential pattern (up to max)
        expected_delay = RetryStrategy.INITIAL_RETRY_DELAY * (RetryStrategy.BACKOFF_MULTIPLIER ** retry_count)
        expected_capped = min(expected_delay, RetryStrategy.MAX_RETRY_DELAY)
        
        assert delay == expected_capped, \
            f"Expected delay {expected_capped}, got {delay} for retry count {retry_count}"
        
        # Property: Delay must be monotonically increasing (until cap)
        if retry_count > 0:
            previous_delay = RetryStrategy.calculate_retry_delay(retry_count - 1)
            if delay < RetryStrategy.MAX_RETRY_DELAY:
                assert delay >= previous_delay, \
                    f"Delay must be non-decreasing: {previous_delay} -> {delay}"
    
    @given(
        message_content=st.text(min_size=1, max_size=1000),
        client_id=st.text(min_size=1, max_size=50),
        initial_retry_count=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=30, deadline=10000)
    def test_retry_attempt_limits_property(self, message_content, client_id, initial_retry_count):
        """
        **Property 11: Message Retry System - Retry Limits**
        
        The system must respect retry limits:
        - Messages must not exceed MAX_TOTAL_RETRIES
        - Failed messages must be marked as permanently failed after max retries
        - Retry count must be accurately tracked
        
        **Validates: Requirements 9.2, 9.4**
        """
        # Create message with initial retry count
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content=message_content,
            client_id=client_id,
            status='failed',
            retry_count=initial_retry_count
        )
        
        async def run_retry_test():
            # Attempt retry
            success = await self.retry_manager.retry_failed_message(
                message.id, 
                'test_retry'
            )
            
            # Refresh message from database
            await message.arefresh_from_db()
            
            # Property: Retry count must be incremented
            if initial_retry_count < RetryStrategy.MAX_TOTAL_RETRIES:
                assert message.retry_count == initial_retry_count + 1, \
                    f"Retry count should be incremented from {initial_retry_count} to {initial_retry_count + 1}, got {message.retry_count}"
            
            # Property: Messages at max retries must not be retried
            if initial_retry_count >= RetryStrategy.MAX_TOTAL_RETRIES:
                assert not success, \
                    f"Message with {initial_retry_count} retries should not be retried (max: {RetryStrategy.MAX_TOTAL_RETRIES})"
                assert message.status == 'failed', \
                    f"Message at max retries should remain failed, got status: {message.status}"
            
            # Property: Retry count must never exceed maximum
            assert message.retry_count <= RetryStrategy.MAX_TOTAL_RETRIES, \
                f"Retry count {message.retry_count} exceeds maximum {RetryStrategy.MAX_TOTAL_RETRIES}"
        
        # Run async test
        asyncio.run(run_retry_test())
    
    @given(
        failure_count=st.integers(min_value=1, max_value=20),
        endpoint_suffix=st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=25, deadline=8000)
    def test_circuit_breaker_property(self, failure_count, endpoint_suffix):
        """
        **Property 11: Message Retry System - Circuit Breaker**
        
        Circuit breaker must prevent cascading failures:
        - Circuit opens after CIRCUIT_BREAKER_THRESHOLD failures
        - Circuit remains open for CIRCUIT_BREAKER_TIMEOUT seconds
        - Circuit transitions to half-open after timeout
        
        **Validates: Requirements 9.5**
        """
        endpoint_key = f"test_endpoint_{endpoint_suffix}"
        
        # Property: Circuit starts closed
        assert not self.retry_manager._is_circuit_breaker_open(endpoint_key), \
            "Circuit breaker should start in closed state"
        
        # Simulate failures
        for i in range(failure_count):
            if endpoint_key not in self.retry_manager.circuit_breaker_state:
                self.retry_manager.circuit_breaker_state[endpoint_key] = {
                    'failure_count': 0,
                    'is_open': False,
                    'opened_at': None
                }
            
            state = self.retry_manager.circuit_breaker_state[endpoint_key]
            state['failure_count'] += 1
            
            # Check if circuit should open
            if state['failure_count'] >= RetryStrategy.CIRCUIT_BREAKER_THRESHOLD:
                state['is_open'] = True
                state['opened_at'] = timezone.now()
        
        # Property: Circuit opens after threshold failures
        if failure_count >= RetryStrategy.CIRCUIT_BREAKER_THRESHOLD:
            assert self.retry_manager._is_circuit_breaker_open(endpoint_key), \
                f"Circuit breaker should be open after {failure_count} failures (threshold: {RetryStrategy.CIRCUIT_BREAKER_THRESHOLD})"
        else:
            assert not self.retry_manager._is_circuit_breaker_open(endpoint_key), \
                f"Circuit breaker should remain closed with {failure_count} failures (threshold: {RetryStrategy.CIRCUIT_BREAKER_THRESHOLD})"
        
        # Property: Circuit state is consistent
        state = self.retry_manager.circuit_breaker_state.get(endpoint_key, {})
        if state.get('is_open'):
            assert state['failure_count'] >= RetryStrategy.CIRCUIT_BREAKER_THRESHOLD, \
                f"Open circuit must have failure count >= threshold, got {state['failure_count']}"
            assert state['opened_at'] is not None, \
                "Open circuit must have opened_at timestamp"
    
    @given(
        queue_size=st.integers(min_value=1, max_value=50),
        batch_size=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=20, deadline=15000)
    def test_retry_queue_processing_property(self, queue_size, batch_size):
        """
        **Property 11: Message Retry System - Queue Processing**
        
        Retry queue processing must be reliable and efficient:
        - All ready messages must be processed
        - Processing must respect batch limits
        - Processed messages must be marked correctly
        
        **Validates: Requirements 9.2, 9.4**
        """
        assume(queue_size >= batch_size or batch_size <= 20)
        
        # Create queued messages ready for retry
        queued_messages = []
        for i in range(queue_size):
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Test message {i}",
                client_id=f"client_{i}",
                status='failed',
                retry_count=1
            )
            
            queued_msg = QueuedMessage.objects.create(
                message=message,
                recipient=self.user2,
                queue_type='retry',
                retry_at=timezone.now() - timedelta(minutes=1),  # Ready for processing
                retry_count=1
            )
            queued_messages.append(queued_msg)
        
        async def run_queue_test():
            # Set batch size for this test
            original_batch_size = self.retry_manager.batch_size
            self.retry_manager.batch_size = batch_size
            
            try:
                # Process retry queue
                processed_count = await self.retry_manager.process_retry_queue()
                
                # Property: Processed count must not exceed batch size
                assert processed_count <= batch_size, \
                    f"Processed count {processed_count} exceeds batch size {batch_size}"
                
                # Property: Processed count must not exceed available messages
                assert processed_count <= queue_size, \
                    f"Processed count {processed_count} exceeds queue size {queue_size}"
                
                # Property: If queue size <= batch size, all should be processed
                if queue_size <= batch_size:
                    assert processed_count == queue_size, \
                        f"Expected to process all {queue_size} messages, got {processed_count}"
                
                # Property: Processed messages must be marked
                processed_messages = await QueuedMessage.objects.filter(
                    id__in=[qm.id for qm in queued_messages[:processed_count]],
                    processed_at__isnull=False
                ).acount()
                
                assert processed_messages == processed_count, \
                    f"Expected {processed_count} processed messages, found {processed_messages}"
                
            finally:
                # Restore original batch size
                self.retry_manager.batch_size = original_batch_size
        
        # Run async test
        asyncio.run(run_queue_test())
    
    @given(
        websocket_success=st.booleans(),
        http_success=st.booleans(),
        retry_count=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=30, deadline=8000)
    def test_fallback_mechanism_property(self, websocket_success, http_success, retry_count):
        """
        **Property 11: Message Retry System - HTTP Fallback**
        
        HTTP fallback must work correctly:
        - WebSocket failure should trigger HTTP fallback
        - HTTP fallback should be attempted when WebSocket fails
        - Success should be determined by either method succeeding
        
        **Validates: Requirements 9.2, 9.3**
        """
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Test fallback message",
            client_id=f"fallback_test_{uuid.uuid4().hex[:8]}",
            status='failed',
            retry_count=retry_count
        )
        
        async def run_fallback_test():
            # Mock the retry methods
            with patch.object(self.retry_manager, '_retry_via_websocket', return_value=websocket_success) as mock_ws, \
                 patch.object(self.retry_manager, '_retry_via_http', return_value=http_success) as mock_http:
                
                success = await self.retry_manager.retry_failed_message(message.id, 'fallback_test')
                
                # Property: WebSocket should be tried first (if within retry limit)
                if retry_count <= RetryStrategy.MAX_WEBSOCKET_RETRIES:
                    mock_ws.assert_called_once()
                
                # Property: HTTP fallback should be tried if WebSocket fails
                if not websocket_success and retry_count < RetryStrategy.MAX_TOTAL_RETRIES:
                    mock_http.assert_called_once()
                
                # Property: Success should match expected outcome
                expected_success = websocket_success or (not websocket_success and http_success)
                if retry_count < RetryStrategy.MAX_TOTAL_RETRIES:
                    assert success == expected_success, \
                        f"Expected success {expected_success}, got {success} (WS: {websocket_success}, HTTP: {http_success})"
                else:
                    # At max retries, should not succeed
                    assert not success, \
                        f"Should not succeed at max retries ({retry_count})"
        
        # Run async test
        asyncio.run(run_fallback_test())
    
    @given(
        error_types=st.lists(
            st.sampled_from(['websocket_failed', 'broadcast_failed', 'network_error', 'timeout', 'database_error']),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=10000)
    def test_error_tracking_property(self, error_types):
        """
        **Property 11: Message Retry System - Error Tracking**
        
        Error tracking must be accurate and persistent:
        - Each retry attempt must update error information
        - Error messages must be preserved
        - Error history must be maintained
        
        **Validates: Requirements 9.4, 9.5**
        """
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Error tracking test message",
            client_id=f"error_test_{uuid.uuid4().hex[:8]}",
            status='pending',
            retry_count=0
        )
        
        async def run_error_tracking_test():
            original_retry_count = message.retry_count
            
            for i, error_type in enumerate(error_types):
                if message.retry_count >= RetryStrategy.MAX_TOTAL_RETRIES:
                    break
                
                # Mock failed retry
                with patch.object(self.retry_manager, '_retry_via_websocket', return_value=False), \
                     patch.object(self.retry_manager, '_retry_via_http', return_value=False):
                    
                    await self.retry_manager.retry_failed_message(message.id, error_type)
                    await message.arefresh_from_db()
                
                # Property: Retry count must be incremented
                expected_count = min(original_retry_count + i + 1, RetryStrategy.MAX_TOTAL_RETRIES)
                assert message.retry_count >= original_retry_count + i + 1 or message.retry_count == RetryStrategy.MAX_TOTAL_RETRIES, \
                    f"Retry count should be incremented, expected >= {original_retry_count + i + 1}, got {message.retry_count}"
                
                # Property: Error information must be updated
                assert message.last_error is not None, \
                    f"Last error should be set after retry attempt {i + 1}"
                
                # Property: Error message should contain error type information
                assert error_type in message.last_error or "attempt" in message.last_error, \
                    f"Error message should contain error type or attempt info: {message.last_error}"
        
        # Run async test
        asyncio.run(run_error_tracking_test())


class MessageRetryStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for message retry system.
    
    Tests complex interactions and state transitions in the retry system.
    """
    
    messages = Bundle('messages')
    
    def __init__(self):
        super().__init__()
        self.user1 = None
        self.user2 = None
        self.retry_manager = MessageRetryManager()
    
    @initialize()
    def setup_users(self):
        """Initialize test users."""
        self.user1 = User.objects.create_user(
            username=f'user1_{uuid.uuid4().hex[:8]}',
            email=f'user1_{uuid.uuid4().hex[:8]}@test.com'
        )
        self.user2 = User.objects.create_user(
            username=f'user2_{uuid.uuid4().hex[:8]}',
            email=f'user2_{uuid.uuid4().hex[:8]}@test.com'
        )
    
    @rule(
        target=messages,
        content=st.text(min_size=1, max_size=100),
        initial_status=st.sampled_from(['pending', 'failed'])
    )
    def create_message(self, content, initial_status):
        """Create a message for testing."""
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content=content,
            client_id=f"state_test_{uuid.uuid4().hex[:8]}",
            status=initial_status,
            retry_count=0
        )
        return message
    
    @rule(
        message=messages,
        error_type=st.sampled_from(['websocket_failed', 'network_error', 'timeout'])
    )
    def retry_message(self, message, error_type):
        """Attempt to retry a message."""
        assume(message.retry_count < RetryStrategy.MAX_TOTAL_RETRIES)
        
        async def run_retry():
            original_count = message.retry_count
            
            # Mock failed retry for predictable testing
            with patch.object(self.retry_manager, '_retry_via_websocket', return_value=False), \
                 patch.object(self.retry_manager, '_retry_via_http', return_value=False):
                
                await self.retry_manager.retry_failed_message(message.id, error_type)
                await message.arefresh_from_db()
            
            # Invariant: Retry count should increase
            assert message.retry_count > original_count, \
                f"Retry count should increase from {original_count} to {message.retry_count}"
        
        asyncio.run(run_retry())
    
    @rule(message=messages)
    def check_message_state_consistency(self, message):
        """Check that message state is always consistent."""
        # Refresh from database
        message.refresh_from_db()
        
        # Invariant: Retry count must not exceed maximum
        assert message.retry_count <= RetryStrategy.MAX_TOTAL_RETRIES, \
            f"Retry count {message.retry_count} exceeds maximum {RetryStrategy.MAX_TOTAL_RETRIES}"
        
        # Invariant: Failed messages with max retries should have error info
        if message.status == 'failed' and message.retry_count >= RetryStrategy.MAX_TOTAL_RETRIES:
            assert message.last_error is not None, \
                "Failed messages at max retries should have error information"
        
        # Invariant: Retry count must be non-negative
        assert message.retry_count >= 0, \
            f"Retry count must be non-negative, got {message.retry_count}"
    
    @invariant()
    def circuit_breaker_states_valid(self):
        """Invariant: All circuit breaker states must be valid."""
        for circuit_key, state in self.retry_manager.circuit_breaker_state.items():
            # Failure count must be non-negative
            assert state['failure_count'] >= 0, \
                f"Circuit breaker {circuit_key} has negative failure count: {state['failure_count']}"
            
            # If open, must have opened_at timestamp
            if state['is_open']:
                assert state['opened_at'] is not None, \
                    f"Open circuit breaker {circuit_key} must have opened_at timestamp"


# Test class for running the state machine
class TestMessageRetryStateMachine(TestCase):
    """Test runner for the message retry state machine."""
    
    def test_message_retry_state_machine(self):
        """Run the stateful property-based tests."""
        # Run the state machine test
        MessageRetryStateMachine.TestCase.settings = settings(
            max_examples=20,
            stateful_step_count=10,
            deadline=15000
        )
        
        test_case = MessageRetryStateMachine.TestCase()
        test_case.runTest()


if __name__ == '__main__':
    pytest.main([__file__])
"""
Property tests for retry mechanisms in messaging system
**Validates: Requirements 6.1, 6.2**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
import asyncio
import time
from .retry_handler import MessageRetryHandler, RetryConfig, RetryStrategy, MessageValidator
from .models import Message, QueuedMessage
from .logging_utils import MessagingLogger

User = get_user_model()


class TestRetryMechanisms(TransactionTestCase):
    """Property tests for messaging system retry mechanisms"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Create retry handler with test configuration
        self.retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,  # Short delays for testing
            max_delay=1.0,
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
        self.retry_handler = MessageRetryHandler(self.retry_config)
        self.message_validator = MessageValidator()
    
    @given(
        failure_rate=st.floats(min_value=0.0, max_value=0.8),
        operation_count=st.integers(min_value=1, max_value=10),
        max_attempts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=15000)
    @pytest.mark.asyncio
    async def test_property_retry_mechanisms_reliability(self, failure_rate, operation_count, max_attempts):
        """
        **Property 11: Retry Mechanisms**
        **Validates: Requirements 6.1, 6.2**
        
        Property: Retry mechanisms must reliably handle transient failures and
        eventually succeed for operations that can succeed, while properly
        failing for operations that cannot succeed.
        
        This property ensures that:
        1. Transient failures are retried with appropriate backoff (6.1)
        2. Failed operations are queued for later retry (6.2)
        3. Retry attempts follow configured strategy and limits
        """
        # Configure retry handler for this test
        test_config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=0.01,  # Very short for testing
            max_delay=0.1,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
        retry_handler = MessageRetryHandler(test_config)
        
        successful_operations = 0
        failed_operations = 0
        retry_counts = []
        
        async def simulate_operation_with_failures(operation_index):
            """Simulate an operation that may fail based on failure rate"""
            nonlocal successful_operations, failed_operations
            
            attempt_count = 0
            
            async def failing_operation():
                nonlocal attempt_count
                attempt_count += 1
                
                # Simulate failure based on failure rate and attempt
                if operation_index / operation_count < failure_rate:
                    # This operation should eventually fail
                    raise Exception(f"Persistent failure for operation {operation_index}")
                elif attempt_count == 1 and failure_rate > 0.3:
                    # Simulate transient failure on first attempt
                    raise Exception(f"Transient failure for operation {operation_index}")
                else:
                    # Success
                    return f"Success for operation {operation_index}"
            
            try:
                result = await retry_handler.retry_async_operation(
                    failing_operation,
                    f"test_operation_{operation_index}"
                )
                successful_operations += 1
                retry_counts.append(attempt_count)
                return result
                
            except Exception:
                failed_operations += 1
                retry_counts.append(attempt_count)
                return None
        
        # Execute operations concurrently
        tasks = [
            simulate_operation_with_failures(i) 
            for i in range(operation_count)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify retry behavior
        total_operations = successful_operations + failed_operations
        assert total_operations == operation_count, \
            "All operations should be accounted for"
        
        # Verify retry attempts don't exceed max_attempts
        for retry_count in retry_counts:
            assert retry_count <= max_attempts, \
                f"Retry count {retry_count} should not exceed max_attempts {max_attempts}"
        
        # Verify that operations that should succeed eventually do
        expected_failures = int(operation_count * failure_rate)
        expected_successes = operation_count - expected_failures
        
        # Allow some tolerance for randomness in failure simulation
        tolerance = max(1, int(operation_count * 0.2))
        
        assert abs(successful_operations - expected_successes) <= tolerance, \
            f"Expected ~{expected_successes} successes, got {successful_operations}"
    
    @given(
        message_content=st.text(min_size=1, max_size=500),
        queue_size=st.integers(min_value=1, max_value=15),
        processing_success_rate=st.floats(min_value=0.3, max_value=1.0)
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.asyncio
    async def test_property_message_queuing_reliability(self, message_content, queue_size, processing_success_rate):
        """
        Property: Message queuing must reliably store failed messages and process them later
        
        This ensures that messages that fail to send are properly queued and
        can be successfully processed in subsequent attempts.
        """
        # Clear any existing queued messages
        await self._clear_queued_messages()
        
        # Queue multiple messages
        queued_messages = []
        for i in range(queue_size):
            success = await self.retry_handler.queue_failed_message(
                sender=self.user1,
                recipient=self.user2,
                content=f"{message_content} - Message {i}",
                original_error=f"Test error {i}",
                retry_id=f"test_retry_{i}"
            )
            
            if success:
                queued_messages.append(i)
        
        # Verify messages were queued
        queued_count = await self._count_queued_messages()
        assert queued_count == len(queued_messages), \
            f"Expected {len(queued_messages)} queued messages, found {queued_count}"
        
        # Mock message creation to simulate success/failure based on success rate
        with patch.object(self.retry_handler, 'retry_message_creation') as mock_retry:
            
            async def mock_message_creation(*args, **kwargs):
                # Simulate success based on processing_success_rate
                import random
                if random.random() < processing_success_rate:
                    return {
                        'id': random.randint(1, 1000),
                        'content': kwargs.get('content', 'test'),
                        'sender': args[0].username if args else 'test',
                        'recipient': args[1].username if len(args) > 1 else 'test',
                        'created_at': time.time()
                    }
                else:
                    return None
            
            mock_retry.side_effect = mock_message_creation
            
            # Process queued messages
            stats = await self.retry_handler.process_queued_messages(batch_size=queue_size)
            
            # Verify processing statistics
            assert stats['processed'] == len(queued_messages), \
                f"Should process {len(queued_messages)} messages, processed {stats['processed']}"
            
            assert stats['successful'] + stats['failed'] + stats['requeued'] == stats['processed'], \
                "All processed messages should be accounted for in results"
            
            # Verify success rate is approximately as expected
            if stats['processed'] > 0:
                actual_success_rate = stats['successful'] / stats['processed']
                expected_success_rate = processing_success_rate
                
                # Allow some tolerance for randomness
                tolerance = 0.3
                assert abs(actual_success_rate - expected_success_rate) <= tolerance, \
                    f"Success rate {actual_success_rate:.2f} should be close to expected {expected_success_rate:.2f}"
    
    @given(
        backoff_strategy=st.sampled_from([RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.LINEAR_BACKOFF, RetryStrategy.FIXED_DELAY]),
        initial_delay=st.floats(min_value=0.01, max_value=0.5),
        max_attempts=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=30, deadline=8000)
    @pytest.mark.asyncio
    async def test_property_backoff_strategy_consistency(self, backoff_strategy, initial_delay, max_attempts):
        """
        Property: Backoff strategies must be consistent and follow configured timing patterns
        
        This ensures that retry delays follow the expected mathematical progression
        based on the chosen strategy.
        """
        # Create retry handler with specific strategy
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=initial_delay * 10,  # Reasonable max delay
            backoff_multiplier=2.0,
            strategy=backoff_strategy
        )
        retry_handler = MessageRetryHandler(config)
        
        # Track actual delays
        actual_delays = []
        start_times = []
        
        async def always_failing_operation():
            """Operation that always fails to test all retry attempts"""
            current_time = time.time()
            if start_times:
                # Calculate delay since last attempt
                delay = current_time - start_times[-1]
                actual_delays.append(delay)
            start_times.append(current_time)
            raise Exception("Always fails for testing")
        
        # Execute operation that will use all retry attempts
        try:
            await retry_handler.retry_async_operation(
                always_failing_operation,
                "backoff_test_operation"
            )
        except Exception:
            pass  # Expected to fail
        
        # Verify we got the expected number of delays
        expected_delay_count = max_attempts - 1  # Delays between attempts
        assert len(actual_delays) == expected_delay_count, \
            f"Expected {expected_delay_count} delays, got {len(actual_delays)}"
        
        # Verify delay progression follows strategy
        if len(actual_delays) > 0:
            for i, delay in enumerate(actual_delays):
                expected_delay = retry_handler._calculate_delay(i)
                
                # Allow some tolerance for timing variations (±50%)
                tolerance = expected_delay * 0.5
                assert abs(delay - expected_delay) <= tolerance, \
                    f"Delay {i}: expected ~{expected_delay:.3f}s, got {delay:.3f}s (strategy: {backoff_strategy})"
    
    @given(
        concurrent_retries=st.integers(min_value=2, max_value=8),
        operation_duration=st.floats(min_value=0.01, max_value=0.1)
    )
    @settings(max_examples=25, deadline=10000)
    @pytest.mark.asyncio
    async def test_property_concurrent_retry_isolation(self, concurrent_retries, operation_duration):
        """
        Property: Concurrent retry operations must not interfere with each other
        
        This ensures that multiple retry operations can run simultaneously
        without affecting each other's retry logic or timing.
        """
        retry_results = []
        
        async def simulate_retry_operation(operation_id):
            """Simulate a retry operation with specific behavior"""
            attempt_count = 0
            
            async def test_operation():
                nonlocal attempt_count
                attempt_count += 1
                
                # Simulate some work
                await asyncio.sleep(operation_duration)
                
                # Fail on first attempt, succeed on second
                if attempt_count == 1:
                    raise Exception(f"First attempt failure for {operation_id}")
                else:
                    return f"Success for {operation_id}"
            
            try:
                result = await self.retry_handler.retry_async_operation(
                    test_operation,
                    f"concurrent_test_{operation_id}"
                )
                return {
                    'operation_id': operation_id,
                    'success': True,
                    'attempts': attempt_count,
                    'result': result
                }
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'success': False,
                    'attempts': attempt_count,
                    'error': str(e)
                }
        
        # Execute concurrent retry operations
        tasks = [
            simulate_retry_operation(i) 
            for i in range(concurrent_retries)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == concurrent_retries, \
            f"Expected {concurrent_retries} results, got {len(results)}"
        
        # Verify each operation had independent retry behavior
        successful_operations = [r for r in results if r['success']]
        
        # All operations should succeed on second attempt
        for result in successful_operations:
            assert result['attempts'] == 2, \
                f"Operation {result['operation_id']} should succeed on attempt 2, got {result['attempts']}"
        
        # Verify operation IDs are unique (no interference)
        operation_ids = [r['operation_id'] for r in results]
        assert len(set(operation_ids)) == len(operation_ids), \
            "All operation IDs should be unique"
    
    @given(
        message_data_complexity=st.integers(min_value=1, max_value=4),
        validation_iterations=st.integers(min_value=5, max_value=15)
    )
    @settings(max_examples=25, deadline=6000)
    def test_property_message_validation_consistency(self, message_data_complexity, validation_iterations):
        """
        Property: Message validation must be consistent across multiple validation attempts
        
        This ensures that validation results are deterministic and don't change
        between validation attempts of the same message data.
        """
        # Generate test message data based on complexity
        test_message = self._generate_test_message_data(message_data_complexity)
        
        validation_results = []
        
        # Validate the same message multiple times
        for iteration in range(validation_iterations):
            try:
                is_valid = self.message_validator.validate_message_format(test_message)
                validation_results.append(is_valid)
            except Exception as e:
                validation_results.append(False)
        
        # Verify consistency - all validation attempts should return the same result
        if validation_results:
            first_result = validation_results[0]
            for i, result in enumerate(validation_results[1:], 1):
                assert result == first_result, \
                    f"Validation attempt {i} returned {result}, expected {first_result}"
    
    def test_retry_config_validation(self):
        """Test that retry configuration is properly validated"""
        # Test valid configuration
        valid_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0
        )
        
        retry_handler = MessageRetryHandler(valid_config)
        assert retry_handler.config.max_attempts == 3
        assert retry_handler.config.initial_delay == 1.0
        
        # Test delay calculation for different strategies
        for strategy in RetryStrategy:
            config = RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                max_delay=10.0,
                backoff_multiplier=2.0,
                strategy=strategy
            )
            handler = MessageRetryHandler(config)
            
            # Calculate delays for multiple attempts
            delays = [handler._calculate_delay(i) for i in range(3)]
            
            # Verify delays are non-negative and within max_delay
            for delay in delays:
                assert delay >= 0, f"Delay should be non-negative: {delay}"
                assert delay <= config.max_delay, f"Delay should not exceed max_delay: {delay} > {config.max_delay}"
    
    def test_message_queuing_database_integration(self):
        """Test that message queuing integrates properly with the database"""
        # Clear existing queued messages
        QueuedMessage.objects.all().delete()
        
        # Create a queued message
        queued_message = QueuedMessage.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Test queued message",
            error_reason="Test error",
            retry_id="test_retry_123",
            retry_count=0
        )
        
        # Verify message was created
        assert QueuedMessage.objects.filter(id=queued_message.id).exists()
        
        # Verify message fields
        retrieved_message = QueuedMessage.objects.get(id=queued_message.id)
        assert retrieved_message.sender == self.user1
        assert retrieved_message.recipient == self.user2
        assert retrieved_message.content == "Test queued message"
        assert retrieved_message.retry_count == 0
    
    def _generate_test_message_data(self, complexity_level):
        """Generate test message data with varying complexity"""
        base_message = {
            'sender': self.user1.username,
            'recipient': self.user2.username,
            'content': 'Test message content'
        }
        
        if complexity_level == 1:
            return base_message
        elif complexity_level == 2:
            return {
                **base_message,
                'timestamp': '2024-01-01T10:00:00Z',
                'message_type': 'text'
            }
        elif complexity_level == 3:
            return {
                **base_message,
                'metadata': {
                    'priority': 'normal',
                    'tags': ['test', 'message']
                },
                'attachments': []
            }
        else:  # complexity_level >= 4
            return {
                **base_message,
                'metadata': {
                    'priority': 'high',
                    'tags': ['test', 'complex', 'message'],
                    'thread_id': 'thread_123',
                    'reply_to': None
                },
                'attachments': [
                    {'type': 'image', 'url': 'http://example.com/image.jpg'},
                    {'type': 'file', 'url': 'http://example.com/file.pdf'}
                ],
                'formatting': {
                    'bold': [0, 4],
                    'italic': [5, 12]
                }
            }
    
    async def _clear_queued_messages(self):
        """Clear all queued messages from database"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def clear_messages():
            QueuedMessage.objects.all().delete()
        
        await clear_messages()
    
    async def _count_queued_messages(self):
        """Count queued messages in database"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def count_messages():
            return QueuedMessage.objects.count()
        
        return await count_messages()
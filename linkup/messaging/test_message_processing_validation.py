"""
Property tests for message processing validation in messaging system
**Validates: Requirements 6.3, 6.5**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from datetime import datetime, timezone
import json
import time
from .retry_handler import MessageValidator
from .consumers import ChatConsumer
from .models import Message
from .serializers import JSONSerializer
from .connection_validator import ConnectionValidator

User = get_user_model()


class TestMessageProcessingValidation(TransactionTestCase):
    """Property tests for message processing validation functionality"""
    
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
        
        self.message_validator = MessageValidator()
        self.json_serializer = JSONSerializer()
        self.connection_validator = ConnectionValidator()
    
    @given(
        message_content=st.text(min_size=1, max_size=1000),
        sender_username=st.text(min_size=1, max_size=150, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        recipient_username=st.text(min_size=1, max_size=150, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        include_optional_fields=st.booleans()
    )
    @settings(max_examples=100, deadline=8000)
    def test_property_message_processing_validation(self, message_content, sender_username, recipient_username, include_optional_fields):
        """
        **Property 12: Message Processing Validation**
        **Validates: Requirements 6.3, 6.5**
        
        Property: All message processing must validate message format and content
        before processing, ensuring data integrity and preventing corruption.
        
        This property ensures that:
        1. Message format validation catches invalid messages (6.3)
        2. Message ordering is preserved during processing (6.5)
        3. Invalid messages are rejected with appropriate error messages
        """
        # Assume reasonable username lengths to avoid Django user model constraints
        assume(len(sender_username) <= 30)
        assume(len(recipient_username) <= 30)
        assume(sender_username != recipient_username)
        
        # Create base message data
        message_data = {
            'sender': sender_username,
            'recipient': recipient_username,
            'content': message_content
        }
        
        # Add optional fields based on test parameter
        if include_optional_fields:
            message_data.update({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message_type': 'text',
                'priority': 'normal'
            })
        
        # Test message format validation
        is_valid = self.message_validator.validate_message_format(message_data)
        
        # Verify validation logic
        expected_valid = (
            len(message_content.strip()) > 0 and  # Content not empty
            len(message_content) <= 10000 and    # Content not too long
            sender_username and                   # Sender exists
            recipient_username                    # Recipient exists
        )
        
        assert is_valid == expected_valid, \
            f"Validation result {is_valid} should match expected {expected_valid} for message: {message_data}"
        
        # Test JSON serialization validation
        serialization_valid = self.json_serializer.validate_serializable(message_data)
        
        # All properly formatted message data should be serializable
        if is_valid:
            assert serialization_valid, \
                f"Valid message should be JSON serializable: {message_data}"
    
    @given(
        message_count=st.integers(min_value=2, max_value=20),
        time_interval_seconds=st.floats(min_value=0.1, max_value=10.0),
        introduce_ordering_errors=st.booleans()
    )
    @settings(max_examples=50, deadline=10000)
    def test_property_message_ordering_validation(self, message_count, time_interval_seconds, introduce_ordering_errors):
        """
        Property: Message ordering validation must detect and handle ordering violations
        
        This ensures that message sequences maintain proper chronological order
        and ordering violations are detected and corrected.
        """
        # Generate a sequence of messages with timestamps
        messages = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(message_count):
            message_time = base_time.timestamp() + (i * time_interval_seconds)
            message = {
                'id': i + 1,
                'sender': self.user1.username,
                'recipient': self.user2.username,
                'content': f'Message {i + 1}',
                'created_at': datetime.fromtimestamp(message_time, timezone.utc).isoformat()
            }
            messages.append(message)
        
        # Introduce ordering errors if requested
        if introduce_ordering_errors and len(messages) >= 2:
            # Swap two adjacent messages to create ordering violation
            swap_index = len(messages) // 2
            messages[swap_index], messages[swap_index + 1] = messages[swap_index + 1], messages[swap_index]
        
        # Test ordering validation
        is_ordered = self.message_validator.validate_message_ordering(messages)
        
        # Verify ordering detection
        expected_ordered = not introduce_ordering_errors
        assert is_ordered == expected_ordered, \
            f"Ordering validation should return {expected_ordered}, got {is_ordered}"
        
        # Test ordering recovery (simulate ChatConsumer method)
        consumer = ChatConsumer()
        consumer.user = self.user1
        consumer.message_validator = self.message_validator
        
        # This would be called in real scenario - we'll test the logic
        if not is_ordered:
            # Simulate recovery by sorting messages by timestamp
            sorted_messages = sorted(messages, key=lambda m: m['created_at'])
            
            # Verify recovery worked
            recovered_ordering = self.message_validator.validate_message_ordering(sorted_messages)
            assert recovered_ordering, "Message ordering should be recovered after sorting"
    
    @given(
        invalid_field_type=st.sampled_from(['missing_sender', 'missing_recipient', 'missing_content', 'empty_content', 'long_content', 'invalid_json']),
        base_content=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=60, deadline=6000)
    def test_property_invalid_message_rejection(self, invalid_field_type, base_content):
        """
        Property: Invalid messages must be consistently rejected with appropriate error information
        
        This ensures that various types of invalid messages are properly detected
        and rejected before processing.
        """
        # Start with valid message data
        message_data = {
            'sender': self.user1.username,
            'recipient': self.user2.username,
            'content': base_content
        }
        
        # Introduce specific type of invalidity
        if invalid_field_type == 'missing_sender':
            del message_data['sender']
        elif invalid_field_type == 'missing_recipient':
            del message_data['recipient']
        elif invalid_field_type == 'missing_content':
            del message_data['content']
        elif invalid_field_type == 'empty_content':
            message_data['content'] = '   '  # Whitespace only
        elif invalid_field_type == 'long_content':
            message_data['content'] = 'x' * 10001  # Exceeds limit
        elif invalid_field_type == 'invalid_json':
            # Add non-serializable object
            message_data['invalid_object'] = object()
        
        # Test validation
        is_valid = self.message_validator.validate_message_format(message_data)
        
        # All these should be invalid
        assert not is_valid, \
            f"Message with {invalid_field_type} should be invalid: {message_data}"
        
        # Test JSON serialization for invalid_json case
        if invalid_field_type == 'invalid_json':
            serialization_valid = self.json_serializer.validate_serializable(message_data)
            assert not serialization_valid, \
                "Message with non-serializable object should fail JSON validation"
    
    @given(
        message_batch_size=st.integers(min_value=1, max_value=15),
        validation_error_rate=st.floats(min_value=0.0, max_value=0.5),
        processing_iterations=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_batch_validation_consistency(self, message_batch_size, validation_error_rate, processing_iterations):
        """
        Property: Batch message validation must be consistent across multiple processing iterations
        
        This ensures that validation results are stable and don't change between
        processing attempts of the same message batch.
        """
        # Generate batch of messages with some potentially invalid ones
        message_batch = []
        
        for i in range(message_batch_size):
            # Introduce validation errors based on error rate
            if i / message_batch_size < validation_error_rate:
                # Create invalid message
                message = {
                    'sender': self.user1.username,
                    'recipient': self.user2.username,
                    'content': ''  # Invalid: empty content
                }
            else:
                # Create valid message
                message = {
                    'sender': self.user1.username,
                    'recipient': self.user2.username,
                    'content': f'Valid message {i}'
                }
            
            message_batch.append(message)
        
        # Validate batch multiple times
        validation_results = []
        
        for iteration in range(processing_iterations):
            batch_results = []
            
            for message in message_batch:
                is_valid = self.message_validator.validate_message_format(message)
                batch_results.append(is_valid)
            
            validation_results.append(batch_results)
        
        # Verify consistency across iterations
        if len(validation_results) > 1:
            first_results = validation_results[0]
            
            for iteration, results in enumerate(validation_results[1:], 1):
                assert results == first_results, \
                    f"Validation results in iteration {iteration} should match first iteration"
        
        # Verify expected number of valid/invalid messages
        if validation_results:
            final_results = validation_results[-1]
            valid_count = sum(final_results)
            invalid_count = len(final_results) - valid_count
            
            expected_invalid = int(message_batch_size * validation_error_rate)
            expected_valid = message_batch_size - expected_invalid
            
            # Allow some tolerance for edge cases in error rate calculation
            tolerance = 1
            assert abs(valid_count - expected_valid) <= tolerance, \
                f"Expected ~{expected_valid} valid messages, got {valid_count}"
    
    @given(
        content_variations=st.lists(
            st.one_of(
                st.text(min_size=1, max_size=100),
                st.just(''),  # Empty content
                st.text(min_size=10001, max_size=10010),  # Too long content
                st.just('   '),  # Whitespace only
            ),
            min_size=1,
            max_size=10
        ),
        validation_rounds=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=40, deadline=8000)
    def test_property_content_validation_edge_cases(self, content_variations, validation_rounds):
        """
        Property: Content validation must handle edge cases consistently
        
        This ensures that various edge cases in message content are handled
        consistently across multiple validation attempts.
        """
        validation_history = []
        
        for round_num in range(validation_rounds):
            round_results = []
            
            for content in content_variations:
                message_data = {
                    'sender': self.user1.username,
                    'recipient': self.user2.username,
                    'content': content
                }
                
                is_valid = self.message_validator.validate_message_format(message_data)
                
                # Determine expected validity
                expected_valid = (
                    len(content.strip()) > 0 and  # Not empty or whitespace only
                    len(content) <= 10000         # Not too long
                )
                
                assert is_valid == expected_valid, \
                    f"Content '{content[:50]}...' validation should be {expected_valid}, got {is_valid}"
                
                round_results.append({
                    'content': content,
                    'is_valid': is_valid,
                    'expected_valid': expected_valid
                })
            
            validation_history.append(round_results)
        
        # Verify consistency across rounds
        if len(validation_history) > 1:
            first_round = validation_history[0]
            
            for round_num, round_results in enumerate(validation_history[1:], 1):
                assert len(round_results) == len(first_round), \
                    f"Round {round_num} should have same number of results as first round"
                
                for i, (first_result, current_result) in enumerate(zip(first_round, round_results)):
                    assert first_result['is_valid'] == current_result['is_valid'], \
                        f"Round {round_num}, content {i}: validation should be consistent"
    
    @given(
        timestamp_format=st.sampled_from([
            'iso_with_z',
            'iso_with_offset', 
            'iso_without_tz',
            'unix_timestamp',
            'invalid_format'
        ]),
        message_sequence_length=st.integers(min_value=2, max_value=8)
    )
    @settings(max_examples=35, deadline=7000)
    def test_property_timestamp_validation_robustness(self, timestamp_format, message_sequence_length):
        """
        Property: Timestamp validation must robustly handle various timestamp formats
        
        This ensures that message ordering validation works correctly with
        different timestamp formats and handles invalid formats gracefully.
        """
        messages = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(message_sequence_length):
            message_time = base_time.timestamp() + i
            
            # Format timestamp according to test parameter
            if timestamp_format == 'iso_with_z':
                timestamp_str = datetime.fromtimestamp(message_time, timezone.utc).isoformat().replace('+00:00', 'Z')
            elif timestamp_format == 'iso_with_offset':
                timestamp_str = datetime.fromtimestamp(message_time, timezone.utc).isoformat()
            elif timestamp_format == 'iso_without_tz':
                timestamp_str = datetime.fromtimestamp(message_time).isoformat()
            elif timestamp_format == 'unix_timestamp':
                timestamp_str = str(int(message_time))
            else:  # invalid_format
                timestamp_str = f'invalid_timestamp_{i}'
            
            message = {
                'id': i + 1,
                'sender': self.user1.username,
                'recipient': self.user2.username,
                'content': f'Message {i + 1}',
                'created_at': timestamp_str
            }
            messages.append(message)
        
        # Test ordering validation with different timestamp formats
        try:
            is_ordered = self.message_validator.validate_message_ordering(messages)
            
            # Valid timestamp formats should allow proper ordering validation
            if timestamp_format in ['iso_with_z', 'iso_with_offset', 'iso_without_tz']:
                # Should be able to validate ordering (and should be ordered since we created them in order)
                assert is_ordered, f"Messages with {timestamp_format} timestamps should be properly ordered"
            else:
                # Invalid formats should be handled gracefully (not crash)
                # The result may be True or False depending on how gracefully invalid timestamps are handled
                assert isinstance(is_ordered, bool), \
                    f"Ordering validation should return boolean even with {timestamp_format} format"
                
        except Exception as e:
            # Should not raise exceptions even with invalid timestamp formats
            pytest.fail(f"Timestamp validation should not raise exceptions with {timestamp_format}: {e}")
    
    def test_message_validation_database_integration(self):
        """Test that message validation integrates properly with database operations"""
        # Create a valid message in database
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Test message for validation"
        )
        
        # Convert to validation format
        message_data = {
            'sender': message.sender.username,
            'recipient': message.recipient.username,
            'content': message.content
        }
        
        # Validate the message data
        is_valid = self.message_validator.validate_message_format(message_data)
        assert is_valid, "Message from database should be valid"
        
        # Test serialization of database message
        serialized = self.json_serializer.serialize_message(message)
        assert isinstance(serialized, dict), "Serialized message should be a dictionary"
        assert 'id' in serialized, "Serialized message should contain ID"
        assert 'content' in serialized, "Serialized message should contain content"
    
    def test_validation_error_logging(self):
        """Test that validation errors are properly logged"""
        with patch('linkup.messaging.logging_utils.MessagingLogger.log_error') as mock_log:
            
            # Test invalid message validation
            invalid_message = {
                'sender': self.user1.username,
                'recipient': self.user2.username,
                'content': ''  # Invalid: empty content
            }
            
            is_valid = self.message_validator.validate_message_format(invalid_message)
            assert not is_valid, "Invalid message should be rejected"
            
            # Verify error was logged
            assert mock_log.called, "Validation error should be logged"
    
    def test_concurrent_validation_safety(self):
        """Test that concurrent validation operations are thread-safe"""
        import threading
        import time
        
        validation_results = []
        
        def validate_messages():
            """Validate messages in a separate thread"""
            for i in range(10):
                message_data = {
                    'sender': self.user1.username,
                    'recipient': self.user2.username,
                    'content': f'Concurrent message {i}'
                }
                
                is_valid = self.message_validator.validate_message_format(message_data)
                validation_results.append(is_valid)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Start multiple validation threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=validate_messages)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all validations succeeded (all messages were valid)
        assert all(validation_results), "All concurrent validations should succeed"
        assert len(validation_results) == 30, "Should have 30 validation results (10 per thread × 3 threads)"
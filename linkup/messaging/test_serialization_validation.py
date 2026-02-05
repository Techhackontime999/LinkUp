"""
Property-based tests for serialization validation and fallback in messaging system
**Feature: messaging-system-fixes**
"""
import json
import pytest
from hypothesis import given, strategies as st, settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from .serializers import JSONSerializer, MessagingJSONEncoder
from .models import Message, Notification, MessagingError

User = get_user_model()


class NonSerializableObject:
    """Test class that cannot be JSON serialized"""
    def __init__(self, data):
        self.data = data
        self.circular_ref = self  # Create circular reference
    
    def __str__(self):
        return f"NonSerializableObject({self.data})"


class PartiallySerializableObject:
    """Test class with some serializable and some non-serializable attributes"""
    def __init__(self, good_data, bad_data):
        self.good_data = good_data
        self.bad_data = bad_data
        self.circular = self
    
    def __str__(self):
        return f"PartiallySerializable(good={self.good_data})"


@database_sync_to_async
def cleanup_errors():
    """Clean up error logs"""
    MessagingError.objects.all().delete()


class TestSerializationValidationAndFallback(TestCase):
    """Property tests for serialization validation and fallback mechanisms"""
    
    def setUp(self):
        """Set up test environment"""
        self.serializer = JSONSerializer()
        self.encoder = MessagingJSONEncoder()
    
    @given(
        good_data=st.text(min_size=1, max_size=100),
        bad_data=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_4_serialization_validation_and_fallback(self, good_data, bad_data):
        """
        **Property 4: Serialization Validation and Fallback**
        For any data being sent via WebSocket, the system should validate JSON serializability 
        before transmission and provide fallback error messages when serialization fails.
        **Validates: Requirements 2.3, 2.4**
        """
        # Test with valid data
        valid_data = {
            'message': good_data,
            'timestamp': '2024-01-01T12:00:00',
            'user_id': 123,
            'is_active': True
        }
        
        # Validate that good data passes validation
        is_valid = self.serializer.validate_serializable(valid_data)
        assert is_valid, "Valid data should pass serialization validation"
        
        # Test JSON conversion of valid data
        json_string = self.serializer.to_json_string(valid_data)
        assert isinstance(json_string, str), "Valid data should convert to JSON string"
        assert good_data in json_string, "Original data should be present in JSON string"
        
        # Test with non-serializable data
        non_serializable = NonSerializableObject(bad_data)
        invalid_data = {
            'message': good_data,
            'problematic_object': non_serializable,
            'timestamp': '2024-01-01T12:00:00'
        }
        
        # Validate that bad data fails validation
        is_invalid = self.serializer.validate_serializable(invalid_data)
        assert not is_invalid, "Invalid data should fail serialization validation"
        
        # Test safe serialization with fallback
        safe_serialized = self.serializer.safe_serialize(invalid_data)
        assert isinstance(safe_serialized, dict), "safe_serialize should always return a dict"
        assert 'message' in safe_serialized, "Valid fields should be preserved"
        assert safe_serialized['message'] == good_data, "Valid data should be preserved"
        
        # Test that fallback JSON is still valid
        fallback_json = self.serializer.to_json_string(invalid_data)
        assert isinstance(fallback_json, str), "Fallback should produce valid JSON string"
        
        # Verify fallback JSON can be parsed
        parsed_fallback = json.loads(fallback_json)
        assert isinstance(parsed_fallback, dict), "Fallback JSON should parse to dict"
    
    @given(
        message_content=st.text(min_size=1, max_size=200),
        error_data=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_4_websocket_message_validation(self, message_content, error_data):
        """
        **Property 4: Serialization Validation and Fallback (WebSocket Messages)**
        For any WebSocket message payload, the system should validate serializability
        and provide fallback messages when validation fails.
        **Validates: Requirements 2.3, 2.4**
        """
        # Create a valid WebSocket message
        valid_message = {
            'type': 'message',
            'id': 123,
            'sender': 'user1',
            'recipient': 'user2',
            'content': message_content,
            'created_at': '2024-01-01T12:00:00Z',
            'is_read': False
        }
        
        # Test validation of valid message
        is_valid = self.serializer.validate_serializable(valid_message)
        assert is_valid, "Valid WebSocket message should pass validation"
        
        # Test JSON conversion
        json_message = self.serializer.to_json_string(valid_message)
        assert isinstance(json_message, str), "Valid message should convert to JSON"
        assert message_content in json_message, "Message content should be in JSON"
        
        # Create invalid WebSocket message with non-serializable object
        problematic_obj = NonSerializableObject(error_data)
        invalid_message = {
            'type': 'message',
            'id': 123,
            'sender': 'user1',
            'recipient': 'user2',
            'content': message_content,
            'problematic_field': problematic_obj,
            'created_at': '2024-01-01T12:00:00Z'
        }
        
        # Test validation failure
        is_invalid = self.serializer.validate_serializable(invalid_message)
        assert not is_invalid, "Invalid WebSocket message should fail validation"
        
        # Test safe serialization with fallback
        safe_message = self.serializer.safe_serialize(invalid_message)
        assert isinstance(safe_message, dict), "Safe serialization should return dict"
        assert safe_message['content'] == message_content, "Valid content should be preserved"
        assert 'type' in safe_message, "Message type should be preserved"
        
        # Test fallback JSON generation
        fallback_json = self.serializer.to_json_string(invalid_message)
        assert isinstance(fallback_json, str), "Should generate fallback JSON string"
        
        # Verify fallback is parseable
        parsed = json.loads(fallback_json)
        assert isinstance(parsed, dict), "Fallback JSON should be parseable"
    
    @pytest.mark.asyncio
    @given(
        data_size=st.integers(min_value=1, max_value=10),
        error_probability=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=30, deadline=10000)
    async def test_property_4_batch_validation_with_mixed_data(self, data_size, error_probability):
        """
        **Property 4: Serialization Validation and Fallback (Batch Processing)**
        For any batch of data with mixed serializable and non-serializable items,
        the system should validate each item and provide appropriate fallbacks.
        **Validates: Requirements 2.3, 2.4**
        """
        try:
            await cleanup_errors()
            
            # Create mixed batch of data
            batch_data = []
            expected_valid_count = 0
            
            for i in range(data_size):
                if (i / data_size) < error_probability:
                    # Create problematic data
                    item = {
                        'id': i,
                        'valid_field': f'data_{i}',
                        'problematic_object': NonSerializableObject(f'error_{i}')
                    }
                else:
                    # Create valid data
                    item = {
                        'id': i,
                        'valid_field': f'data_{i}',
                        'timestamp': '2024-01-01T12:00:00Z'
                    }
                    expected_valid_count += 1
                
                batch_data.append(item)
            
            # Test batch validation
            validation_results = []
            for item in batch_data:
                is_valid = self.serializer.validate_serializable(item)
                validation_results.append(is_valid)
            
            # Verify that some items pass and some fail validation
            valid_count = sum(validation_results)
            invalid_count = len(validation_results) - valid_count
            
            assert valid_count == expected_valid_count, f"Expected {expected_valid_count} valid items, got {valid_count}"
            assert invalid_count > 0 or error_probability == 0, "Should have some invalid items unless error_probability is 0"
            
            # Test safe serialization of entire batch
            safe_batch = self.serializer.safe_serialize(batch_data)
            assert isinstance(safe_batch, list), "Safe batch serialization should return list"
            assert len(safe_batch) == data_size, "All items should be processed"
            
            # Test that safe batch can be converted to JSON
            batch_json = self.serializer.to_json_string(safe_batch)
            assert isinstance(batch_json, str), "Safe batch should convert to JSON string"
            
            # Verify JSON is parseable
            parsed_batch = json.loads(batch_json)
            assert isinstance(parsed_batch, list), "Batch JSON should parse to list"
            assert len(parsed_batch) == data_size, "All items should be in parsed batch"
            
            # Verify each item in parsed batch is a dict
            for item in parsed_batch:
                assert isinstance(item, dict), "Each batch item should be a dict"
                assert 'id' in item, "Each item should have an id"
                assert 'valid_field' in item, "Each item should preserve valid fields"
            
        finally:
            await cleanup_errors()
    
    @given(
        error_message=st.text(min_size=1, max_size=100),
        context_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_4_error_logging_during_serialization_failure(self, error_message, context_data):
        """
        **Property 4: Serialization Validation and Fallback (Error Logging)**
        For any serialization failure, the system should log detailed error information
        while still providing a usable fallback response.
        **Validates: Requirements 2.3, 2.4**
        """
        # Create an object that will cause serialization errors
        class ProblematicObject:
            def __init__(self, message):
                self.message = message
                self.circular = self
            
            def __str__(self):
                return self.message
        
        problematic_obj = ProblematicObject(error_message)
        
        # Create data with serialization problems
        problematic_data = {
            'good_data': 'this_is_fine',
            'context': context_data,
            'problematic': problematic_obj
        }
        
        # Test that validation correctly identifies the problem
        is_valid = self.serializer.validate_serializable(problematic_data)
        assert not is_valid, "Problematic data should fail validation"
        
        # Test safe serialization provides fallback
        safe_result = self.serializer.safe_serialize(problematic_data)
        assert isinstance(safe_result, dict), "Safe serialization should return dict"
        assert 'good_data' in safe_result, "Valid fields should be preserved"
        assert safe_result['good_data'] == 'this_is_fine', "Valid data should be unchanged"
        
        # Test that fallback JSON is generated
        fallback_json = self.serializer.to_json_string(problematic_data)
        assert isinstance(fallback_json, str), "Should generate fallback JSON"
        
        # Verify fallback JSON is valid and parseable
        try:
            parsed = json.loads(fallback_json)
            assert isinstance(parsed, dict), "Fallback should parse to dict"
        except json.JSONDecodeError:
            pytest.fail("Fallback JSON should be valid and parseable")
        
        # Test encoder fallback behavior
        encoded_result = json.dumps(problematic_data, cls=MessagingJSONEncoder)
        assert isinstance(encoded_result, str), "Encoder should provide fallback"
        
        # Verify encoder result is parseable
        try:
            parsed_encoded = json.loads(encoded_result)
            assert isinstance(parsed_encoded, dict), "Encoded result should parse to dict"
        except json.JSONDecodeError:
            pytest.fail("Encoded fallback should be valid JSON")
"""
Property-based tests for connection data validation
**Validates: Requirements 3.1, 3.2, 3.3**
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import Mock, MagicMock
from .connection_validator import ConnectionValidator

User = get_user_model()


class TestConnectionDataSafety(TestCase):
    """Property tests for connection data safety validation"""
    
    def setUp(self):
        self.validator = ConnectionValidator()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @given(
        scope_data=st.one_of(
            st.none(),
            st.text(),
            st.integers(),
            st.lists(st.text()),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(
                    st.none(),
                    st.text(max_size=100),
                    st.integers(),
                    st.booleans(),
                    st.lists(st.text(max_size=50), max_size=5),
                    st.dictionaries(
                        keys=st.text(min_size=1, max_size=10),
                        values=st.text(max_size=50),
                        max_size=5
                    )
                ),
                max_size=10
            )
        )
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_connection_scope_validation_safety(self, scope_data):
        """
        **Property 5: Connection Data Safety**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        Property: The connection validator must safely handle any scope data structure
        without raising exceptions, always returning a valid response structure.
        """
        # Test that validation never crashes regardless of input
        try:
            result = self.validator.validate_connection_scope(scope_data)
            
            # Verify result structure is always consistent
            assert isinstance(result, dict), "Result must be a dictionary"
            assert 'is_valid' in result, "Result must contain is_valid field"
            assert 'errors' in result, "Result must contain errors field"
            assert 'user' in result, "Result must contain user field"
            assert 'url_route' in result, "Result must contain url_route field"
            assert 'headers' in result, "Result must contain headers field"
            assert 'query_string' in result, "Result must contain query_string field"
            
            # Verify field types are correct
            assert isinstance(result['is_valid'], bool), "is_valid must be boolean"
            assert isinstance(result['errors'], list), "errors must be a list"
            assert isinstance(result['url_route'], dict), "url_route must be a dict"
            assert isinstance(result['headers'], dict), "headers must be a dict"
            assert isinstance(result['query_string'], str), "query_string must be a string"
            
            # If scope is not a dict, validation should fail gracefully
            if not isinstance(scope_data, dict):
                assert not result['is_valid'], "Non-dict scope should be invalid"
                assert len(result['errors']) > 0, "Non-dict scope should have errors"
            
        except Exception as e:
            pytest.fail(f"Connection scope validation raised exception: {e}")
    
    @given(
        message_data=st.one_of(
            st.none(),
            st.text(),
            st.integers(),
            st.lists(st.text()),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(
                    st.none(),
                    st.text(max_size=200),
                    st.integers(),
                    st.booleans(),
                    st.lists(st.text(max_size=50), max_size=3)
                ),
                max_size=15
            )
        )
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_message_data_validation_safety(self, message_data):
        """
        **Property 5: Connection Data Safety (Message Validation)**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        Property: The message data validator must safely handle any message data structure
        without raising exceptions, always returning a valid response structure.
        """
        # Test that message validation never crashes regardless of input
        try:
            result = self.validator.validate_message_data(message_data)
            
            # Verify result structure is always consistent
            assert isinstance(result, dict), "Result must be a dictionary"
            assert 'is_valid' in result, "Result must contain is_valid field"
            assert 'errors' in result, "Result must contain errors field"
            assert 'message_type' in result, "Result must contain message_type field"
            assert 'content' in result, "Result must contain content field"
            assert 'parsed_data' in result, "Result must contain parsed_data field"
            
            # Verify field types are correct
            assert isinstance(result['is_valid'], bool), "is_valid must be boolean"
            assert isinstance(result['errors'], list), "errors must be a list"
            assert isinstance(result['parsed_data'], dict), "parsed_data must be a dict"
            
            # If message_data is not a dict, validation should fail gracefully
            if not isinstance(message_data, dict):
                assert not result['is_valid'], "Non-dict message should be invalid"
                assert len(result['errors']) > 0, "Non-dict message should have errors"
            
        except Exception as e:
            pytest.fail(f"Message data validation raised exception: {e}")
    
    @given(
        field_name=st.text(min_size=1, max_size=50),
        field_value=st.one_of(
            st.none(),
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.text(max_size=20), max_size=5),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=10),
                values=st.text(max_size=20),
                max_size=3
            )
        ),
        default_value=st.one_of(st.none(), st.text(max_size=50))
    )
    @settings(max_examples=50, deadline=3000)
    def test_property_safe_field_extraction(self, field_name, field_value, default_value):
        """
        **Property 5: Connection Data Safety (Field Extraction)**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        Property: Safe field extraction methods must handle any field value type
        without raising exceptions, returning appropriate defaults for invalid data.
        """
        test_data = {field_name: field_value}
        
        try:
            # Test string field extraction
            string_result = self.validator.safe_get_string_field(test_data, field_name, default_value)
            assert string_result is None or isinstance(string_result, str), "String field result must be None or string"
            
            # Test integer field extraction
            int_result = self.validator.safe_get_integer_field(test_data, field_name, 0)
            assert int_result is None or isinstance(int_result, int), "Integer field result must be None or int"
            
            # Test boolean field extraction
            bool_result = self.validator.safe_get_boolean_field(test_data, field_name, False)
            assert isinstance(bool_result, bool), "Boolean field result must be boolean"
            
        except Exception as e:
            pytest.fail(f"Safe field extraction raised exception: {e}")
    
    @given(
        errors=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=10
        ),
        message_type=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=50, deadline=3000)
    def test_property_error_response_generation(self, errors, message_type):
        """
        **Property 5: Connection Data Safety (Error Response)**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        Property: Error response generation must always produce valid response structure
        regardless of input error data.
        """
        try:
            response = self.validator.generate_error_response(errors, message_type)
            
            # Verify response structure
            assert isinstance(response, dict), "Error response must be a dictionary"
            assert 'type' in response, "Error response must contain type field"
            assert 'error' in response, "Error response must contain error field"
            assert 'message' in response, "Error response must contain message field"
            
            # Verify field types and values
            assert isinstance(response['type'], str), "Type must be string"
            assert isinstance(response['error'], bool), "Error must be boolean"
            assert response['error'] is True, "Error field must be True"
            assert isinstance(response['message'], str), "Message must be string"
            
            # If errors list is provided, verify it's included
            if 'errors' in response:
                assert isinstance(response['errors'], list), "Errors field must be list"
            
        except Exception as e:
            pytest.fail(f"Error response generation raised exception: {e}")
    
    def test_valid_scope_with_authenticated_user(self):
        """Test validation with properly structured scope and authenticated user"""
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.id = 1
        
        scope = {
            'user': mock_user,
            'url_route': {
                'kwargs': {'username': 'testuser'},
                'args': [],
            },
            'headers': [
                [b'host', b'localhost:8000'],
                [b'user-agent', b'test-client'],
            ],
            'query_string': b'param=value',
        }
        
        result = self.validator.validate_connection_scope(scope)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['user'] == mock_user
        assert result['url_route']['kwargs']['username'] == 'testuser'
        assert 'host' in result['headers']
        assert result['query_string'] == 'param=value'
    
    def test_valid_message_data_structure(self):
        """Test validation with properly structured message data"""
        message_data = {
            'type': 'message',
            'message': 'Hello, world!',
            'retry_id': 'retry_123'
        }
        
        result = self.validator.validate_message_data(message_data)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['message_type'] == 'message'
        assert result['content'] == 'Hello, world!'
        assert result['parsed_data']['retry_id'] == 'retry_123'
    
    def test_invalid_message_type_handling(self):
        """Test handling of invalid message types"""
        message_data = {
            'type': 'invalid_type',
            'message': 'Test message'
        }
        
        result = self.validator.validate_message_data(message_data)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert any('Invalid message type' in error for error in result['errors'])
        assert result['message_type'] == 'invalid_type'
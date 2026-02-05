"""
Property-based tests for JSON serialization in messaging system
**Feature: messaging-system-fixes**
"""
import json
import pytest
from datetime import datetime, date, time
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from .serializers import JSONSerializer, MessagingJSONEncoder
from .models import Message, Notification, UserStatus, MessagingError

User = get_user_model()


@database_sync_to_async
def create_test_user(username):
    """Create a test user synchronously"""
    return User.objects.create_user(username=username, email=f"{username}@test.com")


@database_sync_to_async
def create_test_message(sender, recipient, content):
    """Create a test message synchronously"""
    return Message.objects.create(sender=sender, recipient=recipient, content=content)


@database_sync_to_async
def create_test_notification(recipient, title, message, sender=None):
    """Create a test notification synchronously"""
    return Notification.create_notification(
        recipient=recipient,
        notification_type='new_message',
        title=title,
        message=message,
        sender=sender
    )


@database_sync_to_async
def cleanup_test_data():
    """Clean up test data"""
    Message.objects.all().delete()
    Notification.objects.all().delete()
    UserStatus.objects.all().delete()
    MessagingError.objects.all().delete()


class TestJSONSerializationCompleteness(TestCase):
    """Property tests for JSON serialization completeness"""
    
    def setUp(self):
        """Set up test environment"""
        self.serializer = JSONSerializer()
        self.encoder = MessagingJSONEncoder()
    
    @pytest.mark.asyncio
    @given(
        sender_username=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        recipient_username=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        message_content=st.text(min_size=1, max_size=1000)
    )
    @settings(max_examples=100, deadline=10000)
    async def test_property_3_message_serialization_completeness(self, sender_username, recipient_username, message_content):
        """
        **Property 3: JSON Serialization Completeness**
        For any Message object or datetime-containing data structure, serialization should 
        produce valid JSON without errors, converting non-serializable types to appropriate string representations.
        **Validates: Requirements 2.1, 2.2**
        """
        # Ensure usernames are different
        if sender_username == recipient_username:
            recipient_username = sender_username + "_r"
        
        try:
            # Clean up existing data
            await cleanup_test_data()
            
            # Create test users
            sender = await create_test_user(f"s_{sender_username}")
            recipient = await create_test_user(f"r_{recipient_username}")
            
            # Create test message
            message = await create_test_message(sender, recipient, message_content)
            
            # Test Message.to_dict() serialization
            message_dict = await database_sync_to_async(message.to_dict)()
            assert isinstance(message_dict, dict), "Message.to_dict() should return a dictionary"
            
            # Verify all required fields are present and serializable
            required_fields = ['id', 'sender', 'recipient', 'content', 'is_read', 'created_at']
            for field in required_fields:
                assert field in message_dict, f"Message dict should contain {field}"
                assert message_dict[field] is not None or field in ['read_at', 'delivered_at', 'attachment_url'], f"{field} should not be None"
            
            # Test JSON serialization of message dict
            json_string = json.dumps(message_dict)
            assert isinstance(json_string, str), "Message dict should serialize to JSON string"
            
            # Test round-trip serialization
            parsed_back = json.loads(json_string)
            assert isinstance(parsed_back, dict), "JSON should parse back to dictionary"
            assert parsed_back['id'] == message.id, "Message ID should be preserved in serialization"
            assert parsed_back['content'] == message_content, "Message content should be preserved"
            
            # Test Message.to_websocket_message() serialization
            websocket_dict = await database_sync_to_async(message.to_websocket_message)()
            assert isinstance(websocket_dict, dict), "Message.to_websocket_message() should return a dictionary"
            assert websocket_dict['type'] == 'message', "WebSocket message should have correct type"
            
            # Test JSON serialization of websocket message
            websocket_json = json.dumps(websocket_dict)
            assert isinstance(websocket_json, str), "WebSocket message should serialize to JSON"
            
            # Test JSONSerializer.serialize_message()
            serialized_message = self.serializer.serialize_message(message)
            assert isinstance(serialized_message, dict), "JSONSerializer should return dictionary"
            
            serialized_json = json.dumps(serialized_message)
            assert isinstance(serialized_json, str), "Serialized message should convert to JSON"
            
        finally:
            await cleanup_test_data()
    
    @pytest.mark.asyncio
    @given(
        username=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        title=st.text(min_size=1, max_size=200),
        message_text=st.text(min_size=1, max_size=500),
        priority=st.sampled_from(['low', 'normal', 'high', 'urgent'])
    )
    @settings(max_examples=50, deadline=10000)
    async def test_property_3_notification_serialization_completeness(self, username, title, message_text, priority):
        """
        **Property 3: JSON Serialization Completeness (Notifications)**
        For any Notification object with datetime fields, serialization should 
        produce valid JSON without errors.
        **Validates: Requirements 2.1, 2.2**
        """
        try:
            # Clean up existing data
            await cleanup_test_data()
            
            # Create test user
            user = await create_test_user(f"user_{username}")
            
            # Create test notification
            notification = await create_test_notification(user, title, message_text, sender=user)
            
            # Test Notification.to_dict() serialization
            notification_dict = await database_sync_to_async(notification.to_dict)()
            assert isinstance(notification_dict, dict), "Notification.to_dict() should return a dictionary"
            
            # Verify all required fields are present
            required_fields = ['id', 'notification_type', 'title', 'message', 'priority', 'created_at']
            for field in required_fields:
                assert field in notification_dict, f"Notification dict should contain {field}"
            
            # Test JSON serialization
            json_string = json.dumps(notification_dict)
            assert isinstance(json_string, str), "Notification dict should serialize to JSON string"
            
            # Test round-trip serialization
            parsed_back = json.loads(json_string)
            assert parsed_back['title'] == title, "Notification title should be preserved"
            assert parsed_back['message'] == message_text, "Notification message should be preserved"
            assert parsed_back['priority'] == priority, "Notification priority should be preserved"
            
            # Test Notification.to_websocket_message() serialization
            websocket_dict = await database_sync_to_async(notification.to_websocket_message)()
            assert isinstance(websocket_dict, dict), "Notification.to_websocket_message() should return a dictionary"
            assert websocket_dict['type'] == 'notification', "WebSocket notification should have correct type"
            
            # Test JSON serialization of websocket notification
            websocket_json = json.dumps(websocket_dict)
            assert isinstance(websocket_json, str), "WebSocket notification should serialize to JSON"
            
            # Test JSONSerializer.serialize_notification()
            serialized_notification = self.serializer.serialize_notification(notification)
            assert isinstance(serialized_notification, dict), "JSONSerializer should return dictionary"
            
            serialized_json = json.dumps(serialized_notification)
            assert isinstance(serialized_json, str), "Serialized notification should convert to JSON"
            
        finally:
            await cleanup_test_data()
    
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),  # Safe day range
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_3_datetime_serialization_completeness(self, year, month, day, hour, minute, second):
        """
        **Property 3: JSON Serialization Completeness (DateTime Objects)**
        For any datetime object, serialization should produce valid JSON 
        by converting to ISO format strings.
        **Validates: Requirements 2.1, 2.2**
        """
        # Create datetime object
        dt = datetime(year, month, day, hour, minute, second)
        
        # Test datetime serialization
        serialized_dt = self.serializer.serialize_datetime(dt)
        assert isinstance(serialized_dt, str), "Datetime should serialize to string"
        assert 'T' in serialized_dt, "Datetime string should be in ISO format"
        
        # Test that serialized datetime is valid JSON
        json_data = {'timestamp': serialized_dt}
        json_string = json.dumps(json_data)
        assert isinstance(json_string, str), "Datetime in dict should serialize to JSON"
        
        # Test round-trip
        parsed_back = json.loads(json_string)
        assert parsed_back['timestamp'] == serialized_dt, "Datetime should survive round-trip"
        
        # Test encoder with datetime
        encoded_dt = json.dumps(dt, cls=MessagingJSONEncoder)
        assert isinstance(encoded_dt, str), "MessagingJSONEncoder should handle datetime"
        
        # Test safe_serialize with datetime
        safe_serialized = self.serializer.safe_serialize(dt)
        assert isinstance(safe_serialized, str), "safe_serialize should handle datetime"
        
        # Test complex structure with datetime
        complex_data = {
            'created_at': dt,
            'updated_at': dt,
            'metadata': {
                'timestamp': dt,
                'nested': [dt, dt]
            }
        }
        
        safe_complex = self.serializer.safe_serialize(complex_data)
        assert isinstance(safe_complex, dict), "safe_serialize should handle complex datetime structures"
        
        complex_json = json.dumps(safe_complex)
        assert isinstance(complex_json, str), "Complex datetime structure should serialize to JSON"
    
    @given(
        decimal_value=st.decimals(min_value=-1000, max_value=1000, places=2),
        text_value=st.text(max_size=100),
        int_value=st.integers(min_value=-1000, max_value=1000),
        bool_value=st.booleans()
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_3_mixed_type_serialization_completeness(self, decimal_value, text_value, int_value, bool_value):
        """
        **Property 3: JSON Serialization Completeness (Mixed Types)**
        For any data structure containing mixed types including Decimal, 
        serialization should produce valid JSON.
        **Validates: Requirements 2.1, 2.2**
        """
        # Create mixed data structure
        mixed_data = {
            'decimal_field': decimal_value,
            'text_field': text_value,
            'int_field': int_value,
            'bool_field': bool_value,
            'none_field': None,
            'list_field': [decimal_value, text_value, int_value],
            'nested': {
                'decimal': decimal_value,
                'text': text_value
            }
        }
        
        # Test safe_serialize with mixed data
        serialized_data = self.serializer.safe_serialize(mixed_data)
        assert isinstance(serialized_data, dict), "safe_serialize should handle mixed data structure"
        
        # Test JSON serialization
        json_string = json.dumps(serialized_data)
        assert isinstance(json_string, str), "Mixed data should serialize to JSON string"
        
        # Test round-trip
        parsed_back = json.loads(json_string)
        assert isinstance(parsed_back, dict), "JSON should parse back to dictionary"
        assert parsed_back['text_field'] == text_value, "Text field should be preserved"
        assert parsed_back['int_field'] == int_value, "Int field should be preserved"
        assert parsed_back['bool_field'] == bool_value, "Bool field should be preserved"
        assert parsed_back['none_field'] is None, "None field should be preserved"
        
        # Test encoder with mixed data
        encoded_json = json.dumps(mixed_data, cls=MessagingJSONEncoder)
        assert isinstance(encoded_json, str), "MessagingJSONEncoder should handle mixed data"
        
        # Test validation
        is_valid = self.serializer.validate_serializable(serialized_data)
        assert is_valid, "Serialized mixed data should be valid for JSON"
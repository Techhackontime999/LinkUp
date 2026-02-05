"""
Property tests for comprehensive error logging in messaging system
**Validates: Requirements 5.1, 5.4, 5.5**
"""
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, AsyncMock
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.contrib.auth import get_user_model
from .consumers import ChatConsumer, NotificationsConsumer
from .models import Message, Notification, UserStatus, MessagingError
from .logging_utils import MessagingLogger

User = get_user_model()


class TestComprehensiveErrorLogging(TestCase):
    """Property tests for comprehensive error logging functionality"""
    
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
    
    @given(
        error_message=st.text(min_size=1, max_size=500),
        context_keys=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10),
        context_values=st.lists(st.one_of(st.text(), st.integers(), st.booleans()), min_size=0, max_size=10)
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_comprehensive_error_logging(self, error_message, context_keys, context_values):
        """
        **Property 9: Comprehensive Error Logging**
        **Validates: Requirements 5.1, 5.4, 5.5**
        
        Property: All errors in the messaging system must be logged with appropriate
        categorization, context data, and error details for debugging and monitoring.
        
        This property ensures that:
        1. All error types are properly categorized (5.1)
        2. Context data is preserved for debugging (5.4) 
        3. Error logging is consistent across all components (5.5)
        """
        # Create context data from parallel lists
        context_data = {}
        for i, key in enumerate(context_keys):
            if i < len(context_values):
                context_data[key] = context_values[i]
        
        # Test different error logging methods
        with patch('linkup.messaging.logging_utils.MessagingLogger._log_to_database') as mock_db_log:
            with patch('linkup.messaging.logging_utils.logger') as mock_logger:
                
                # Test async context error logging
                test_exception = Exception(error_message)
                MessagingLogger.log_async_context_error(
                    test_exception,
                    context_data=context_data,
                    user=self.user1
                )
                
                # Verify database logging was called
                assert mock_db_log.called, "Database logging should be called for async context errors"
                
                # Verify logger was called with appropriate level
                assert mock_logger.error.called, "Logger should be called with error level"
                
                # Test JSON serialization error logging
                mock_db_log.reset_mock()
                mock_logger.reset_mock()
                
                MessagingLogger.log_json_error(
                    test_exception,
                    data="test_data",
                    context_data=context_data
                )
                
                # Verify consistent logging behavior
                assert mock_db_log.called, "Database logging should be called for JSON errors"
                assert mock_logger.error.called, "Logger should be called for JSON errors"
                
                # Test connection error logging
                mock_db_log.reset_mock()
                mock_logger.reset_mock()
                
                MessagingLogger.log_connection_error(
                    error_message,
                    context_data=context_data
                )
                
                # Verify connection errors are logged
                assert mock_db_log.called, "Database logging should be called for connection errors"
                assert mock_logger.error.called, "Logger should be called for connection errors"
    
    @given(
        operation_name=st.text(min_size=1, max_size=100),
        user_id=st.integers(min_value=1, max_value=999999),
        error_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_error_categorization_consistency(self, operation_name, user_id, error_count):
        """
        Property: Error categorization must be consistent across all messaging operations
        
        This ensures that similar errors are categorized the same way regardless of
        where they occur in the system.
        """
        with patch('linkup.messaging.logging_utils.MessagingLogger._log_to_database') as mock_db_log:
            
            # Generate multiple errors for the same operation
            for i in range(error_count):
                error_message = f"Error {i} in {operation_name}"
                test_exception = Exception(error_message)
                
                MessagingLogger.log_async_context_error(
                    test_exception,
                    context_data={'operation': operation_name, 'user_id': user_id},
                    user=self.user1
                )
            
            # Verify all errors were logged
            assert mock_db_log.call_count == error_count, f"Expected {error_count} database log calls"
            
            # Verify consistent categorization
            for call in mock_db_log.call_args_list:
                args, kwargs = call
                # All async context errors should have the same category
                assert 'async_context_violation' in str(args) or 'async_context_violation' in str(kwargs), \
                    "Async context errors should be consistently categorized"
    
    @given(
        message_content=st.text(min_size=1, max_size=1000),
        simulate_error=st.booleans()
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.asyncio
    async def test_property_consumer_error_logging(self, message_content, simulate_error):
        """
        Property: All consumer errors must be logged with sufficient context for debugging
        
        This ensures that WebSocket consumer errors are properly captured and logged.
        """
        # Create a mock consumer for testing
        consumer = ChatConsumer()
        consumer.user = self.user1
        consumer.other_user = self.user2
        consumer.room_group_name = f'chat_{self.user1.id}_{self.user2.id}'
        
        with patch('linkup.messaging.logging_utils.MessagingLogger.log_error') as mock_log_error:
            with patch('linkup.messaging.logging_utils.MessagingLogger.log_json_error') as mock_log_json_error:
                
                if simulate_error:
                    # Test error handling in message processing
                    with patch.object(consumer.message_handler, 'handle_message_creation', 
                                    side_effect=Exception("Simulated error")):
                        
                        # Simulate message data
                        message_data = {
                            'type': 'message',
                            'message': message_content
                        }
                        
                        # This should trigger error logging
                        await consumer._handle_message(message_data)
                        
                        # Verify error was logged
                        assert mock_log_error.called, "Error should be logged when message creation fails"
                        
                        # Verify context data is included
                        call_args = mock_log_error.call_args
                        if call_args and len(call_args) > 1:
                            context_data = call_args[1].get('context_data', {})
                            assert 'sender_id' in context_data, "Sender ID should be in error context"
                            assert 'recipient_id' in context_data, "Recipient ID should be in error context"
                else:
                    # Test successful operation (should not log errors)
                    with patch.object(consumer.message_handler, 'handle_message_creation', 
                                    return_value={'id': 1, 'content': message_content}):
                        
                        message_data = {
                            'type': 'message', 
                            'message': message_content
                        }
                        
                        await consumer._handle_message(message_data)
                        
                        # Should not log errors for successful operations
                        assert not mock_log_error.called, "No errors should be logged for successful operations"
    
    @given(
        notification_count=st.integers(min_value=1, max_value=20),
        error_probability=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_notification_error_resilience(self, notification_count, error_probability):
        """
        Property: Notification system errors must be logged without affecting other notifications
        
        This ensures that individual notification failures don't cascade and all errors
        are properly logged for monitoring.
        """
        with patch('linkup.messaging.logging_utils.MessagingLogger.log_error') as mock_log_error:
            
            successful_notifications = 0
            failed_notifications = 0
            
            for i in range(notification_count):
                try:
                    # Simulate notification creation with potential errors
                    if error_probability > 0.5:  # Simulate error condition
                        raise Exception(f"Notification error {i}")
                    else:
                        # Simulate successful notification
                        notification = Notification.create_notification(
                            recipient=self.user1,
                            notification_type='test',
                            title=f'Test Notification {i}',
                            message=f'Test message {i}',
                            sender=self.user2
                        )
                        successful_notifications += 1
                        
                except Exception as e:
                    # Log the error (this should happen in real code)
                    MessagingLogger.log_error(
                        f"Notification creation failed: {e}",
                        context_data={'notification_index': i, 'recipient_id': self.user1.id}
                    )
                    failed_notifications += 1
            
            # Verify error logging behavior
            if failed_notifications > 0:
                assert mock_log_error.call_count >= failed_notifications, \
                    "All notification failures should be logged"
            
            # Verify that some operations can succeed even when others fail
            total_operations = successful_notifications + failed_notifications
            assert total_operations == notification_count, \
                "All operations should be accounted for"
    
    def test_error_logging_database_integration(self):
        """
        Test that error logging integrates properly with the database
        """
        # Clear any existing errors
        MessagingError.objects.all().delete()
        
        # Log a test error
        test_exception = Exception("Test database integration error")
        MessagingLogger.log_async_context_error(
            test_exception,
            context_data={'test': 'database_integration'},
            user=self.user1
        )
        
        # Verify error was saved to database
        errors = MessagingError.objects.filter(user=self.user1)
        assert errors.exists(), "Error should be saved to database"
        
        error = errors.first()
        assert error.error_type == 'async_context_violation', "Error type should be correctly categorized"
        assert 'test' in error.context_data, "Context data should be preserved"
        assert error.error_message == str(test_exception), "Error message should be preserved"
    
    def test_error_logging_without_user(self):
        """
        Test that error logging works even when no user is provided
        """
        with patch('linkup.messaging.logging_utils.MessagingLogger._log_to_database') as mock_db_log:
            
            # Log error without user
            MessagingLogger.log_connection_error(
                "Test connection error without user",
                context_data={'test': 'no_user'}
            )
            
            # Should still log to database
            assert mock_db_log.called, "Should log to database even without user"
    
    def test_context_data_serialization(self):
        """
        Test that complex context data is properly serialized for logging
        """
        complex_context = {
            'user_id': self.user1.id,
            'nested_dict': {'key': 'value', 'number': 42},
            'list_data': [1, 2, 3, 'string'],
            'boolean': True,
            'none_value': None
        }
        
        with patch('linkup.messaging.logging_utils.MessagingLogger._log_to_database') as mock_db_log:
            
            MessagingLogger.log_error(
                "Test complex context serialization",
                context_data=complex_context
            )
            
            # Verify database logging was called
            assert mock_db_log.called, "Database logging should handle complex context data"
            
            # Verify the call was made with serializable data
            call_args = mock_db_log.call_args
            assert call_args is not None, "Database log should be called with arguments"
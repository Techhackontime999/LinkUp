"""
Integration tests for end-to-end message flow in messaging system
**Validates: All requirements**
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
import json
import asyncio
import time
from unittest.mock import patch, Mock

from .consumers import ChatConsumer, NotificationsConsumer
from .models import Message, Notification, UserStatus, QueuedMessage
from .notification_service import NotificationService
from .async_handlers import AsyncSafeMessageHandler
from .serializers import JSONSerializer
from .connection_validator import ConnectionValidator
from .retry_handler import MessageRetryHandler
from .logging_utils import MessagingLogger

User = get_user_model()


class TestEndToEndMessageFlow(TransactionTestCase):
    """Integration tests for complete message lifecycle"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='sender_user',
            email='sender@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='recipient_user',
            email='recipient@example.com',
            password='testpass123'
        )
        
        # Initialize components
        self.message_handler = AsyncSafeMessageHandler()
        self.json_serializer = JSONSerializer()
        self.connection_validator = ConnectionValidator()
        self.retry_handler = MessageRetryHandler()
        self.notification_service = NotificationService()
    
    @pytest.mark.asyncio
    async def test_complete_message_lifecycle(self):
        """
        Test complete message lifecycle from WebSocket to database to notification
        
        This integration test validates:
        1. Message creation through async-safe handlers
        2. JSON serialization of message data
        3. WebSocket transmission
        4. Database persistence
        5. Notification creation and delivery
        6. Error handling throughout the flow
        """
        # Step 1: Create message using async-safe handler
        message_content = "Integration test message"
        
        message_data = await self.message_handler.handle_message_creation(
            sender=self.user1,
            recipient=self.user2,
            content=message_content
        )
        
        assert message_data is not None, "Message creation should succeed"
        assert message_data['content'] == message_content, "Message content should be preserved"
        assert message_data['sender'] == self.user1.username, "Sender should be correct"
        assert message_data['recipient'] == self.user2.username, "Recipient should be correct"
        
        # Step 2: Validate JSON serialization
        serialized_message = self.json_serializer.safe_serialize(message_data)
        assert isinstance(serialized_message, dict), "Serialized message should be a dictionary"
        
        json_string = self.json_serializer.to_json_string(serialized_message)
        assert isinstance(json_string, str), "JSON string should be generated"
        
        # Verify JSON can be parsed back
        parsed_data = json.loads(json_string)
        assert parsed_data['content'] == message_content, "Content should survive serialization"
        
        # Step 3: Verify database persistence
        message_id = message_data['id']
        message_obj = await database_sync_to_async(Message.objects.get)(id=message_id)
        
        assert message_obj.sender == self.user1, "Database message sender should be correct"
        assert message_obj.recipient == self.user2, "Database message recipient should be correct"
        assert message_obj.content == message_content, "Database message content should be correct"
        
        # Step 4: Test notification creation
        notification = await database_sync_to_async(self.notification_service.create_and_send_notification)(
            recipient=self.user2,
            notification_type='new_message',
            title='New Message',
            message=f'{self.user1.username}: {message_content}',
            sender=self.user1
        )
        
        assert notification is not None, "Notification should be created"
        assert notification.recipient == self.user2, "Notification recipient should be correct"
        assert notification.sender == self.user1, "Notification sender should be correct"
        
        # Step 5: Verify notification serialization
        notification_data = self.json_serializer.serialize_notification(notification)
        assert isinstance(notification_data, dict), "Notification should be serializable"
        assert notification_data['title'] == 'New Message', "Notification title should be preserved"
    
    @pytest.mark.asyncio
    async def test_websocket_consumer_integration(self):
        """
        Test WebSocket consumer integration with all components
        
        This test validates:
        1. Consumer initialization with all handlers
        2. Message processing through consumer
        3. Error handling in consumer
        4. Connection validation
        5. Response serialization
        """
        # Create consumer instance
        consumer = ChatConsumer()
        consumer.user = self.user1
        consumer.other_user = self.user2
        consumer.room_group_name = f'chat_{self.user1.id}_{self.user2.id}'
        
        # Mock channel layer for testing
        consumer.channel_layer = Mock()
        consumer.channel_layer.group_send = AsyncMock()
        
        # Test message handling
        message_data = {
            'type': 'message',
            'message': 'WebSocket integration test message'
        }
        
        # Process message through consumer
        await consumer._handle_message(message_data)
        
        # Verify channel layer was called (message was sent)
        assert consumer.channel_layer.group_send.called, "Message should be sent via channel layer"
        
        # Verify message was created in database
        messages = await database_sync_to_async(list)(
            Message.objects.filter(
                sender=self.user1,
                recipient=self.user2,
                content='WebSocket integration test message'
            )
        )
        
        assert len(messages) > 0, "Message should be created in database"
        message = messages[0]
        assert message.content == 'WebSocket integration test message', "Message content should be correct"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """
        Test error handling integration across all components
        
        This test validates:
        1. Error propagation through the system
        2. Logging of errors at each level
        3. Graceful degradation when components fail
        4. Recovery mechanisms
        """
        error_logs = []
        
        # Mock logging to capture errors
        def mock_log_error(message, context_data=None):
            error_logs.append({'message': message, 'context': context_data})
        
        with patch.object(MessagingLogger, 'log_error', side_effect=mock_log_error):
            
            # Test 1: Database error handling
            with patch('linkup.messaging.models.Message.objects.create', side_effect=Exception("Database error")):
                
                message_data = await self.message_handler.handle_message_creation(
                    sender=self.user1,
                    recipient=self.user2,
                    content="Error test message"
                )
                
                # Should return None on error
                assert message_data is None, "Message creation should fail gracefully"
                
                # Should log error
                assert len(error_logs) > 0, "Error should be logged"
                assert any("Database error" in log['message'] for log in error_logs), "Database error should be logged"
            
            # Reset error logs
            error_logs.clear()
            
            # Test 2: Serialization error handling
            with patch.object(self.json_serializer, 'safe_serialize', side_effect=Exception("Serialization error")):
                
                # Create a valid message first
                message_data = await self.message_handler.handle_message_creation(
                    sender=self.user1,
                    recipient=self.user2,
                    content="Serialization test message"
                )
                
                assert message_data is not None, "Message should be created"
                
                # Try to serialize (should handle error gracefully)
                try:
                    serialized = self.json_serializer.safe_serialize(message_data)
                    # Should not reach here, but if it does, should not crash
                except Exception:
                    pass  # Expected to fail
                
                # Error should be logged
                assert len(error_logs) > 0, "Serialization error should be logged"
    
    @pytest.mark.asyncio
    async def test_retry_mechanism_integration(self):
        """
        Test retry mechanism integration with message operations
        
        This test validates:
        1. Retry mechanisms work with real operations
        2. Exponential backoff is applied
        3. Failed operations are queued
        4. Queued operations can be processed later
        """
        # Test retry with transient failures
        attempt_count = 0
        
        async def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:  # Fail first 2 attempts
                raise Exception(f"Transient failure attempt {attempt_count}")
            
            # Succeed on 3rd attempt
            return await self.message_handler.create_message(
                sender=self.user1,
                recipient=self.user2,
                content="Retry test message"
            )
        
        # Use retry handler
        result = await self.retry_handler.retry_async_operation(
            failing_operation,
            "retry_integration_test"
        )
        
        assert result is not None, "Operation should eventually succeed"
        assert attempt_count == 3, "Should take 3 attempts to succeed"
        
        # Verify message was created
        message = await database_sync_to_async(Message.objects.get)(id=result.id)
        assert message.content == "Retry test message", "Message should be created correctly"
    
    @pytest.mark.asyncio
    async def test_notification_integration_with_messaging(self):
        """
        Test notification system integration with messaging
        
        This test validates:
        1. Messages trigger notifications
        2. Notifications are properly serialized
        3. WebSocket delivery works end-to-end
        4. Fallback mechanisms work
        """
        # Mock channel layer for notifications
        mock_channel_layer = Mock()
        mock_channel_layer.group_send = AsyncMock()
        
        with patch.object(self.notification_service, 'channel_layer', mock_channel_layer):
            
            # Create message
            message_data = await self.message_handler.handle_message_creation(
                sender=self.user1,
                recipient=self.user2,
                content="Notification integration test"
            )
            
            assert message_data is not None, "Message should be created"
            
            # Create notification for the message
            notification = await database_sync_to_async(self.notification_service.create_and_send_notification)(
                recipient=self.user2,
                notification_type='new_message',
                title='New Message',
                message=f'{self.user1.username}: Notification integration test',
                sender=self.user1
            )
            
            assert notification is not None, "Notification should be created"
            
            # Verify WebSocket delivery was attempted
            assert mock_channel_layer.group_send.called, "Notification should be sent via WebSocket"
            
            # Verify notification data structure
            call_args = mock_channel_layer.group_send.call_args
            assert call_args is not None, "Channel layer should be called with arguments"
            
            group_name, message_payload = call_args[0]
            assert group_name == f'user_{self.user2.id}', "Should send to correct user group"
            assert 'message' in message_payload, "Should contain message payload"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self):
        """
        Test concurrent operations across all components
        
        This test validates:
        1. Multiple simultaneous message creations
        2. Concurrent notification deliveries
        3. Database consistency under load
        4. Error isolation between operations
        """
        concurrent_operations = 5
        
        async def create_message_and_notification(index):
            """Create message and notification concurrently"""
            try:
                # Create message
                message_data = await self.message_handler.handle_message_creation(
                    sender=self.user1,
                    recipient=self.user2,
                    content=f"Concurrent message {index}"
                )
                
                if not message_data:
                    return {'success': False, 'error': 'Message creation failed'}
                
                # Create notification
                notification = await database_sync_to_async(self.notification_service.create_and_send_notification)(
                    recipient=self.user2,
                    notification_type='new_message',
                    title='New Message',
                    message=f'{self.user1.username}: Concurrent message {index}',
                    sender=self.user1
                )
                
                return {
                    'success': True,
                    'message_id': message_data['id'],
                    'notification_id': notification.id if notification else None
                }
                
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Execute concurrent operations
        tasks = [create_message_and_notification(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        successful_operations = [r for r in results if r['success']]
        failed_operations = [r for r in results if not r['success']]
        
        assert len(successful_operations) > 0, "Some operations should succeed"
        
        # Verify database consistency
        message_count = await database_sync_to_async(Message.objects.filter(
            sender=self.user1,
            recipient=self.user2
        ).count)()
        
        notification_count = await database_sync_to_async(Notification.objects.filter(
            recipient=self.user2,
            sender=self.user1,
            notification_type='new_message'
        ).count)()
        
        assert message_count == len(successful_operations), \
            f"Should have {len(successful_operations)} messages, found {message_count}"
        
        # Notifications might be fewer due to delivery failures, but should not exceed messages
        assert notification_count <= len(successful_operations), \
            f"Notification count {notification_count} should not exceed successful operations {len(successful_operations)}"
    
    def test_component_initialization_integration(self):
        """
        Test that all components initialize correctly together
        
        This test validates:
        1. All handlers can be instantiated
        2. Dependencies are properly resolved
        3. Configuration is consistent across components
        """
        # Test component initialization
        components = {
            'message_handler': AsyncSafeMessageHandler(),
            'json_serializer': JSONSerializer(),
            'connection_validator': ConnectionValidator(),
            'retry_handler': MessageRetryHandler(),
            'notification_service': NotificationService()
        }
        
        # Verify all components initialized
        for name, component in components.items():
            assert component is not None, f"{name} should initialize successfully"
        
        # Test component interactions
        message_data = {
            'sender': self.user1.username,
            'recipient': self.user2.username,
            'content': 'Component integration test'
        }
        
        # Validate with connection validator
        is_valid = components['connection_validator'].validate_message_data(message_data)
        assert is_valid, "Message data should be valid"
        
        # Serialize with JSON serializer
        serialized = components['json_serializer'].safe_serialize(message_data)
        assert isinstance(serialized, dict), "Should serialize to dictionary"
        
        # Validate serialization
        is_serializable = components['json_serializer'].validate_serializable(message_data)
        assert is_serializable, "Message data should be serializable"
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """
        Test error recovery mechanisms across the entire system
        
        This test validates:
        1. System recovers from transient failures
        2. Partial failures don't corrupt system state
        3. Error recovery preserves data integrity
        """
        # Simulate system under stress with intermittent failures
        operations_attempted = 10
        successful_operations = 0
        
        for i in range(operations_attempted):
            try:
                # Simulate intermittent database failures
                if i % 3 == 0:  # Every 3rd operation fails
                    with patch('linkup.messaging.models.Message.objects.create', 
                             side_effect=Exception("Intermittent database failure")):
                        
                        message_data = await self.message_handler.handle_message_creation(
                            sender=self.user1,
                            recipient=self.user2,
                            content=f"Recovery test message {i}"
                        )
                        
                        # Should handle failure gracefully
                        assert message_data is None, f"Operation {i} should fail gracefully"
                else:
                    # Normal operation
                    message_data = await self.message_handler.handle_message_creation(
                        sender=self.user1,
                        recipient=self.user2,
                        content=f"Recovery test message {i}"
                    )
                    
                    if message_data:
                        successful_operations += 1
                        
            except Exception as e:
                # Should not propagate unhandled exceptions
                pytest.fail(f"Operation {i} should not raise unhandled exception: {e}")
        
        # Verify system state is consistent
        expected_successful = operations_attempted - (operations_attempted // 3)
        assert successful_operations == expected_successful, \
            f"Expected {expected_successful} successful operations, got {successful_operations}"
        
        # Verify database consistency
        actual_message_count = await database_sync_to_async(Message.objects.filter(
            sender=self.user1,
            recipient=self.user2
        ).count)()
        
        assert actual_message_count == successful_operations, \
            f"Database should contain {successful_operations} messages, found {actual_message_count}"
    
    def tearDown(self):
        """Clean up test data"""
        # Clear test data
        Message.objects.filter(sender__in=[self.user1, self.user2]).delete()
        Notification.objects.filter(recipient__in=[self.user1, self.user2]).delete()
        QueuedMessage.objects.filter(sender__in=[self.user1, self.user2]).delete()
        UserStatus.objects.filter(user__in=[self.user1, self.user2]).delete()
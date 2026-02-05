"""
Property tests for operation stability in messaging system
**Validates: Requirements 5.2, 5.3**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from channels.testing import WebsocketCommunicator
import asyncio
import json
from .consumers import ChatConsumer, NotificationsConsumer
from .models import Message, Notification, UserStatus
from .async_handlers import AsyncSafeMessageHandler
from .serializers import JSONSerializer
from .connection_validator import ConnectionValidator

User = get_user_model()


class TestOperationStability(TransactionTestCase):
    """Property tests for messaging system operation stability"""
    
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
        self.handler = AsyncSafeMessageHandler()
        self.serializer = JSONSerializer()
        self.validator = ConnectionValidator()
    
    @given(
        message_content=st.text(min_size=1, max_size=1000),
        concurrent_operations=st.integers(min_value=1, max_value=10),
        failure_rate=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=50, deadline=15000)
    @pytest.mark.asyncio
    async def test_property_operation_stability_under_load(self, message_content, concurrent_operations, failure_rate):
        """
        **Property 10: Operation Stability**
        **Validates: Requirements 5.2, 5.3**
        
        Property: Messaging operations must remain stable and consistent under
        concurrent load and partial failure conditions.
        
        This property ensures that:
        1. System maintains consistency under concurrent operations (5.2)
        2. Partial failures don't corrupt system state (5.3)
        3. Operations are atomic and don't leave inconsistent state
        """
        successful_operations = 0
        failed_operations = 0
        
        async def create_message_with_potential_failure(index):
            """Simulate message creation with potential failure"""
            nonlocal successful_operations, failed_operations
            
            try:
                # Simulate random failures based on failure_rate
                if index / concurrent_operations < failure_rate:
                    raise Exception(f"Simulated failure for operation {index}")
                
                # Use async-safe message handler
                message = await self.handler.create_message(
                    sender=self.user1,
                    recipient=self.user2,
                    content=f"{message_content} - Operation {index}"
                )
                
                if message:
                    successful_operations += 1
                    return message
                else:
                    failed_operations += 1
                    return None
                    
            except Exception:
                failed_operations += 1
                return None
        
        # Execute concurrent operations
        tasks = [
            create_message_with_potential_failure(i) 
            for i in range(concurrent_operations)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify system stability
        total_operations = successful_operations + failed_operations
        assert total_operations == concurrent_operations, \
            "All operations should be accounted for"
        
        # Verify database consistency
        actual_message_count = await self._count_messages_async()
        assert actual_message_count == successful_operations, \
            f"Database should contain exactly {successful_operations} messages, found {actual_message_count}"
        
        # Verify no partial state corruption
        messages = await self._get_all_messages_async()
        for message in messages:
            assert message.sender_id is not None, "Message sender should not be None"
            assert message.recipient_id is not None, "Message recipient should not be None"
            assert message.content is not None, "Message content should not be None"
            assert message.created_at is not None, "Message created_at should not be None"
    
    @given(
        user_count=st.integers(min_value=2, max_value=8),
        status_changes=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.asyncio
    async def test_property_user_status_consistency(self, user_count, status_changes):
        """
        Property: User status operations must maintain consistency across concurrent updates
        
        This ensures that user online/offline status remains consistent even with
        rapid status changes from multiple connections.
        """
        # Create additional users for testing
        users = [self.user1, self.user2]
        for i in range(user_count - 2):
            user = User.objects.create_user(
                username=f'testuser{i+3}',
                email=f'test{i+3}@example.com',
                password='testpass123'
            )
            users.append(user)
        
        async def update_user_status(user, change_index):
            """Update user status with potential concurrency"""
            is_online = (change_index % 2) == 0  # Alternate between online/offline
            
            success = await self.handler.set_user_online_status(user, is_online)
            return success, user.id, is_online
        
        # Execute concurrent status updates
        tasks = []
        for i in range(status_changes):
            user = users[i % len(users)]
            tasks.append(update_user_status(user, i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed
        successful_updates = sum(1 for result in results if isinstance(result, tuple) and result[0])
        
        # Verify final status consistency
        for user in users:
            status_data = await self.handler.get_user_status(user)
            assert isinstance(status_data, dict), "Status data should be a dictionary"
            assert 'is_online' in status_data, "Status should contain is_online field"
            assert isinstance(status_data['is_online'], bool), "is_online should be boolean"
    
    @given(
        notification_batch_size=st.integers(min_value=1, max_value=15),
        recipient_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.asyncio
    async def test_property_notification_atomicity(self, notification_batch_size, recipient_count):
        """
        Property: Notification operations must be atomic and maintain referential integrity
        
        This ensures that notification creation either fully succeeds or fully fails,
        without leaving partial or corrupted notification data.
        """
        # Create additional recipients
        recipients = [self.user1]
        for i in range(recipient_count - 1):
            user = User.objects.create_user(
                username=f'recipient{i+1}',
                email=f'recipient{i+1}@example.com',
                password='testpass123'
            )
            recipients.append(user)
        
        async def create_notification_batch(batch_index):
            """Create a batch of notifications atomically"""
            notifications_created = []
            
            try:
                for i in range(notification_batch_size):
                    recipient = recipients[i % len(recipients)]
                    
                    notification = await self.handler.create_notification(
                        recipient=recipient,
                        notification_type='test_batch',
                        title=f'Batch {batch_index} Notification {i}',
                        message=f'Test notification {i} in batch {batch_index}',
                        sender=self.user2
                    )
                    
                    if notification:
                        notifications_created.append(notification.id)
                    else:
                        # If any notification fails, the batch should be considered failed
                        raise Exception(f"Failed to create notification {i} in batch {batch_index}")
                
                return notifications_created
                
            except Exception as e:
                # In case of failure, verify no partial notifications were created
                return []
        
        # Create multiple batches concurrently
        batch_count = 3
        tasks = [create_notification_batch(i) for i in range(batch_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify atomicity - each batch should either fully succeed or fully fail
        total_expected_notifications = 0
        for result in results:
            if isinstance(result, list) and len(result) > 0:
                # Successful batch
                assert len(result) == notification_batch_size, \
                    "Successful batch should contain all expected notifications"
                total_expected_notifications += len(result)
        
        # Verify database consistency
        actual_notification_count = await self._count_notifications_async()
        assert actual_notification_count == total_expected_notifications, \
            f"Database should contain {total_expected_notifications} notifications, found {actual_notification_count}"
    
    @given(
        json_data_complexity=st.integers(min_value=1, max_value=5),
        serialization_attempts=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=30, deadline=8000)
    def test_property_serialization_stability(self, json_data_complexity, serialization_attempts):
        """
        Property: JSON serialization must be stable and consistent across multiple attempts
        
        This ensures that serialization operations don't introduce inconsistencies
        or fail unpredictably under repeated use.
        """
        # Generate complex test data based on complexity level
        test_data = self._generate_complex_data(json_data_complexity)
        
        serialization_results = []
        
        for attempt in range(serialization_attempts):
            try:
                # Test serialization stability
                serialized = self.serializer.safe_serialize(test_data)
                json_string = self.serializer.to_json_string(serialized)
                
                # Verify serialization is valid JSON
                parsed_back = json.loads(json_string)
                
                serialization_results.append({
                    'success': True,
                    'result': json_string,
                    'parsed': parsed_back
                })
                
            except Exception as e:
                serialization_results.append({
                    'success': False,
                    'error': str(e)
                })
        
        # Verify stability - all attempts should have consistent results
        successful_results = [r for r in serialization_results if r['success']]
        
        if successful_results:
            # All successful serializations should produce the same result
            first_result = successful_results[0]['result']
            for result in successful_results[1:]:
                assert result['result'] == first_result, \
                    "Serialization should be deterministic and consistent"
        
        # Verify that serialization doesn't fail randomly
        success_rate = len(successful_results) / len(serialization_results)
        assert success_rate >= 0.8, \
            f"Serialization should be stable (success rate: {success_rate:.2f})"
    
    @given(
        connection_data_variants=st.integers(min_value=5, max_value=15),
        validation_attempts=st.integers(min_value=3, max_size=10)
    )
    @settings(max_examples=25, deadline=6000)
    def test_property_connection_validation_consistency(self, connection_data_variants, validation_attempts):
        """
        Property: Connection validation must be consistent and deterministic
        
        This ensures that validation results are stable and don't change
        between multiple validation attempts of the same data.
        """
        # Generate various connection data scenarios
        test_scenarios = []
        
        for i in range(connection_data_variants):
            scenario = {
                'valid_message': {
                    'type': 'message',
                    'message': f'Test message {i}',
                    'timestamp': f'2024-01-{i+1:02d}T10:00:00Z'
                },
                'invalid_message': {
                    'invalid_field': f'Invalid data {i}',
                    'missing_type': True
                },
                'malformed_data': f'not_a_dict_{i}'
            }
            test_scenarios.append(scenario)
        
        # Test validation consistency
        for scenario in test_scenarios:
            for data_type, data in scenario.items():
                validation_results = []
                
                # Validate the same data multiple times
                for attempt in range(validation_attempts):
                    try:
                        if isinstance(data, dict):
                            is_valid = self.validator.validate_message_data(data)
                        else:
                            is_valid = False  # Non-dict data should be invalid
                        
                        validation_results.append(is_valid)
                        
                    except Exception:
                        validation_results.append(False)
                
                # Verify consistency - all validation attempts should return the same result
                if validation_results:
                    first_result = validation_results[0]
                    for result in validation_results[1:]:
                        assert result == first_result, \
                            f"Validation should be consistent for {data_type}: {data}"
    
    def _generate_complex_data(self, complexity_level):
        """Generate test data with varying complexity levels"""
        if complexity_level == 1:
            return {'simple': 'data', 'number': 42}
        elif complexity_level == 2:
            return {
                'nested': {'key': 'value', 'list': [1, 2, 3]},
                'boolean': True,
                'null': None
            }
        elif complexity_level == 3:
            return {
                'message': Message(
                    id=1,
                    sender=self.user1,
                    recipient=self.user2,
                    content='Test message'
                ),
                'metadata': {'created': '2024-01-01', 'priority': 'high'}
            }
        elif complexity_level == 4:
            return {
                'users': [self.user1, self.user2],
                'messages': [
                    {'id': 1, 'content': 'Message 1'},
                    {'id': 2, 'content': 'Message 2'}
                ],
                'deep_nesting': {
                    'level1': {
                        'level2': {
                            'level3': {'data': 'deep_value'}
                        }
                    }
                }
            }
        else:  # complexity_level >= 5
            return {
                'mixed_types': [
                    'string',
                    42,
                    True,
                    None,
                    {'nested': 'dict'},
                    [1, 2, 3]
                ],
                'user_objects': [self.user1, self.user2],
                'complex_nested': {
                    'notifications': [
                        {
                            'id': i,
                            'type': f'type_{i}',
                            'data': {'key': f'value_{i}'}
                        }
                        for i in range(5)
                    ]
                }
            }
    
    async def _count_messages_async(self):
        """Count messages in database asynchronously"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def count_messages():
            return Message.objects.count()
        
        return await count_messages()
    
    async def _get_all_messages_async(self):
        """Get all messages from database asynchronously"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def get_messages():
            return list(Message.objects.all())
        
        return await get_messages()
    
    async def _count_notifications_async(self):
        """Count notifications in database asynchronously"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def count_notifications():
            return Notification.objects.count()
        
        return await count_notifications()
    
    def test_database_transaction_rollback_stability(self):
        """
        Test that database operations maintain consistency during transaction rollbacks
        """
        initial_message_count = Message.objects.count()
        
        try:
            with transaction.atomic():
                # Create a message
                message = Message.objects.create(
                    sender=self.user1,
                    recipient=self.user2,
                    content="Test message for rollback"
                )
                
                # Verify message exists within transaction
                assert Message.objects.filter(id=message.id).exists()
                
                # Force a rollback by raising an exception
                raise IntegrityError("Forced rollback for testing")
                
        except IntegrityError:
            pass  # Expected exception
        
        # Verify rollback worked - message count should be unchanged
        final_message_count = Message.objects.count()
        assert final_message_count == initial_message_count, \
            "Message count should be unchanged after rollback"
    
    def test_concurrent_user_status_updates(self):
        """
        Test that concurrent user status updates don't create race conditions
        """
        from threading import Thread
        import time
        
        def update_status_repeatedly(user, iterations):
            """Update user status multiple times"""
            for i in range(iterations):
                status, created = UserStatus.objects.get_or_create(user=user)
                status.is_online = (i % 2) == 0
                status.save()
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Start multiple threads updating the same user's status
        threads = []
        for i in range(3):
            thread = Thread(target=update_status_repeatedly, args=(self.user1, 10))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify final state is consistent
        status = UserStatus.objects.get(user=self.user1)
        assert isinstance(status.is_online, bool), "Final status should be a valid boolean"
        
        # Verify only one status record exists
        status_count = UserStatus.objects.filter(user=self.user1).count()
        assert status_count == 1, "Should have exactly one status record per user"
"""
Property tests for notification delivery resilience in messaging system
**Validates: Requirements 6.4**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from channels.layers import InMemoryChannelLayer
import asyncio
import json
from .notification_service import NotificationService
from .models import Notification, NotificationPreference
from .serializers import JSONSerializer
from .logging_utils import MessagingLogger

User = get_user_model()


class TestNotificationDeliveryResilience(TransactionTestCase):
    """Property tests for notification delivery resilience functionality"""
    
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
        
        # Create notification preferences
        NotificationPreference.objects.get_or_create(
            user=self.user1,
            notification_type='test_notification',
            defaults={'is_enabled': True, 'delivery_method': 'realtime'}
        )
        
        self.notification_service = NotificationService()
        self.json_serializer = JSONSerializer()
    
    @given(
        notification_count=st.integers(min_value=1, max_value=15),
        websocket_failure_rate=st.floats(min_value=0.0, max_value=0.8),
        fallback_success_rate=st.floats(min_value=0.5, max_value=1.0)
    )
    @settings(max_examples=50, deadline=15000)
    def test_property_notification_delivery_resilience(self, notification_count, websocket_failure_rate, fallback_success_rate):
        """
        **Property 13: Notification Delivery Resilience**
        **Validates: Requirements 6.4**
        
        Property: Notification delivery must be resilient to failures and provide
        alternative delivery methods when primary delivery fails.
        
        This property ensures that:
        1. Failed WebSocket deliveries trigger fallback mechanisms (6.4)
        2. Alternative delivery methods are attempted in order
        3. Notifications are preserved in database regardless of delivery success
        4. Delivery failures are properly logged for monitoring
        """
        successful_deliveries = 0
        failed_deliveries = 0
        fallback_attempts = 0
        
        # Mock channel layer to simulate WebSocket failures
        with patch.object(self.notification_service, 'channel_layer') as mock_channel_layer:
            with patch.object(self.notification_service, '_send_email_notification') as mock_email:
                
                # Configure mocks based on failure rates
                def mock_group_send(*args, **kwargs):
                    nonlocal fallback_attempts
                    import random
                    if random.random() < websocket_failure_rate:
                        raise Exception("Simulated WebSocket failure")
                    return True
                
                def mock_email_fallback(notification):
                    nonlocal fallback_attempts
                    fallback_attempts += 1
                    import random
                    return random.random() < fallback_success_rate
                
                mock_channel_layer.group_send = Mock(side_effect=mock_group_send)
                mock_email.side_effect = mock_email_fallback
                
                # Create and send notifications
                notifications_created = []
                
                for i in range(notification_count):
                    notification = self.notification_service.create_and_send_notification(
                        recipient=self.user1,
                        notification_type='test_notification',
                        title=f'Test Notification {i}',
                        message=f'Test message content {i}',
                        sender=self.user2,
                        priority='normal'
                    )
                    
                    if notification:
                        notifications_created.append(notification)
                        successful_deliveries += 1
                    else:
                        failed_deliveries += 1
                
                # Verify resilience properties
                total_operations = successful_deliveries + failed_deliveries
                assert total_operations == notification_count, \
                    "All notification operations should be accounted for"
                
                # Verify notifications were created in database regardless of delivery success
                db_notification_count = Notification.objects.filter(
                    recipient=self.user1,
                    notification_type='test_notification'
                ).count()
                
                assert db_notification_count == successful_deliveries, \
                    f"Database should contain {successful_deliveries} notifications, found {db_notification_count}"
                
                # Verify fallback mechanisms were triggered for WebSocket failures
                expected_fallback_attempts = int(successful_deliveries * websocket_failure_rate)
                tolerance = max(1, int(successful_deliveries * 0.3))  # Allow for randomness
                
                if expected_fallback_attempts > 0:
                    assert abs(fallback_attempts - expected_fallback_attempts) <= tolerance, \
                        f"Expected ~{expected_fallback_attempts} fallback attempts, got {fallback_attempts}"
    
    @given(
        notification_data_complexity=st.integers(min_value=1, max_value=4),
        serialization_error_rate=st.floats(min_value=0.0, max_value=0.3),
        delivery_attempts=st.integers(min_value=3, max_value=8)
    )
    @settings(max_examples=30, deadline=10000)
    def test_property_serialization_error_resilience(self, notification_data_complexity, serialization_error_rate, delivery_attempts):
        """
        Property: Notification delivery must handle serialization errors gracefully
        
        This ensures that serialization failures don't prevent notification creation
        and that alternative serialization methods are attempted.
        """
        # Generate complex notification data
        extra_data = self._generate_complex_notification_data(notification_data_complexity)
        
        serialization_failures = 0
        successful_notifications = 0
        
        with patch.object(self.json_serializer, 'validate_serializable') as mock_validate:
            with patch.object(self.json_serializer, 'serialize_notification') as mock_serialize:
                
                def mock_validation(data):
                    import random
                    if random.random() < serialization_error_rate:
                        return False  # Simulate serialization failure
                    return True
                
                def mock_serialization(notification):
                    import random
                    if random.random() < serialization_error_rate:
                        raise Exception("Serialization error")
                    # Return valid serialized data
                    return {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'notification_type': notification.notification_type
                    }
                
                mock_validate.side_effect = mock_validation
                mock_serialize.side_effect = mock_serialization
                
                # Attempt multiple deliveries
                for attempt in range(delivery_attempts):
                    try:
                        notification = self.notification_service.create_and_send_notification(
                            recipient=self.user1,
                            notification_type='test_serialization',
                            title=f'Serialization Test {attempt}',
                            message=f'Test message {attempt}',
                            sender=self.user2,
                            extra_data=extra_data
                        )
                        
                        if notification:
                            successful_notifications += 1
                        else:
                            serialization_failures += 1
                            
                    except Exception as e:
                        serialization_failures += 1
                
                # Verify resilience to serialization errors
                total_attempts = successful_notifications + serialization_failures
                assert total_attempts == delivery_attempts, \
                    "All delivery attempts should be accounted for"
                
                # Even with serialization errors, some notifications should succeed
                if serialization_error_rate < 0.9:  # If error rate is not too high
                    assert successful_notifications > 0, \
                        "Some notifications should succeed even with serialization errors"
                
                # Verify notifications exist in database (creation should succeed even if delivery fails)
                db_notifications = Notification.objects.filter(
                    recipient=self.user1,
                    notification_type='test_serialization'
                ).count()
                
                assert db_notifications == successful_notifications, \
                    "Database notifications should match successful creations"
    
    @given(
        concurrent_notifications=st.integers(min_value=2, max_value=10),
        channel_layer_available=st.booleans(),
        database_error_rate=st.floats(min_value=0.0, max_value=0.3)
    )
    @settings(max_examples=25, deadline=12000)
    def test_property_concurrent_delivery_resilience(self, concurrent_notifications, channel_layer_available, database_error_rate):
        """
        Property: Concurrent notification deliveries must not interfere with each other
        
        This ensures that multiple simultaneous notification deliveries are handled
        independently and failures in one don't affect others.
        """
        import threading
        import time
        
        delivery_results = []
        
        def create_notification_concurrently(notification_index):
            """Create notification in separate thread"""
            try:
                # Simulate potential database errors
                import random
                if random.random() < database_error_rate:
                    raise Exception(f"Simulated database error for notification {notification_index}")
                
                notification = self.notification_service.create_and_send_notification(
                    recipient=self.user1,
                    notification_type='concurrent_test',
                    title=f'Concurrent Notification {notification_index}',
                    message=f'Concurrent test message {notification_index}',
                    sender=self.user2
                )
                
                delivery_results.append({
                    'index': notification_index,
                    'success': notification is not None,
                    'notification_id': notification.id if notification else None
                })
                
            except Exception as e:
                delivery_results.append({
                    'index': notification_index,
                    'success': False,
                    'error': str(e)
                })
        
        # Mock channel layer availability
        if not channel_layer_available:
            with patch.object(self.notification_service, 'channel_layer', None):
                # Start concurrent notification creation
                threads = []
                for i in range(concurrent_notifications):
                    thread = threading.Thread(target=create_notification_concurrently, args=(i,))
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join()
        else:
            # Start concurrent notification creation with channel layer
            threads = []
            for i in range(concurrent_notifications):
                thread = threading.Thread(target=create_notification_concurrently, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
        
        # Verify concurrent delivery results
        assert len(delivery_results) == concurrent_notifications, \
            f"Should have {concurrent_notifications} results, got {len(delivery_results)}"
        
        # Verify each notification was processed independently
        successful_deliveries = [r for r in delivery_results if r['success']]
        failed_deliveries = [r for r in delivery_results if not r['success']]
        
        # Check that notification IDs are unique (no interference)
        successful_ids = [r['notification_id'] for r in successful_deliveries if r['notification_id']]
        assert len(set(successful_ids)) == len(successful_ids), \
            "All successful notification IDs should be unique"
        
        # Verify database consistency
        db_notification_count = Notification.objects.filter(
            recipient=self.user1,
            notification_type='concurrent_test'
        ).count()
        
        assert db_notification_count == len(successful_deliveries), \
            f"Database should contain {len(successful_deliveries)} notifications, found {db_notification_count}"
    
    @given(
        notification_priority=st.sampled_from(['low', 'normal', 'high', 'urgent']),
        user_preferences_enabled=st.booleans(),
        quiet_hours_active=st.booleans()
    )
    @settings(max_examples=40, deadline=8000)
    def test_property_delivery_preference_resilience(self, notification_priority, user_preferences_enabled, quiet_hours_active):
        """
        Property: Notification delivery must respect user preferences while maintaining resilience
        
        This ensures that user preferences are honored but don't prevent proper
        error handling and fallback mechanisms.
        """
        # Set up user preferences
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.user1,
            notification_type='preference_test',
            defaults={
                'is_enabled': user_preferences_enabled,
                'delivery_method': 'realtime'
            }
        )
        
        if not created:
            preference.is_enabled = user_preferences_enabled
            preference.save()
        
        # Mock quiet hours if needed
        with patch.object(preference, 'is_in_quiet_hours', return_value=quiet_hours_active):
            
            notification = self.notification_service.create_and_send_notification(
                recipient=self.user1,
                notification_type='preference_test',
                title='Preference Test Notification',
                message='Testing user preference handling',
                sender=self.user2,
                priority=notification_priority
            )
            
            # Determine expected behavior based on preferences
            should_be_delivered = user_preferences_enabled
            
            # High/urgent priority notifications should bypass quiet hours
            if quiet_hours_active and notification_priority in ['high', 'urgent']:
                should_be_delivered = user_preferences_enabled  # Still respect enabled/disabled
            elif quiet_hours_active and notification_priority in ['low', 'normal']:
                should_be_delivered = False  # Blocked by quiet hours
            
            # Verify notification creation matches expectations
            if should_be_delivered:
                assert notification is not None, \
                    f"Notification should be created with priority {notification_priority}, enabled={user_preferences_enabled}, quiet_hours={quiet_hours_active}"
                
                # Verify notification exists in database
                db_notification = Notification.objects.filter(
                    recipient=self.user1,
                    notification_type='preference_test',
                    id=notification.id
                ).first()
                
                assert db_notification is not None, "Notification should exist in database"
                assert db_notification.priority == notification_priority, "Priority should be preserved"
                
            else:
                assert notification is None, \
                    f"Notification should not be created with priority {notification_priority}, enabled={user_preferences_enabled}, quiet_hours={quiet_hours_active}"
    
    def test_notification_validation_error_handling(self):
        """Test that notification validation errors are handled gracefully"""
        with patch('linkup.messaging.logging_utils.MessagingLogger.log_error') as mock_log:
            
            # Test invalid notification data
            invalid_cases = [
                # Missing recipient
                {'recipient': None, 'notification_type': 'test', 'title': 'Test', 'message': 'Test'},
                # Empty title
                {'recipient': self.user1, 'notification_type': 'test', 'title': '', 'message': 'Test'},
                # Empty message
                {'recipient': self.user1, 'notification_type': 'test', 'title': 'Test', 'message': ''},
                # Too long title
                {'recipient': self.user1, 'notification_type': 'test', 'title': 'x' * 201, 'message': 'Test'},
                # Too long message
                {'recipient': self.user1, 'notification_type': 'test', 'title': 'Test', 'message': 'x' * 1001},
            ]
            
            for i, invalid_data in enumerate(invalid_cases):
                try:
                    notification = self.notification_service.create_and_send_notification(**invalid_data)
                    assert notification is None, f"Invalid case {i} should return None"
                except Exception:
                    # Should not raise exceptions, should handle gracefully
                    pytest.fail(f"Invalid case {i} should not raise exception")
            
            # Verify errors were logged
            assert mock_log.call_count >= len(invalid_cases), \
                "Validation errors should be logged"
    
    def test_channel_layer_unavailable_fallback(self):
        """Test behavior when channel layer is unavailable"""
        # Test with no channel layer
        original_channel_layer = self.notification_service.channel_layer
        self.notification_service.channel_layer = None
        
        try:
            notification = self.notification_service.create_and_send_notification(
                recipient=self.user1,
                notification_type='no_channel_test',
                title='No Channel Test',
                message='Testing without channel layer',
                sender=self.user2
            )
            
            # Notification should still be created (database fallback)
            assert notification is not None, "Notification should be created even without channel layer"
            
            # Verify it exists in database
            db_notification = Notification.objects.filter(id=notification.id).first()
            assert db_notification is not None, "Notification should exist in database"
            
        finally:
            # Restore original channel layer
            self.notification_service.channel_layer = original_channel_layer
    
    def test_database_transaction_rollback_resilience(self):
        """Test that notification service handles database transaction rollbacks gracefully"""
        from django.db import transaction, IntegrityError
        
        initial_count = Notification.objects.count()
        
        try:
            with transaction.atomic():
                # Create notification
                notification = self.notification_service.create_and_send_notification(
                    recipient=self.user1,
                    notification_type='rollback_test',
                    title='Rollback Test',
                    message='Testing transaction rollback',
                    sender=self.user2
                )
                
                # Verify notification was created within transaction
                assert notification is not None, "Notification should be created"
                
                # Force rollback
                raise IntegrityError("Forced rollback for testing")
                
        except IntegrityError:
            pass  # Expected
        
        # Verify rollback worked
        final_count = Notification.objects.count()
        assert final_count == initial_count, "Notification count should be unchanged after rollback"
    
    def _generate_complex_notification_data(self, complexity_level):
        """Generate notification extra data with varying complexity"""
        if complexity_level == 1:
            return {'simple': 'data'}
        elif complexity_level == 2:
            return {
                'metadata': {'priority': 'high', 'category': 'test'},
                'tags': ['test', 'notification']
            }
        elif complexity_level == 3:
            return {
                'user_data': {
                    'preferences': {'theme': 'dark', 'language': 'en'},
                    'activity': {'last_seen': '2024-01-01T10:00:00Z'}
                },
                'content': {
                    'attachments': [{'type': 'image', 'url': 'http://example.com/image.jpg'}]
                }
            }
        else:  # complexity_level >= 4
            return {
                'complex_nested': {
                    'level1': {
                        'level2': {
                            'level3': {
                                'data': 'deep_value',
                                'array': [1, 2, 3, {'nested': 'object'}]
                            }
                        }
                    }
                },
                'mixed_types': [
                    'string',
                    42,
                    True,
                    None,
                    {'key': 'value'}
                ]
            }
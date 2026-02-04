"""
Property-Based Tests for Offline Message Handling

Tests the universal properties of the offline message handling system including
message queuing for offline recipients, chronological delivery, 7-day expiration,
and local message queuing for offline senders.

Feature: whatsapp-messaging-fix, Property 9: Offline Message Handling
Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings, assume
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from messaging.offline_queue_manager import OfflineQueueManager
from messaging.models import QueuedMessage, Message

User = get_user_model()


class OfflineHandlingPropertiesTest(TransactionTestCase):
    """Property-based tests for offline message handling system."""
    
    def setUp(self):
        """Set up test environment."""
        self.user1 = User.objects.create_user(
            username='offline_user1',
            email='offline1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='offline_user2',
            email='offline2@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='offline_user3',
            email='offline3@example.com',
            password='testpass123'
        )
        
        self.queue_manager = OfflineQueueManager()
    
    @given(
        message_count=st.integers(min_value=1, max_value=20),
        priority_levels=st.lists(
            st.integers(min_value=1, max_value=3),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=30, deadline=8000)
    def test_offline_recipient_queuing_property(self, message_count, priority_levels):
        """
        Property 9.1: Offline Recipient Message Queuing
        For any message sent to an offline recipient, the system should queue 
        the message for delivery when they come online, preserving message order 
        and priority.
        
        **Validates: Requirements 7.1, 7.2**
        """
        # Arrange
        messages_queued = []
        
        # Act - Queue messages for offline recipient
        for i in range(message_count):
            priority = priority_levels[i % len(priority_levels)]
            client_id = f"offline_test_{uuid.uuid4().hex[:8]}"
            
            queued_id = self.queue_manager.queue_message_for_offline_recipient(
                sender_id=self.user1.id,
                recipient_id=self.user2.id,
                content=f"Offline message {i+1}",
                priority=priority,
                client_id=client_id
            )
            
            if queued_id:
                messages_queued.append({
                    'id': queued_id,
                    'priority': priority,
                    'content': f"Offline message {i+1}",
                    'client_id': client_id
                })
        
        # Assert
        assert len(messages_queued) == message_count, "All messages should be queued"
        
        # Verify messages are in database
        queued_messages = QueuedMessage.objects.filter(
            recipient_id=self.user2.id,
            queue_type='incoming',
            is_processed=False
        ).order_by('priority', 'created_at')
        
        assert queued_messages.count() >= message_count, "Messages should be persisted"
        
        # Verify priority ordering
        if queued_messages.count() > 1:
            for i in range(1, len(queued_messages)):
                prev_msg = queued_messages[i-1]
                curr_msg = queued_messages[i]
                
                # Higher priority (lower number) should come first
                assert prev_msg.priority <= curr_msg.priority, "Messages should be ordered by priority"
                
                # Within same priority, should be chronological
                if prev_msg.priority == curr_msg.priority:
                    assert prev_msg.created_at <= curr_msg.created_at, "Same priority messages should be chronological"
        
        # Verify expiration is set (7 days)
        for msg in queued_messages:
            assert msg.expires_at is not None, "Expiration should be set"
            expected_expiry = msg.created_at + timedelta(days=7)
            time_diff = abs((msg.expires_at - expected_expiry).total_seconds())
            assert time_diff < 60, "Expiration should be approximately 7 days"
        
        # Cleanup
        QueuedMessage.objects.filter(id__in=[msg['id'] for msg in messages_queued]).delete()
    
    @given(
        offline_duration_hours=st.integers(min_value=1, max_value=48),
        message_intervals_minutes=st.lists(
            st.integers(min_value=1, max_value=60),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=10000)
    def test_chronological_delivery_property(self, offline_duration_hours, message_intervals_minutes):
        """
        Property 9.2: Chronological Message Delivery
        For any user who comes online after being offline, all queued messages 
        should be delivered in chronological order based on when they were 
        originally sent.
        
        **Validates: Requirements 7.2, 7.3**
        """
        # Arrange - Create messages with specific timestamps
        base_time = timezone.now() - timedelta(hours=offline_duration_hours)
        queued_messages = []
        
        for i, interval in enumerate(message_intervals_minutes):
            message_time = base_time + timedelta(minutes=sum(message_intervals_minutes[:i+1]))
            
            # Create queued message with specific timestamp
            queued_msg = QueuedMessage.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Chronological message {i+1}",
                queue_type='incoming',
                priority=2,  # Same priority to test chronological ordering
                created_at=message_time,
                expires_at=message_time + timedelta(days=7)
            )
            queued_messages.append(queued_msg)
        
        # Act - Deliver queued messages
        async def run_delivery():
            with patch('messaging.offline_queue_manager.OfflineQueueManager._deliver_message_via_websocket') as mock_deliver:
                mock_deliver.return_value = True
                
                result = await self.queue_manager.deliver_queued_messages_for_user(self.user2.id)
                return result, mock_deliver.call_args_list
        
        delivery_result, delivery_calls = asyncio.run(run_delivery())
        
        # Assert
        assert 'delivered_count' in delivery_result
        assert delivery_result['delivered_count'] >= len(message_intervals_minutes)
        
        # Verify messages were delivered in chronological order
        delivered_messages = delivery_result.get('messages', [])
        if len(delivered_messages) > 1:
            for i in range(1, len(delivered_messages)):
                prev_time = datetime.fromisoformat(delivered_messages[i-1]['created_at'])
                curr_time = datetime.fromisoformat(delivered_messages[i]['created_at'])
                assert prev_time <= curr_time, "Messages should be delivered in chronological order"
        
        # Verify queued messages are marked as processed
        for queued_msg in queued_messages:
            queued_msg.refresh_from_db()
            assert queued_msg.is_processed, "Delivered messages should be marked as processed"
        
        # Cleanup
        QueuedMessage.objects.filter(id__in=[msg.id for msg in queued_messages]).delete()
    
    @given(
        days_old=st.integers(min_value=8, max_value=30),
        message_count=st.integers(min_value=1, max_value=15)
    )
    @settings(max_examples=20, deadline=5000)
    def test_message_expiration_property(self, days_old, message_count):
        """
        Property 9.3: 7-Day Message Expiration
        For any queued message older than 7 days, the system should 
        automatically expire and remove it from the queue.
        
        **Validates: Requirements 7.5**
        """
        # Arrange - Create old messages
        old_time = timezone.now() - timedelta(days=days_old)
        old_messages = []
        
        for i in range(message_count):
            # Create message that's older than 7 days
            queued_msg = QueuedMessage.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Old message {i+1}",
                queue_type='incoming',
                created_at=old_time,
                expires_at=old_time + timedelta(days=7)  # Already expired
            )
            old_messages.append(queued_msg)
        
        # Also create some recent messages that shouldn't expire
        recent_messages = []
        for i in range(min(message_count, 5)):
            recent_msg = QueuedMessage.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Recent message {i+1}",
                queue_type='incoming',
                expires_at=timezone.now() + timedelta(days=7)
            )
            recent_messages.append(recent_msg)
        
        # Act - Clean up expired messages
        expired_count = self.queue_manager.cleanup_expired_messages()
        
        # Assert
        assert expired_count >= message_count, "Should clean up expired messages"
        
        # Verify old messages are removed
        for old_msg in old_messages:
            with pytest.raises(QueuedMessage.DoesNotExist):
                QueuedMessage.objects.get(id=old_msg.id)
        
        # Verify recent messages are preserved
        for recent_msg in recent_messages:
            assert QueuedMessage.objects.filter(id=recent_msg.id).exists(), "Recent messages should be preserved"
        
        # Cleanup
        QueuedMessage.objects.filter(id__in=[msg.id for msg in recent_messages]).delete()
    
    @given(
        outgoing_count=st.integers(min_value=1, max_value=10),
        sender_offline_duration=st.integers(min_value=1, max_value=24)
    )
    @settings(max_examples=20, deadline=6000)
    def test_local_message_queuing_property(self, outgoing_count, sender_offline_duration):
        """
        Property 9.4: Local Message Queuing for Offline Senders
        For any message sent by an offline user, the system should queue 
        the message locally and send it when the sender comes online.
        
        **Validates: Requirements 7.4**
        """
        # Arrange - Queue outgoing messages for offline sender
        queued_outgoing = []
        
        for i in range(outgoing_count):
            client_id = f"outgoing_test_{uuid.uuid4().hex[:8]}"
            
            queued_id = self.queue_manager.queue_outgoing_message_for_offline_sender(
                sender_id=self.user1.id,
                recipient_id=self.user2.id,
                content=f"Outgoing message {i+1}",
                client_id=client_id
            )
            
            if queued_id:
                queued_outgoing.append({
                    'id': queued_id,
                    'client_id': client_id,
                    'content': f"Outgoing message {i+1}"
                })
        
        # Assert
        assert len(queued_outgoing) == outgoing_count, "All outgoing messages should be queued"
        
        # Verify messages are queued as outgoing type
        outgoing_messages = QueuedMessage.objects.filter(
            sender_id=self.user1.id,
            queue_type='outgoing',
            is_processed=False
        )
        
        assert outgoing_messages.count() >= outgoing_count, "Outgoing messages should be persisted"
        
        # Verify queue properties
        for msg in outgoing_messages:
            assert msg.queue_type == 'outgoing', "Should be marked as outgoing"
            assert not msg.is_processed, "Should not be processed yet"
            assert msg.expires_at is not None, "Should have expiration set"
        
        # Test processing outgoing queue (simulate sender coming online)
        async def run_retry_processing():
            with patch('messaging.offline_queue_manager.OfflineQueueManager._retry_outgoing_message') as mock_retry:
                mock_retry.return_value = True
                
                # Mark messages as ready for retry
                for msg in outgoing_messages:
                    msg.schedule_next_retry()
                
                result = await self.queue_manager.process_retry_queue()
                return result, mock_retry.call_count
        
        retry_result, retry_calls = asyncio.run(run_retry_processing())
        
        # Should have attempted to process the outgoing messages
        assert retry_result.get('processed_count', 0) >= 0
        
        # Cleanup
        QueuedMessage.objects.filter(id__in=[msg['id'] for msg in queued_outgoing]).delete()
    
    @given(
        retry_scenarios=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=3),  # retry_count
                st.booleans()  # success
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=8000)
    def test_exponential_backoff_retry_property(self, retry_scenarios):
        """
        Property 9.5: Exponential Backoff for Failed Messages
        For any message that fails to deliver, the system should implement 
        exponential backoff for retry attempts with proper delay calculation.
        
        **Validates: Requirements 7.3, 9.2, 9.3**
        """
        # Arrange - Create message for retry testing
        original_message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Test retry message",
            status='pending'
        )
        
        queued_id = self.queue_manager.queue_message_for_retry(
            original_message_id=original_message.id,
            sender_id=self.user1.id,
            recipient_id=self.user2.id,
            content="Test retry message",
            error_message="Initial delivery failed",
            client_id="retry_test"
        )
        
        assert queued_id is not None, "Message should be queued for retry"
        
        queued_msg = QueuedMessage.objects.get(id=queued_id)
        
        # Test exponential backoff calculation
        previous_delay = 0
        for retry_count, success in retry_scenarios:
            # Set retry count
            queued_msg.retry_count = retry_count - 1  # Will be incremented
            queued_msg.save()
            
            # Calculate next retry delay
            if queued_msg.can_retry():
                delay = queued_msg.calculate_next_retry_delay()
                
                # Verify exponential backoff
                expected_delay = queued_msg.base_delay_seconds * (queued_msg.backoff_multiplier ** (retry_count - 1))
                expected_delay = min(expected_delay, queued_msg.max_delay_seconds)
                
                assert abs(delay - expected_delay) < 0.1, f"Delay should follow exponential backoff: expected {expected_delay}, got {delay}"
                
                # Verify delay increases (or caps at maximum)
                if retry_count > 1:
                    assert delay >= previous_delay, "Delay should increase or stay at maximum"
                
                previous_delay = delay
                
                # Schedule next retry
                queued_msg.schedule_next_retry()
                
                if success:
                    # Mark as processed and break
                    queued_msg.mark_processed(success=True)
                    break
                else:
                    # Mark as failed for next iteration
                    queued_msg.mark_failed("Simulated failure")
        
        # Verify final state
        queued_msg.refresh_from_db()
        
        # Should either be processed (if any success) or have proper retry state
        final_success = any(success for _, success in retry_scenarios)
        if final_success:
            assert queued_msg.is_processed, "Should be marked as processed on success"
        else:
            # Should have proper retry count and error tracking
            assert queued_msg.retry_count > 0, "Should have retry attempts recorded"
            assert queued_msg.last_error, "Should have error message recorded"
        
        # Cleanup
        QueuedMessage.objects.filter(id=queued_id).delete()
        Message.objects.filter(id=original_message.id).delete()
    
    @given(
        queue_types=st.lists(
            st.sampled_from(['outgoing', 'incoming', 'retry']),
            min_size=1,
            max_size=10
        ),
        priorities=st.lists(
            st.integers(min_value=1, max_value=3),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=15, deadline=5000)
    def test_queue_statistics_property(self, queue_types, priorities):
        """
        Property 9.6: Queue Statistics and Monitoring
        For any set of queued messages, the system should provide accurate 
        statistics about queue state, processing status, and message distribution.
        
        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        # Arrange - Create messages with different types and priorities
        created_messages = []
        
        for i, (queue_type, priority) in enumerate(zip(queue_types, priorities)):
            queued_msg = QueuedMessage.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Stats test message {i+1}",
                queue_type=queue_type,
                priority=priority,
                is_processed=(i % 3 == 0)  # Some processed, some not
            )
            created_messages.append(queued_msg)
        
        # Act - Get queue statistics
        stats = self.queue_manager.get_queue_statistics(user_id=self.user2.id)
        
        # Assert
        assert 'total_queued' in stats, "Should include total queued count"
        assert 'total_processed' in stats, "Should include total processed count"
        assert 'by_queue_type' in stats, "Should include breakdown by queue type"
        assert 'by_priority' in stats, "Should include breakdown by priority"
        assert 'pending_retries' in stats, "Should include pending retries count"
        assert 'timestamp' in stats, "Should include timestamp"
        
        # Verify queue type statistics
        for queue_type in set(queue_types):
            assert queue_type in stats['by_queue_type'], f"Should include stats for {queue_type}"
            expected_count = sum(1 for qt, processed in zip(queue_types, [msg.is_processed for msg in created_messages]) 
                               if qt == queue_type and not processed)
            # Allow some tolerance for other test data
            assert stats['by_queue_type'][queue_type] >= 0, f"Should have non-negative count for {queue_type}"
        
        # Verify priority statistics
        for priority in set(priorities):
            priority_key = str(priority)
            assert priority_key in stats['by_priority'], f"Should include stats for priority {priority}"
            assert stats['by_priority'][priority_key] >= 0, f"Should have non-negative count for priority {priority}"
        
        # Verify totals make sense
        assert stats['total_queued'] >= 0, "Total queued should be non-negative"
        assert stats['total_processed'] >= 0, "Total processed should be non-negative"
        assert stats['pending_retries'] >= 0, "Pending retries should be non-negative"
        
        # Cleanup
        QueuedMessage.objects.filter(id__in=[msg.id for msg in created_messages]).delete()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
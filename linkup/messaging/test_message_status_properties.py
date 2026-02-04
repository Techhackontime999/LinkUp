"""
Property-based tests for message status tracking system.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from messaging.models import Message
from messaging.message_status_manager import MessageStatusManager
import uuid

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class MessageStatusPropertiesTest(TransactionTestCase):
    """Property-based tests for message status tracking."""
    
    def setUp(self):
        """Set up test users and status manager."""
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
        self.status_manager = MessageStatusManager()
    
    @given(
        message_content=st.text(min_size=1, max_size=500),
        client_id=st.text(min_size=10, max_size=50).filter(lambda x: x.isalnum())
    )
    @settings(max_examples=30, deadline=3000)
    def test_property_message_status_transitions(self, message_content, client_id):
        """
        **Property 5: Message Status Tracking**
        
        For any message, status transitions should follow the correct sequence:
        1. pending -> sent -> delivered -> read (success path)
        2. pending/sent/delivered -> failed (error path)
        3. Status transitions should be atomic and consistent
        4. Timestamps should be set correctly for each status
        """
        # Create a message with pending status
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content=message_content,
            client_id=client_id,
            status='pending'
        )
        
        # Test successful status progression
        self._test_successful_status_progression(message)
        
        # Create another message to test failure scenarios
        message2 = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content=message_content + "_v2",
            client_id=client_id + "_v2",
            status='pending'
        )
        
        self._test_failure_status_transitions(message2)
    
    def _test_successful_status_progression(self, message):
        """Test the successful message status progression."""
        initial_time = timezone.now()
        
        # 1. pending -> sent
        assert message.status == 'pending'
        success = self.status_manager.update_message_status(message, 'sent')
        assert success, "Status update to 'sent' should succeed"
        
        message.refresh_from_db()
        assert message.status == 'sent'
        assert message.sent_at is not None
        assert message.sent_at >= initial_time
        
        # 2. sent -> delivered
        success = self.status_manager.update_message_status(message, 'delivered')
        assert success, "Status update to 'delivered' should succeed"
        
        message.refresh_from_db()
        assert message.status == 'delivered'
        assert message.delivered_at is not None
        assert message.delivered_at >= message.sent_at
        
        # 3. delivered -> read
        success = self.status_manager.update_message_status(message, 'read')
        assert success, "Status update to 'read' should succeed"
        
        message.refresh_from_db()
        assert message.status == 'read'
        assert message.is_read is True
        assert message.read_at is not None
        assert message.read_at >= message.delivered_at
    
    def _test_failure_status_transitions(self, message):
        """Test failure status transitions from any state."""
        error_message = "Test network error"
        
        # Test failure from pending
        success = self.status_manager.update_message_status(message, 'failed', error_message)
        assert success, "Status update to 'failed' should succeed"
        
        message.refresh_from_db()
        assert message.status == 'failed'
        assert message.failed_at is not None
        assert message.last_error == error_message
        assert message.retry_count == 1
    
    @given(
        status_sequence=st.lists(
            st.sampled_from(['sent', 'delivered', 'read', 'failed']),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=2000)
    def test_property_status_sequence_validity(self, status_sequence):
        """
        **Property 6: Status Sequence Validity**
        
        For any sequence of status updates:
        1. Valid transitions should succeed
        2. Invalid transitions should be handled gracefully
        3. Final status should be consistent with the last valid transition
        """
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Test message for sequence",
            status='pending'
        )
        
        last_valid_status = 'pending'
        
        for new_status in status_sequence:
            if self._is_valid_transition(last_valid_status, new_status):
                success = self.status_manager.update_message_status(message, new_status)
                assert success, f"Valid transition {last_valid_status} -> {new_status} should succeed"
                message.refresh_from_db()
                assert message.status == new_status
                last_valid_status = new_status
            else:
                # Invalid transitions should either fail gracefully or be ignored
                old_status = message.status
                self.status_manager.update_message_status(message, new_status)
                message.refresh_from_db()
                # Status should either remain unchanged or transition to failed
                assert message.status in [old_status, 'failed']
    
    def _is_valid_transition(self, from_status, to_status):
        """Check if a status transition is valid."""
        valid_transitions = {
            'pending': ['sent', 'failed'],
            'sent': ['delivered', 'failed'],
            'delivered': ['read', 'failed'],
            'read': ['failed'],  # Can only fail from read state
            'failed': []  # No transitions from failed state
        }
        return to_status in valid_transitions.get(from_status, [])
    
    @given(
        message_count=st.integers(min_value=1, max_value=10),
        target_status=st.sampled_from(['sent', 'delivered', 'read', 'failed'])
    )
    @settings(max_examples=15, deadline=3000)
    def test_property_bulk_status_update(self, message_count, target_status):
        """
        **Property 7: Bulk Status Update**
        
        For any number of messages and target status:
        1. Bulk updates should be atomic per message
        2. Partial failures should not affect other messages
        3. Results should accurately reflect success/failure counts
        """
        # Create multiple messages
        messages = []
        for i in range(message_count):
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Bulk test message {i}",
                client_id=f"bulk_test_{i}_{uuid.uuid4().hex[:8]}",
                status='pending'
            )
            messages.append(message)
        
        message_ids = [msg.id for msg in messages]
        
        # Perform bulk update
        results = self.status_manager.bulk_update_status(message_ids, target_status)
        
        # Verify results structure
        assert 'success_count' in results
        assert 'error_count' in results
        assert 'errors' in results
        assert isinstance(results['errors'], list)
        
        # Total should match message count
        assert results['success_count'] + results['error_count'] == message_count
        
        # Verify actual message statuses
        updated_messages = Message.objects.filter(id__in=message_ids)
        
        if target_status in ['sent', 'delivered', 'read']:
            # For valid transitions from pending, all should succeed
            success_count = sum(1 for msg in updated_messages if msg.status == target_status)
            assert success_count == results['success_count']
    
    @given(
        retry_count=st.integers(min_value=0, max_value=5),
        max_retries=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=20, deadline=2000)
    def test_property_message_retry_logic(self, retry_count, max_retries):
        """
        **Property 8: Message Retry Logic**
        
        For any retry count and max retries:
        1. Messages should be retryable if retry_count < max_retries
        2. Failed messages should track retry attempts correctly
        3. Retry logic should be consistent across all messages
        """
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Retry test message",
            status='failed',
            retry_count=retry_count
        )
        
        # Test retry eligibility
        can_retry = message.can_retry(max_retries)
        expected_can_retry = retry_count < max_retries
        
        assert can_retry == expected_can_retry, f"Retry logic incorrect: {retry_count} < {max_retries} = {expected_can_retry}"
        
        # Test retry attempt
        if can_retry:
            old_retry_count = message.retry_count
            self.status_manager.update_message_status(message, 'failed', "Retry test error")
            message.refresh_from_db()
            assert message.retry_count == old_retry_count + 1
    
    @given(
        message_content=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=15, deadline=2000)
    def test_property_status_icon_generation(self, message_content):
        """
        **Property 9: Status Icon Generation**
        
        For any message status:
        1. Status icons should be generated consistently
        2. Icons should be valid HTML
        3. Icon should match the message status
        4. Icons should contain appropriate CSS classes
        """
        statuses = ['pending', 'sent', 'delivered', 'read', 'failed']
        
        for status in statuses:
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=message_content,
                status=status
            )
            
            # Test icon generation
            icon_html = self.status_manager.get_status_icon_html(message)
            
            # Verify icon is valid HTML (contains SVG)
            assert '<svg' in icon_html, f"Icon for status '{status}' should contain SVG"
            assert '</svg>' in icon_html, f"Icon for status '{status}' should be valid SVG"
            
            # Verify appropriate CSS classes based on status
            if status == 'pending':
                assert 'animate-pulse' in icon_html or 'text-gray-400' in icon_html
            elif status == 'read':
                assert 'text-blue-500' in icon_html
            elif status == 'failed':
                assert 'text-red-500' in icon_html
            elif status in ['sent', 'delivered']:
                assert 'text-gray-400' in icon_html
    
    def test_property_conversation_status_summary(self):
        """
        **Property 10: Conversation Status Summary**
        
        For any conversation between two users:
        1. Status summary should accurately count messages by status
        2. Unread counts should be correct for each user
        3. Latest message info should be accurate
        4. Summary should handle empty conversations
        """
        # Test empty conversation
        summary = self.status_manager.get_conversation_status_summary(
            self.user1.id, self.user2.id
        )
        assert summary['total_messages'] == 0
        assert summary['unread_counts'][self.user1.id] == 0
        assert summary['unread_counts'][self.user2.id] == 0
        
        # Create messages with different statuses
        statuses = ['pending', 'sent', 'delivered', 'read', 'failed']
        messages = []
        
        for i, status in enumerate(statuses):
            message = Message.objects.create(
                sender=self.user1 if i % 2 == 0 else self.user2,
                recipient=self.user2 if i % 2 == 0 else self.user1,
                content=f"Test message {i}",
                status=status,
                is_read=(status == 'read')
            )
            messages.append(message)
        
        # Get updated summary
        summary = self.status_manager.get_conversation_status_summary(
            self.user1.id, self.user2.id
        )
        
        # Verify total count
        assert summary['total_messages'] == len(statuses)
        
        # Verify status counts
        for status in statuses:
            expected_count = 1  # We created one message per status
            actual_count = summary['status_counts'].get(status, 0)
            assert actual_count == expected_count, f"Status count for '{status}' incorrect"
        
        # Verify latest message
        latest_message = messages[-1]  # Last created message
        assert summary['latest_message']['id'] == latest_message.id
        assert summary['latest_message']['status'] == latest_message.status


if __name__ == '__main__':
    pytest.main([__file__])
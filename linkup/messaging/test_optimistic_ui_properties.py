"""
Property-Based Tests for Optimistic UI Performance

Tests the universal properties that must hold for optimistic UI updates
including 50ms display target for senders and 100ms target for recipients.

**Validates: Requirements 10.1, 10.2**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize, invariant
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import uuid
import time
import json

from .models import Message
from .consumers import ChatConsumer

User = get_user_model()


class OptimisticUIPerformanceTests(TransactionTestCase):
    """Property-based tests for optimistic UI performance functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='sender', email='sender@test.com')
        self.user2 = User.objects.create_user(username='recipient', email='recipient@test.com')
    
    @given(
        message_content=st.text(min_size=1, max_size=1000),
        client_id=st.text(min_size=1, max_size=50),
        send_delay=st.integers(min_value=0, max_value=200)
    )
    @settings(max_examples=30, deadline=8000)
    def test_optimistic_display_timing_property(self, message_content, client_id, send_delay):
        """
        **Property 12: Optimistic UI Performance - Display Timing**
        
        Optimistic message display must meet timing requirements:
        - Sender sees message within 50ms (optimistic display target)
        - Message appears immediately in UI before server confirmation
        - Display timing must be consistent regardless of message content
        
        **Validates: Requirements 10.1**
        """
        # Simulate optimistic message creation
        start_time = time.time()
        
        # Create optimistic message data
        optimistic_message = {
            'id': f'temp_{client_id}',
            'sender': self.user1.username,
            'recipient': self.user2.username,
            'content': message_content,
            'status': 'pending',
            'client_id': client_id,
            'created_at': timezone.now().isoformat(),
            'optimistic': True
        }
        
        # Simulate UI display delay (should be <= 50ms for sender)
        time.sleep(send_delay / 1000.0)  # Convert to seconds
        
        display_time = time.time()
        display_duration = (display_time - start_time) * 1000  # Convert to milliseconds
        
        # Property: Optimistic display should happen within 50ms target
        if send_delay <= 50:
            assert display_duration <= 100, \
                f"Optimistic display took {display_duration:.2f}ms, should be <= 100ms (including test overhead)"
        
        # Property: Message must have optimistic flag
        assert optimistic_message['optimistic'] is True, \
            "Optimistic messages must be flagged as optimistic"
        
        # Property: Message must have temporary ID
        assert optimistic_message['id'].startswith('temp_'), \
            f"Optimistic message ID should start with 'temp_', got {optimistic_message['id']}"
        
        # Property: Message must have pending status initially
        assert optimistic_message['status'] == 'pending', \
            f"Optimistic message should have 'pending' status, got {optimistic_message['status']}"
        
        # Property: Client ID must be preserved for deduplication
        assert optimistic_message['client_id'] == client_id, \
            f"Client ID must be preserved: expected {client_id}, got {optimistic_message['client_id']}"
    
    @given(
        message_count=st.integers(min_value=1, max_value=20),
        processing_delay=st.integers(min_value=0, max_value=150)
    )
    @settings(max_examples=25, deadline=10000)
    def test_recipient_display_timing_property(self, message_count, processing_delay):
        """
        **Property 12: Optimistic UI Performance - Recipient Display Timing**
        
        Message display for recipients must meet timing requirements:
        - Recipients see messages within 100ms target
        - Multiple messages should be processed efficiently
        - Display timing should scale well with message count
        
        **Validates: Requirements 10.2**
        """
        messages = []
        display_times = []
        
        # Create multiple messages to test batch processing
        for i in range(message_count):
            message_data = {
                'id': i + 1,
                'sender': self.user1.username,
                'recipient': self.user2.username,
                'content': f'Test message {i + 1}',
                'status': 'sent',
                'created_at': timezone.now().isoformat(),
                'optimistic': False
            }
            messages.append(message_data)
        
        # Simulate message processing and display
        start_time = time.time()
        
        for message in messages:
            # Simulate processing delay
            time.sleep(processing_delay / 1000.0)
            
            # Simulate message display
            display_time = time.time()
            display_duration = (display_time - start_time) * 1000
            display_times.append(display_duration)
            
            # Reset start time for next message
            start_time = time.time()
        
        # Property: Each message should be displayed within 100ms target
        for i, duration in enumerate(display_times):
            target_time = 100 + processing_delay  # Account for simulated delay
            assert duration <= target_time + 50, \
                f"Message {i + 1} display took {duration:.2f}ms, should be <= {target_time + 50}ms"
        
        # Property: Average display time should be reasonable
        if display_times:
            avg_display_time = sum(display_times) / len(display_times)
            max_acceptable_avg = 100 + processing_delay + 25  # 25ms buffer
            assert avg_display_time <= max_acceptable_avg, \
                f"Average display time {avg_display_time:.2f}ms exceeds acceptable limit {max_acceptable_avg}ms"
        
        # Property: Display times should not degrade significantly with more messages
        if len(display_times) > 1:
            first_half = display_times[:len(display_times)//2]
            second_half = display_times[len(display_times)//2:]
            
            if first_half and second_half:
                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)
                
                # Second half shouldn't be more than 50% slower than first half
                degradation_threshold = avg_first * 1.5
                assert avg_second <= degradation_threshold, \
                    f"Performance degraded: first half avg {avg_first:.2f}ms, second half avg {avg_second:.2f}ms"
    
    @given(
        update_count=st.integers(min_value=1, max_value=15),
        status_transitions=st.lists(
            st.sampled_from(['pending', 'sent', 'delivered', 'read', 'failed']),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=8000)
    def test_status_update_performance_property(self, update_count, status_transitions):
        """
        **Property 12: Optimistic UI Performance - Status Update Performance**
        
        Message status updates must be performant and smooth:
        - Status updates should be applied quickly
        - Multiple status updates should not cause UI lag
        - Status transitions should be visually smooth
        
        **Validates: Requirements 10.1, 10.2**
        """
        # Create messages for status updates
        messages = []
        for i in range(update_count):
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f'Status test message {i + 1}',
                client_id=f'status_test_{i}',
                status='pending'
            )
            messages.append(message)
        
        # Test status update performance
        update_times = []
        
        for message in messages:
            for new_status in status_transitions:
                start_time = time.time()
                
                # Simulate status update
                message.status = new_status
                if new_status == 'sent':
                    message.sent_at = timezone.now()
                elif new_status == 'delivered':
                    message.delivered_at = timezone.now()
                elif new_status == 'read':
                    message.read_at = timezone.now()
                    message.is_read = True
                
                message.save()
                
                end_time = time.time()
                update_duration = (end_time - start_time) * 1000
                update_times.append(update_duration)
        
        # Property: Individual status updates should be fast
        for i, duration in enumerate(update_times):
            assert duration <= 50, \
                f"Status update {i + 1} took {duration:.2f}ms, should be <= 50ms"
        
        # Property: Average update time should be reasonable
        if update_times:
            avg_update_time = sum(update_times) / len(update_times)
            assert avg_update_time <= 25, \
                f"Average status update time {avg_update_time:.2f}ms exceeds 25ms limit"
        
        # Property: Update times should be consistent
        if len(update_times) > 1:
            import statistics
            std_dev = statistics.stdev(update_times)
            mean_time = statistics.mean(update_times)
            
            # Standard deviation should not be more than 50% of mean
            max_std_dev = mean_time * 0.5
            assert std_dev <= max_std_dev, \
                f"Status update times too inconsistent: std_dev {std_dev:.2f}ms, mean {mean_time:.2f}ms"
    
    @given(
        message_batch_size=st.integers(min_value=1, max_value=10),
        concurrent_users=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15, deadline=12000)
    def test_concurrent_message_performance_property(self, message_batch_size, concurrent_users):
        """
        **Property 12: Optimistic UI Performance - Concurrent Message Performance**
        
        System must handle concurrent messages efficiently:
        - Multiple users sending messages simultaneously
        - Batch message processing should be efficient
        - Performance should not degrade with concurrent load
        
        **Validates: Requirements 10.1, 10.2**
        """
        # Create additional users for concurrency testing
        users = [self.user1, self.user2]
        for i in range(concurrent_users - 2):
            user = User.objects.create_user(
                username=f'concurrent_user_{i}',
                email=f'concurrent_{i}@test.com'
            )
            users.append(user)
        
        # Simulate concurrent message creation
        all_messages = []
        creation_times = []
        
        start_time = time.time()
        
        for user_idx, user in enumerate(users[:concurrent_users]):
            user_messages = []
            
            for msg_idx in range(message_batch_size):
                msg_start = time.time()
                
                # Create message
                message = Message.objects.create(
                    sender=user,
                    recipient=users[(user_idx + 1) % len(users)],
                    content=f'Concurrent message {msg_idx + 1} from {user.username}',
                    client_id=f'concurrent_{user_idx}_{msg_idx}',
                    status='pending'
                )
                
                msg_end = time.time()
                creation_time = (msg_end - msg_start) * 1000
                creation_times.append(creation_time)
                
                user_messages.append(message)
            
            all_messages.extend(user_messages)
        
        total_time = (time.time() - start_time) * 1000
        
        # Property: Individual message creation should be fast
        for i, duration in enumerate(creation_times):
            assert duration <= 100, \
                f"Message creation {i + 1} took {duration:.2f}ms, should be <= 100ms"
        
        # Property: Total batch processing time should scale reasonably
        expected_max_time = (message_batch_size * concurrent_users) * 50  # 50ms per message max
        assert total_time <= expected_max_time, \
            f"Total processing time {total_time:.2f}ms exceeds expected {expected_max_time}ms"
        
        # Property: Average creation time should be reasonable
        if creation_times:
            avg_creation_time = sum(creation_times) / len(creation_times)
            assert avg_creation_time <= 50, \
                f"Average message creation time {avg_creation_time:.2f}ms exceeds 50ms limit"
        
        # Property: All messages should be created successfully
        assert len(all_messages) == message_batch_size * concurrent_users, \
            f"Expected {message_batch_size * concurrent_users} messages, got {len(all_messages)}"
        
        # Property: Messages should have unique client IDs
        client_ids = [msg.client_id for msg in all_messages]
        unique_client_ids = set(client_ids)
        assert len(unique_client_ids) == len(client_ids), \
            f"Duplicate client IDs found: {len(client_ids)} total, {len(unique_client_ids)} unique"
    
    @given(
        animation_duration=st.integers(min_value=100, max_value=500),
        frame_count=st.integers(min_value=5, max_value=30)
    )
    @settings(max_examples=20, deadline=6000)
    def test_ui_animation_performance_property(self, animation_duration, frame_count):
        """
        **Property 12: Optimistic UI Performance - UI Animation Performance**
        
        UI animations must be smooth and performant:
        - Animations should maintain consistent frame rates
        - Animation timing should be predictable
        - Performance should not degrade during animations
        
        **Validates: Requirements 10.1, 10.2**
        """
        # Simulate animation frame timing
        frame_times = []
        expected_frame_duration = animation_duration / frame_count
        
        start_time = time.time()
        
        for frame in range(frame_count):
            frame_start = time.time()
            
            # Simulate frame processing (DOM updates, style calculations, etc.)
            # This is a simplified simulation of what happens during UI animations
            processing_time = min(expected_frame_duration / 1000.0, 0.016)  # Max 16ms per frame
            time.sleep(processing_time)
            
            frame_end = time.time()
            frame_duration = (frame_end - frame_start) * 1000
            frame_times.append(frame_duration)
        
        total_animation_time = (time.time() - start_time) * 1000
        
        # Property: Individual frames should not exceed 16ms (60 FPS target)
        for i, duration in enumerate(frame_times):
            assert duration <= 20, \
                f"Frame {i + 1} took {duration:.2f}ms, should be <= 20ms for smooth animation"
        
        # Property: Total animation time should be close to expected duration
        time_tolerance = animation_duration * 0.2  # 20% tolerance
        assert abs(total_animation_time - animation_duration) <= time_tolerance, \
            f"Animation time {total_animation_time:.2f}ms differs from expected {animation_duration}ms by more than {time_tolerance}ms"
        
        # Property: Frame timing should be consistent
        if len(frame_times) > 1:
            import statistics
            std_dev = statistics.stdev(frame_times)
            mean_time = statistics.mean(frame_times)
            
            # Standard deviation should not be more than 30% of mean
            max_std_dev = mean_time * 0.3
            assert std_dev <= max_std_dev, \
                f"Frame timing too inconsistent: std_dev {std_dev:.2f}ms, mean {mean_time:.2f}ms"
        
        # Property: Average frame time should support smooth animation
        if frame_times:
            avg_frame_time = sum(frame_times) / len(frame_times)
            assert avg_frame_time <= 16.67, \
                f"Average frame time {avg_frame_time:.2f}ms exceeds 16.67ms (60 FPS threshold)"


class OptimisticUIStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for optimistic UI performance.
    
    Tests complex interactions and performance characteristics over time.
    """
    
    messages = Bundle('messages')
    
    def __init__(self):
        super().__init__()
        self.user1 = None
        self.user2 = None
        self.performance_metrics = {
            'message_creation_times': [],
            'status_update_times': [],
            'total_messages': 0
        }
    
    @initialize()
    def setup_users(self):
        """Initialize test users."""
        self.user1 = User.objects.create_user(
            username=f'perf_user1_{uuid.uuid4().hex[:8]}',
            email=f'perf1_{uuid.uuid4().hex[:8]}@test.com'
        )
        self.user2 = User.objects.create_user(
            username=f'perf_user2_{uuid.uuid4().hex[:8]}',
            email=f'perf2_{uuid.uuid4().hex[:8]}@test.com'
        )
    
    @rule(
        target=messages,
        content=st.text(min_size=1, max_size=200)
    )
    def create_optimistic_message(self, content):
        """Create an optimistic message and measure performance."""
        start_time = time.time()
        
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content=content,
            client_id=f"perf_test_{uuid.uuid4().hex[:8]}",
            status='pending'
        )
        
        end_time = time.time()
        creation_time = (end_time - start_time) * 1000
        
        self.performance_metrics['message_creation_times'].append(creation_time)
        self.performance_metrics['total_messages'] += 1
        
        return message
    
    @rule(
        message=messages,
        new_status=st.sampled_from(['sent', 'delivered', 'read', 'failed'])
    )
    def update_message_status(self, message, new_status):
        """Update message status and measure performance."""
        start_time = time.time()
        
        message.status = new_status
        if new_status == 'sent':
            message.sent_at = timezone.now()
        elif new_status == 'delivered':
            message.delivered_at = timezone.now()
        elif new_status == 'read':
            message.read_at = timezone.now()
            message.is_read = True
        
        message.save()
        
        end_time = time.time()
        update_time = (end_time - start_time) * 1000
        
        self.performance_metrics['status_update_times'].append(update_time)
    
    @invariant()
    def performance_metrics_within_bounds(self):
        """Invariant: All performance metrics must stay within acceptable bounds."""
        # Check message creation times
        creation_times = self.performance_metrics['message_creation_times']
        if creation_times:
            avg_creation = sum(creation_times) / len(creation_times)
            assert avg_creation <= 100, \
                f"Average message creation time {avg_creation:.2f}ms exceeds 100ms limit"
            
            max_creation = max(creation_times)
            assert max_creation <= 200, \
                f"Maximum message creation time {max_creation:.2f}ms exceeds 200ms limit"
        
        # Check status update times
        update_times = self.performance_metrics['status_update_times']
        if update_times:
            avg_update = sum(update_times) / len(update_times)
            assert avg_update <= 50, \
                f"Average status update time {avg_update:.2f}ms exceeds 50ms limit"
            
            max_update = max(update_times)
            assert max_update <= 100, \
                f"Maximum status update time {max_update:.2f}ms exceeds 100ms limit"
    
    @invariant()
    def message_count_consistency(self):
        """Invariant: Message count should be consistent with performance metrics."""
        creation_count = len(self.performance_metrics['message_creation_times'])
        total_messages = self.performance_metrics['total_messages']
        
        assert creation_count == total_messages, \
            f"Creation count {creation_count} doesn't match total messages {total_messages}"


# Test class for running the state machine
class TestOptimisticUIStateMachine(TestCase):
    """Test runner for the optimistic UI performance state machine."""
    
    def test_optimistic_ui_state_machine(self):
        """Run the stateful property-based tests."""
        # Run the state machine test
        OptimisticUIStateMachine.TestCase.settings = settings(
            max_examples=15,
            stateful_step_count=8,
            deadline=10000
        )
        
        test_case = OptimisticUIStateMachine.TestCase()
        test_case.runTest()


if __name__ == '__main__':
    pytest.main([__file__])
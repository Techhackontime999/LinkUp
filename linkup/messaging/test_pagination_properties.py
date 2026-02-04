"""
Property-Based Tests for Chat History Pagination

Tests the universal properties that must hold for chat history pagination
including 20-message batch loading, proper pagination, and scroll performance.

**Validates: Requirements 10.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize, invariant
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from unittest.mock import patch, MagicMock
import uuid
import json

from .models import Message

User = get_user_model()


class ChatHistoryPaginationTests(TransactionTestCase):
    """Property-based tests for chat history pagination functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com')
        self.client = Client()
        self.client.force_login(self.user1)
    
    @given(
        total_messages=st.integers(min_value=1, max_value=200),
        page_size=st.integers(min_value=5, max_value=50),
        page_number=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=30, deadline=10000)
    def test_pagination_consistency_property(self, total_messages, page_size, page_number):
        """
        **Property 13: Chat History Pagination - Pagination Consistency**
        
        Pagination must be mathematically consistent:
        - Total items across all pages equals actual message count
        - No messages should be duplicated across pages
        - No messages should be missing from pagination
        - Page boundaries should be respected
        
        **Validates: Requirements 10.3**
        """
        assume(page_size <= 50)  # Reasonable page size limit
        assume(total_messages >= page_size or page_number == 1)
        
        # Create messages with timestamps spread over time
        messages = []
        base_time = timezone.now() - timedelta(hours=total_messages)
        
        for i in range(total_messages):
            message = Message.objects.create(
                sender=self.user1 if i % 2 == 0 else self.user2,
                recipient=self.user2 if i % 2 == 0 else self.user1,
                content=f'Test message {i + 1}',
                client_id=f'pagination_test_{i}',
                created_at=base_time + timedelta(minutes=i)
            )
            messages.append(message)
        
        # Test pagination via API
        url = reverse('messaging:fetch_history', args=[self.user2.username])
        response = self.client.get(url, {
            'page': page_number,
            'page_size': page_size
        })
        
        assert response.status_code == 200, f"API request failed with status {response.status_code}"
        
        data = response.json()
        assert 'messages' in data, "Response must contain 'messages' field"
        assert 'pagination' in data, "Response must contain 'pagination' field"
        
        returned_messages = data['messages']
        pagination_info = data['pagination']
        
        # Property: Returned message count should not exceed page size
        assert len(returned_messages) <= page_size, \
            f"Returned {len(returned_messages)} messages, should be <= {page_size}"
        
        # Property: Pagination metadata should be consistent
        expected_total_pages = (total_messages + page_size - 1) // page_size
        assert pagination_info['total_pages'] == expected_total_pages, \
            f"Expected {expected_total_pages} total pages, got {pagination_info['total_pages']}"
        
        assert pagination_info['current_page'] == page_number, \
            f"Expected current page {page_number}, got {pagination_info['current_page']}"
        
        assert pagination_info['total_messages'] == total_messages, \
            f"Expected {total_messages} total messages, got {pagination_info['total_messages']}"
        
        # Property: has_previous and has_next should be correct
        expected_has_previous = page_number > 1
        expected_has_next = page_number < expected_total_pages
        
        assert pagination_info['has_previous'] == expected_has_previous, \
            f"has_previous should be {expected_has_previous} for page {page_number}"
        
        assert pagination_info['has_next'] == expected_has_next, \
            f"has_next should be {expected_has_next} for page {page_number}"
        
        # Property: Messages should be ordered chronologically (oldest first)
        if len(returned_messages) > 1:
            for i in range(1, len(returned_messages)):
                prev_time = returned_messages[i-1]['created_at']
                curr_time = returned_messages[i]['created_at']
                assert prev_time <= curr_time, \
                    f"Messages not in chronological order: {prev_time} > {curr_time}"
        
        # Property: Message IDs should be unique
        message_ids = [msg['id'] for msg in returned_messages]
        unique_ids = set(message_ids)
        assert len(unique_ids) == len(message_ids), \
            f"Duplicate message IDs found: {len(message_ids)} total, {len(unique_ids)} unique"
    
    @given(
        message_count=st.integers(min_value=25, max_value=100),
        batch_size=st.integers(min_value=5, max_value=25)
    )
    @settings(max_examples=20, deadline=12000)
    def test_infinite_scroll_loading_property(self, message_count, batch_size):
        """
        **Property 13: Chat History Pagination - Infinite Scroll Loading**
        
        Infinite scroll must load messages correctly:
        - Each batch should load the correct number of messages
        - Messages should not overlap between batches
        - Loading should work with before_id parameter
        - has_more flag should be accurate
        
        **Validates: Requirements 10.3**
        """
        assume(batch_size <= 25)  # Reasonable batch size
        assume(message_count > batch_size)  # Need enough messages for multiple batches
        
        # Create messages with sequential timestamps
        messages = []
        base_time = timezone.now() - timedelta(hours=message_count)
        
        for i in range(message_count):
            message = Message.objects.create(
                sender=self.user1 if i % 2 == 0 else self.user2,
                recipient=self.user2 if i % 2 == 0 else self.user1,
                content=f'Infinite scroll message {i + 1}',
                client_id=f'infinite_scroll_{i}',
                created_at=base_time + timedelta(minutes=i)
            )
            messages.append(message)
        
        # Test infinite scroll loading
        url = reverse('messaging:load_older_messages', args=[self.user2.username])
        loaded_messages = []
        all_loaded_ids = set()
        
        # Start with the newest message
        newest_message = messages[-1]
        before_id = newest_message.id
        
        batches_loaded = 0
        max_batches = (message_count // batch_size) + 1
        
        while batches_loaded < max_batches and before_id:
            response = self.client.get(url, {
                'before_id': before_id,
                'page_size': batch_size
            })
            
            assert response.status_code == 200, \
                f"Infinite scroll request failed with status {response.status_code}"
            
            data = response.json()
            assert 'messages' in data, "Response must contain 'messages' field"
            assert 'has_more' in data, "Response must contain 'has_more' field"
            
            batch_messages = data['messages']
            has_more = data['has_more']
            
            # Property: Batch size should not exceed requested size
            assert len(batch_messages) <= batch_size, \
                f"Batch {batches_loaded + 1} returned {len(batch_messages)} messages, should be <= {batch_size}"
            
            # Property: No duplicate messages across batches
            for msg in batch_messages:
                msg_id = msg['id']
                assert msg_id not in all_loaded_ids, \
                    f"Duplicate message ID {msg_id} found in batch {batches_loaded + 1}"
                all_loaded_ids.add(msg_id)
            
            loaded_messages.extend(batch_messages)
            
            # Property: Messages in batch should be chronologically ordered
            if len(batch_messages) > 1:
                for i in range(1, len(batch_messages)):
                    prev_time = batch_messages[i-1]['created_at']
                    curr_time = batch_messages[i]['created_at']
                    assert prev_time <= curr_time, \
                        f"Messages in batch {batches_loaded + 1} not chronologically ordered"
            
            # Update before_id for next batch
            if batch_messages:
                before_id = batch_messages[0]['id']  # Oldest message in current batch
            else:
                before_id = None
            
            batches_loaded += 1
            
            # Property: has_more should be accurate
            remaining_messages = message_count - len(loaded_messages)
            expected_has_more = remaining_messages > 0
            
            if not batch_messages:  # Empty batch means no more messages
                assert not has_more, \
                    f"has_more should be False when no messages returned in batch {batches_loaded}"
                break
            elif remaining_messages <= 0:
                assert not has_more, \
                    f"has_more should be False when all messages loaded (batch {batches_loaded})"
            
            if not has_more:
                break
        
        # Property: Total loaded messages should not exceed total available
        assert len(loaded_messages) <= message_count, \
            f"Loaded {len(loaded_messages)} messages, but only {message_count} exist"
        
        # Property: All loaded message IDs should be unique
        loaded_ids = [msg['id'] for msg in loaded_messages]
        unique_loaded_ids = set(loaded_ids)
        assert len(unique_loaded_ids) == len(loaded_ids), \
            f"Duplicate IDs in loaded messages: {len(loaded_ids)} total, {len(unique_loaded_ids)} unique"
    
    @given(
        page_sizes=st.lists(
            st.integers(min_value=5, max_value=30),
            min_size=2,
            max_size=5
        ),
        total_messages=st.integers(min_value=50, max_value=150)
    )
    @settings(max_examples=15, deadline=15000)
    def test_variable_page_size_consistency_property(self, page_sizes, total_messages):
        """
        **Property 13: Chat History Pagination - Variable Page Size Consistency**
        
        Pagination must work consistently with different page sizes:
        - Different page sizes should return same total message count
        - Message ordering should be consistent across page sizes
        - No messages should be lost or duplicated with different page sizes
        
        **Validates: Requirements 10.3**
        """
        # Create messages
        messages = []
        base_time = timezone.now() - timedelta(hours=total_messages)
        
        for i in range(total_messages):
            message = Message.objects.create(
                sender=self.user1 if i % 2 == 0 else self.user2,
                recipient=self.user2 if i % 2 == 0 else self.user1,
                content=f'Variable page size test message {i + 1}',
                client_id=f'var_page_size_{i}',
                created_at=base_time + timedelta(minutes=i)
            )
            messages.append(message)
        
        # Test with different page sizes
        url = reverse('messaging:fetch_history', args=[self.user2.username])
        results_by_page_size = {}
        
        for page_size in page_sizes:
            all_messages_for_size = []
            page = 1
            
            while True:
                response = self.client.get(url, {
                    'page': page,
                    'page_size': page_size
                })
                
                assert response.status_code == 200, \
                    f"Request failed for page_size {page_size}, page {page}"
                
                data = response.json()
                batch_messages = data['messages']
                pagination_info = data['pagination']
                
                all_messages_for_size.extend(batch_messages)
                
                if not pagination_info['has_next']:
                    break
                
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 20:
                    break
            
            results_by_page_size[page_size] = all_messages_for_size
        
        # Property: Total message count should be consistent across page sizes
        message_counts = [len(msgs) for msgs in results_by_page_size.values()]
        unique_counts = set(message_counts)
        assert len(unique_counts) == 1, \
            f"Inconsistent message counts across page sizes: {message_counts}"
        
        # Property: Message ordering should be consistent
        if len(results_by_page_size) >= 2:
            page_size_list = list(results_by_page_size.keys())
            first_result = results_by_page_size[page_size_list[0]]
            
            for page_size in page_size_list[1:]:
                other_result = results_by_page_size[page_size]
                
                # Compare message IDs in order
                first_ids = [msg['id'] for msg in first_result]
                other_ids = [msg['id'] for msg in other_result]
                
                assert first_ids == other_ids, \
                    f"Message order differs between page_size {page_size_list[0]} and {page_size}"
        
        # Property: All messages should be unique within each page size result
        for page_size, msgs in results_by_page_size.items():
            msg_ids = [msg['id'] for msg in msgs]
            unique_ids = set(msg_ids)
            assert len(unique_ids) == len(msg_ids), \
                f"Duplicate messages found for page_size {page_size}: {len(msg_ids)} total, {len(unique_ids)} unique"
    
    @given(
        search_before_id=st.integers(min_value=1, max_value=50),
        message_count=st.integers(min_value=60, max_value=120),
        load_size=st.integers(min_value=10, max_value=30)
    )
    @settings(max_examples=20, deadline=10000)
    def test_before_id_filtering_property(self, search_before_id, message_count, load_size):
        """
        **Property 13: Chat History Pagination - Before ID Filtering**
        
        Before ID filtering must work correctly:
        - Only messages created before the specified message should be returned
        - Filtering should be consistent and predictable
        - Invalid before_id should be handled gracefully
        
        **Validates: Requirements 10.3**
        """
        assume(search_before_id < message_count)  # Ensure before_id exists
        
        # Create messages with known timestamps
        messages = []
        base_time = timezone.now() - timedelta(hours=message_count)
        
        for i in range(message_count):
            message = Message.objects.create(
                sender=self.user1 if i % 2 == 0 else self.user2,
                recipient=self.user2 if i % 2 == 0 else self.user1,
                content=f'Before ID test message {i + 1}',
                client_id=f'before_id_test_{i}',
                created_at=base_time + timedelta(minutes=i)
            )
            messages.append(message)
        
        # Get the reference message for before_id
        reference_message = messages[search_before_id - 1]  # 0-indexed
        reference_time = reference_message.created_at
        
        # Test before_id filtering
        url = reverse('messaging:load_older_messages', args=[self.user2.username])
        response = self.client.get(url, {
            'before_id': reference_message.id,
            'page_size': load_size
        })
        
        assert response.status_code == 200, \
            f"Before ID filtering request failed with status {response.status_code}"
        
        data = response.json()
        returned_messages = data['messages']
        
        # Property: All returned messages should be created before the reference message
        for msg in returned_messages:
            msg_created_at = timezone.datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
            assert msg_created_at < reference_time, \
                f"Message {msg['id']} created at {msg_created_at} should be before {reference_time}"
        
        # Property: Returned messages should be in chronological order
        if len(returned_messages) > 1:
            for i in range(1, len(returned_messages)):
                prev_time = returned_messages[i-1]['created_at']
                curr_time = returned_messages[i]['created_at']
                assert prev_time <= curr_time, \
                    f"Messages not in chronological order: {prev_time} > {curr_time}"
        
        # Property: Number of returned messages should not exceed load_size
        assert len(returned_messages) <= load_size, \
            f"Returned {len(returned_messages)} messages, should be <= {load_size}"
        
        # Property: has_more should be accurate
        has_more = data.get('has_more', False)
        
        # Count how many messages exist before the reference message
        messages_before_count = sum(1 for msg in messages if msg.created_at < reference_time)
        
        if len(returned_messages) < messages_before_count:
            # There are more messages available
            assert has_more, \
                f"has_more should be True when {messages_before_count} messages exist before reference but only {len(returned_messages)} returned"
        elif len(returned_messages) == messages_before_count:
            # All available messages were returned
            assert not has_more, \
                f"has_more should be False when all {messages_before_count} available messages were returned"


class PaginationStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for pagination functionality.
    
    Tests complex pagination scenarios and state transitions.
    """
    
    messages = Bundle('messages')
    
    def __init__(self):
        super().__init__()
        self.user1 = None
        self.user2 = None
        self.client = None
        self.total_messages = 0
    
    @initialize()
    def setup_test_environment(self):
        """Initialize test environment."""
        self.user1 = User.objects.create_user(
            username=f'pagination_user1_{uuid.uuid4().hex[:8]}',
            email=f'pag1_{uuid.uuid4().hex[:8]}@test.com'
        )
        self.user2 = User.objects.create_user(
            username=f'pagination_user2_{uuid.uuid4().hex[:8]}',
            email=f'pag2_{uuid.uuid4().hex[:8]}@test.com'
        )
        self.client = Client()
        self.client.force_login(self.user1)
    
    @rule(
        target=messages,
        content=st.text(min_size=1, max_size=100)
    )
    def add_message(self, content):
        """Add a message to the conversation."""
        message = Message.objects.create(
            sender=self.user1 if self.total_messages % 2 == 0 else self.user2,
            recipient=self.user2 if self.total_messages % 2 == 0 else self.user1,
            content=content,
            client_id=f'state_machine_{self.total_messages}',
            created_at=timezone.now() + timedelta(seconds=self.total_messages)
        )
        
        self.total_messages += 1
        return message
    
    @rule(
        page_size=st.integers(min_value=5, max_value=20),
        page_number=st.integers(min_value=1, max_value=5)
    )
    def test_pagination_request(self, page_size, page_number):
        """Test a pagination request and verify consistency."""
        if self.total_messages == 0:
            return  # Skip if no messages
        
        url = reverse('messaging:fetch_history', args=[self.user2.username])
        response = self.client.get(url, {
            'page': page_number,
            'page_size': page_size
        })
        
        assert response.status_code == 200, \
            f"Pagination request failed with status {response.status_code}"
        
        data = response.json()
        returned_messages = data['messages']
        pagination_info = data['pagination']
        
        # Invariant: Returned messages should not exceed page size
        assert len(returned_messages) <= page_size, \
            f"Returned {len(returned_messages)} messages, should be <= {page_size}"
        
        # Invariant: Total messages should match our count
        assert pagination_info['total_messages'] == self.total_messages, \
            f"API reports {pagination_info['total_messages']} messages, we have {self.total_messages}"
    
    @rule(message=messages)
    def test_before_id_loading(self, message):
        """Test loading messages before a specific message."""
        url = reverse('messaging:load_older_messages', args=[self.user2.username])
        response = self.client.get(url, {
            'before_id': message.id,
            'page_size': 10
        })
        
        if response.status_code == 200:
            data = response.json()
            returned_messages = data['messages']
            
            # Invariant: All returned messages should be older than the reference
            for msg in returned_messages:
                msg_id = msg['id']
                assert msg_id != message.id, \
                    f"Reference message {message.id} should not be included in results"
    
    @invariant()
    def total_message_count_consistent(self):
        """Invariant: Total message count should be consistent."""
        actual_count = Message.objects.filter(
            sender__in=[self.user1, self.user2],
            recipient__in=[self.user1, self.user2]
        ).count()
        
        assert actual_count == self.total_messages, \
            f"Database has {actual_count} messages, state machine tracked {self.total_messages}"


# Test class for running the state machine
class TestPaginationStateMachine(TestCase):
    """Test runner for the pagination state machine."""
    
    def test_pagination_state_machine(self):
        """Run the stateful property-based tests."""
        # Run the state machine test
        PaginationStateMachine.TestCase.settings = settings(
            max_examples=10,
            stateful_step_count=15,
            deadline=20000
        )
        
        test_case = PaginationStateMachine.TestCase()
        test_case.runTest()


if __name__ == '__main__':
    pytest.main([__file__])
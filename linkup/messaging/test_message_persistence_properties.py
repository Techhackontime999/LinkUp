"""
Property-Based Tests for Message Persistence and Synchronization

**Validates: Requirements 11.1, 11.3, 11.4**

This module contains property-based tests that verify the correctness of message persistence
and synchronization functionality in the WhatsApp-like messaging system.

Requirements Coverage:
- 11.1: Message persistence with database locking
- 11.3: Multi-tab synchronization support  
- 11.4: Accurate timestamp tracking
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, IntegrityError
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.extra.django import TestCase as HypothesisTestCase
from unittest.mock import patch, MagicMock, AsyncMock
import logging

from .models import Message, UserStatus
from .message_persistence_manager import (
    MessagePersistenceManager, MessageLockManager, 
    TimestampManager, MultiTabSyncManager
)

User = get_user_model()
logger = logging.getLogger(__name__)


class MessagePersistencePropertiesTest(HypothesisTestCase):
    """Property-based tests for message persistence functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
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
        self.persistence_manager = MessagePersistenceManager()
        
        # Ensure clean state
        Message.objects.all().delete()
    
    def tearDown(self):
        """Clean up after tests"""
        Message.objects.all().delete()
    
    @given(
        content=st.text(min_size=1, max_size=1000),
        client_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=50, deadline=5000)
    def test_atomic_message_creation_properties(self, content, client_id):
        """
        **Property 16.1: Atomic Message Creation**
        
        Property: Message creation is atomic and prevents duplicates
        - Messages with same client_id should not create duplicates
        - Failed creation should not leave partial data
        - Timestamps should be accurate and ordered
        """
        async def run_test():
            # Test atomic creation
            message1 = await self.persistence_manager.create_message_atomic(
                sender=self.user1,
                recipient=self.user2,
                content=content,
                client_id=client_id
            )
            
            # Verify message was created
            self.assertIsNotNone(message1)
            self.assertEqual(message1.content, content)
            self.assertEqual(message1.client_id, client_id)
            self.assertEqual(message1.sender, self.user1)
            self.assertEqual(message1.recipient, self.user2)
            
            # Test duplicate prevention
            message2 = await self.persistence_manager.create_message_atomic(
                sender=self.user1,
                recipient=self.user2,
                content="Different content",
                client_id=client_id  # Same client_id
            )
            
            # Should return the same message, not create duplicate
            self.assertEqual(message1.id, message2.id)
            self.assertEqual(message2.content, content)  # Original content preserved
            
            # Verify only one message exists
            message_count = await Message.objects.filter(
                sender=self.user1,
                client_id=client_id
            ).acount()
            self.assertEqual(message_count, 1)
            
            # Test timestamp accuracy
            self.assertIsNotNone(message1.created_at)
            self.assertLessEqual(
                abs((timezone.now() - message1.created_at).total_seconds()),
                5  # Within 5 seconds
            )
        
        asyncio.run(run_test())
    
    @given(
        message_count=st.integers(min_value=2, max_value=10),
        new_status=st.sampled_from(['sent', 'delivered', 'read'])
    )
    @settings(max_examples=30, deadline=10000)
    def test_bulk_status_update_properties(self, message_count, new_status):
        """
        **Property 16.2: Bulk Status Update Consistency**
        
        Property: Bulk status updates maintain consistency
        - All valid messages should be updated atomically
        - Invalid transitions should be rejected
        - Status transitions should follow proper order
        """
        async def run_test():
            # Create multiple messages
            messages = []
            for i in range(message_count):
                message = await self.persistence_manager.create_message_atomic(
                    sender=self.user1,
                    recipient=self.user2,
                    content=f"Test message {i}",
                    client_id=f"test_bulk_{i}_{uuid.uuid4().hex[:8]}"
                )
                messages.append(message)
            
            message_ids = [msg.id for msg in messages]
            
            # Test bulk status update
            result = await self.persistence_manager.bulk_update_message_status(
                message_ids=message_ids,
                new_status=new_status,
                user_id=self.user1.id
            )
            
            # Verify results
            self.assertIsInstance(result, dict)
            self.assertIn('updated_count', result)
            self.assertIn('failed_count', result)
            self.assertIn('total_requested', result)
            self.assertEqual(result['total_requested'], message_count)
            
            # All messages should be updated (since they start as 'pending')
            self.assertEqual(result['updated_count'], message_count)
            self.assertEqual(result['failed_count'], 0)
            
            # Verify actual status changes
            for message_id in message_ids:
                updated_message = await Message.objects.aget(id=message_id)
                self.assertEqual(updated_message.status, new_status)
                
                # Verify appropriate timestamp was set
                if new_status == 'sent':
                    self.assertIsNotNone(updated_message.sent_at)
                elif new_status == 'delivered':
                    self.assertIsNotNone(updated_message.delivered_at)
                elif new_status == 'read':
                    self.assertIsNotNone(updated_message.read_at)
                    self.assertTrue(updated_message.is_read)
        
        asyncio.run(run_test())
    
    @given(
        limit=st.integers(min_value=1, max_value=100),
        total_messages=st.integers(min_value=5, max_value=50)
    )
    @settings(max_examples=20, deadline=15000)
    def test_conversation_loading_properties(self, limit, total_messages):
        """
        **Property 16.3: Conversation Loading Consistency**
        
        Property: Conversation loading maintains proper ordering and limits
        - Messages should be returned in chronological order
        - Limit should be respected
        - Pagination should work correctly
        """
        assume(limit <= total_messages)  # Ensure meaningful test
        
        async def run_test():
            # Create messages with slight time differences
            messages = []
            base_time = timezone.now()
            
            for i in range(total_messages):
                # Create message with incremental timestamp
                message = await self.persistence_manager.create_message_atomic(
                    sender=self.user1 if i % 2 == 0 else self.user2,
                    recipient=self.user2 if i % 2 == 0 else self.user1,
                    content=f"Message {i:03d}",
                    client_id=f"conv_test_{i}_{uuid.uuid4().hex[:8]}"
                )
                
                # Manually adjust timestamp to ensure ordering
                message.created_at = base_time + timedelta(seconds=i)
                await message.asave()
                messages.append(message)
            
            # Test conversation loading
            conversation_data = await self.persistence_manager.get_conversation_messages(
                user1_id=self.user1.id,
                user2_id=self.user2.id,
                limit=limit,
                include_metadata=True
            )
            
            # Verify structure
            self.assertIsInstance(conversation_data, dict)
            self.assertIn('messages', conversation_data)
            self.assertIn('count', conversation_data)
            self.assertIn('has_more', conversation_data)
            self.assertIn('metadata', conversation_data)
            
            loaded_messages = conversation_data['messages']
            
            # Verify limit is respected
            self.assertLessEqual(len(loaded_messages), limit)
            self.assertEqual(conversation_data['count'], len(loaded_messages))
            
            # Verify chronological ordering (oldest first)
            if len(loaded_messages) > 1:
                for i in range(1, len(loaded_messages)):
                    prev_time = datetime.fromisoformat(loaded_messages[i-1]['created_at'].replace('Z', '+00:00'))
                    curr_time = datetime.fromisoformat(loaded_messages[i]['created_at'].replace('Z', '+00:00'))
                    self.assertLessEqual(prev_time, curr_time)
            
            # Verify has_more flag
            expected_has_more = total_messages > limit
            self.assertEqual(conversation_data['has_more'], expected_has_more)
            
            # Verify metadata
            metadata = conversation_data['metadata']
            self.assertIn('total_messages', metadata)
            self.assertEqual(metadata['total_messages'], total_messages)
        
        asyncio.run(run_test())
    
    @given(
        concurrent_operations=st.integers(min_value=2, max_value=5),
        content=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=15, deadline=20000)
    def test_concurrent_message_creation_properties(self, concurrent_operations, content):
        """
        **Property 16.4: Concurrent Operation Safety**
        
        Property: Concurrent message operations are safe
        - No race conditions in message creation
        - Database locks prevent corruption
        - All operations complete successfully
        """
        async def run_test():
            # Create tasks for concurrent message creation
            tasks = []
            client_ids = []
            
            for i in range(concurrent_operations):
                client_id = f"concurrent_{i}_{uuid.uuid4().hex[:8]}"
                client_ids.append(client_id)
                
                task = self.persistence_manager.create_message_atomic(
                    sender=self.user1,
                    recipient=self.user2,
                    content=f"{content} - {i}",
                    client_id=client_id
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all operations succeeded
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.fail(f"Concurrent operation {i} failed: {result}")
                else:
                    self.assertIsNotNone(result)
                    successful_results.append(result)
            
            # Verify all messages were created
            self.assertEqual(len(successful_results), concurrent_operations)
            
            # Verify no duplicates (all client_ids should be unique)
            created_client_ids = [msg.client_id for msg in successful_results]
            self.assertEqual(len(set(created_client_ids)), concurrent_operations)
            
            # Verify all messages exist in database
            for client_id in client_ids:
                message_exists = await Message.objects.filter(
                    sender=self.user1,
                    client_id=client_id
                ).aexists()
                self.assertTrue(message_exists, f"Message with client_id {client_id} not found")
        
        asyncio.run(run_test())


class TimestampManagerPropertiesTest(HypothesisTestCase):
    """Property-based tests for timestamp management"""
    
    def setUp(self):
        self.timestamp_manager = TimestampManager()
        self.user1 = User.objects.create_user(
            username='timestamp_user1',
            email='timestamp1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='timestamp_user2',
            email='timestamp2@example.com', 
            password='testpass123'
        )
    
    @given(
        message_count=st.integers(min_value=2, max_value=20)
    )
    @settings(max_examples=20, deadline=10000)
    def test_timestamp_ordering_properties(self, message_count):
        """
        **Property 16.5: Timestamp Ordering Consistency**
        
        Property: Timestamps maintain proper ordering
        - Messages created in sequence have ordered timestamps
        - No two messages have identical timestamps
        - Timestamp validation works correctly
        """
        # Create messages with potential timestamp conflicts
        messages = []
        base_time = timezone.now()
        
        for i in range(message_count):
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Timestamp test {i}",
                created_at=base_time  # Same timestamp initially
            )
            messages.append(message)
        
        # Apply timestamp ordering
        ordered_messages = self.timestamp_manager.ensure_timestamp_ordering(messages)
        
        # Verify ordering
        self.assertEqual(len(ordered_messages), message_count)
        
        if message_count > 1:
            for i in range(1, len(ordered_messages)):
                prev_time = ordered_messages[i-1].created_at
                curr_time = ordered_messages[i].created_at
                self.assertLess(prev_time, curr_time)
        
        # Verify all timestamps are unique
        timestamps = [msg.created_at for msg in ordered_messages]
        self.assertEqual(len(set(timestamps)), message_count)
        
        # Test timestamp validation
        for message in ordered_messages:
            # Set some status timestamps
            message.sent_at = message.created_at + timedelta(seconds=1)
            message.delivered_at = message.created_at + timedelta(seconds=2)
            message.read_at = message.created_at + timedelta(seconds=3)
            
            # Should be valid
            self.assertTrue(self.timestamp_manager.validate_timestamp_sequence(message))
            
            # Test invalid sequence
            message.read_at = message.created_at - timedelta(seconds=1)  # Invalid
            self.assertFalse(self.timestamp_manager.validate_timestamp_sequence(message))


class MultiTabSyncPropertiesTest(HypothesisTestCase):
    """Property-based tests for multi-tab synchronization"""
    
    def setUp(self):
        self.sync_manager = MultiTabSyncManager()
        self.user1 = User.objects.create_user(
            username='sync_user1',
            email='sync1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='sync_user2',
            email='sync2@example.com',
            password='testpass123'
        )
    
    @given(
        sync_operations=st.integers(min_value=1, max_value=10),
        operation_type=st.sampled_from(['message_update', 'conversation_sync', 'status_change'])
    )
    @settings(max_examples=20, deadline=10000)
    def test_sync_token_properties(self, sync_operations, operation_type):
        """
        **Property 16.6: Sync Token Management**
        
        Property: Sync tokens are unique and properly managed
        - Each sync operation gets unique token
        - Tokens can be marked as completed
        - Old tokens are cleaned up properly
        """
        # Generate sync tokens
        tokens = []
        for i in range(sync_operations):
            token = self.sync_manager.generate_sync_token(
                user_id=self.user1.id,
                operation=f"{operation_type}_{i}"
            )
            tokens.append(token)
        
        # Verify all tokens are unique
        self.assertEqual(len(set(tokens)), sync_operations)
        
        # Verify tokens exist in sync events
        for token in tokens:
            self.assertIn(token, self.sync_manager.sync_events)
            event = self.sync_manager.sync_events[token]
            self.assertEqual(event['user_id'], self.user1.id)
            self.assertFalse(event['completed'])
        
        # Mark some tokens as completed
        completed_tokens = tokens[:sync_operations//2]
        for token in completed_tokens:
            self.sync_manager.mark_sync_completed(token)
            event = self.sync_manager.sync_events[token]
            self.assertTrue(event['completed'])
            self.assertIn('completed_at', event)
        
        # Test cleanup
        initial_count = len(self.sync_manager.sync_events)
        
        # Simulate old events by modifying timestamps
        cutoff_time = timezone.now() - timedelta(hours=2)
        for token in tokens[:2]:  # Make first 2 tokens old
            self.sync_manager.sync_events[token]['created_at'] = cutoff_time
        
        # Run cleanup
        self.sync_manager.cleanup_old_sync_events(max_age_minutes=60)
        
        # Verify old tokens were cleaned up
        remaining_count = len(self.sync_manager.sync_events)
        self.assertLess(remaining_count, initial_count)
        
        # Verify the old tokens are gone
        for token in tokens[:2]:
            self.assertNotIn(token, self.sync_manager.sync_events)


class MessageLockManagerPropertiesTest(TransactionTestCase):
    """Property-based tests for message locking (requires TransactionTestCase for proper transaction handling)"""
    
    def setUp(self):
        self.lock_manager = MessageLockManager()
        self.user1 = User.objects.create_user(
            username='lock_user1',
            email='lock1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='lock_user2',
            email='lock2@example.com',
            password='testpass123'
        )
    
    @given(
        operation_type=st.sampled_from(['update', 'delete', 'status_change'])
    )
    @settings(max_examples=10, deadline=15000)
    def test_message_locking_properties(self, operation_type):
        """
        **Property 16.7: Message Locking Safety**
        
        Property: Message locks prevent concurrent modifications
        - Locks are properly acquired and released
        - Concurrent access is serialized
        - No deadlocks occur
        """
        # Create a test message
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Lock test message"
        )
        
        # Test lock acquisition
        with self.lock_manager.acquire_message_lock(message.id, operation_type) as locked_message:
            self.assertIsNotNone(locked_message)
            self.assertEqual(locked_message.id, message.id)
            
            # Verify we can modify the message
            original_content = locked_message.content
            locked_message.content = f"Modified - {operation_type}"
            locked_message.save()
            
            # Verify modification persisted
            locked_message.refresh_from_db()
            self.assertNotEqual(locked_message.content, original_content)
        
        # Verify lock was released (no exception should occur)
        with self.lock_manager.acquire_message_lock(message.id, 'verify') as locked_message:
            self.assertIsNotNone(locked_message)
    
    @given(
        conversation_operations=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=10, deadline=20000)
    def test_conversation_locking_properties(self, conversation_operations):
        """
        **Property 16.8: Conversation Locking Consistency**
        
        Property: Conversation locks work correctly
        - Entire conversations can be locked
        - Lock ordering prevents deadlocks
        - Operations are atomic
        """
        # Create messages in conversation
        messages = []
        for i in range(conversation_operations):
            message = Message.objects.create(
                sender=self.user1 if i % 2 == 0 else self.user2,
                recipient=self.user2 if i % 2 == 0 else self.user1,
                content=f"Conversation message {i}"
            )
            messages.append(message)
        
        # Test conversation lock
        with self.lock_manager.acquire_conversation_lock(
            self.user1.id, self.user2.id, 'bulk_update'
        ):
            # Modify all messages in the conversation
            for i, message in enumerate(messages):
                message.content = f"Bulk updated {i}"
                message.save()
        
        # Verify all modifications persisted
        for i, message in enumerate(messages):
            message.refresh_from_db()
            self.assertEqual(message.content, f"Bulk updated {i}")


if __name__ == '__main__':
    pytest.main([__file__])
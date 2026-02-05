"""
Property-Based Tests for Concurrent Operation Safety

**Validates: Requirements 11.5**

This module contains property-based tests that verify the safety and correctness
of concurrent operations in the WhatsApp-like messaging system, ensuring that
race conditions are prevented and data integrity is maintained.

Requirements Coverage:
- 11.5: Concurrent operation safety with proper locking and atomicity
"""

import pytest
import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, IntegrityError, connection
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.extra.django import TestCase as HypothesisTestCase
from unittest.mock import patch, MagicMock
import logging

from .models import Message, UserStatus, QueuedMessage
from .message_persistence_manager import (
    MessagePersistenceManager, MessageLockManager
)
from .message_status_manager import MessageStatusManager

User = get_user_model()
logger = logging.getLogger(__name__)


class ConcurrentOperationSafetyTest(TransactionTestCase):
    """Property-based tests for concurrent operation safety"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user1 = User.objects.create_user(
            username='concurrent_user1',
            email='concurrent1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='concurrent_user2',
            email='concurrent2@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='concurrent_user3',
            email='concurrent3@example.com',
            password='testpass123'
        )
        
        self.persistence_manager = MessagePersistenceManager()
        self.status_manager = MessageStatusManager()
        self.lock_manager = MessageLockManager()
        
        # Ensure clean state
        Message.objects.all().delete()
        QueuedMessage.objects.all().delete()
    
    def tearDown(self):
        """Clean up after tests"""
        Message.objects.all().delete()
        QueuedMessage.objects.all().delete()
    
    @given(
        thread_count=st.integers(min_value=2, max_value=8),
        messages_per_thread=st.integers(min_value=2, max_value=10),
        content_base=st.text(min_size=5, max_size=50)
    )
    @settings(max_examples=10, deadline=30000)
    def test_concurrent_message_creation_safety(self, thread_count, messages_per_thread, content_base):
        """
        **Property 18.1: Concurrent Message Creation Safety**
        
        Property: Concurrent message creation operations are safe
        - No duplicate messages with same client_id
        - All messages are created successfully
        - Database integrity is maintained
        - No race conditions occur
        """
        def create_messages_in_thread(thread_id):
            """Create messages in a separate thread"""
            created_messages = []
            errors = []
            
            for i in range(messages_per_thread):
                try:
                    client_id = f"thread_{thread_id}_msg_{i}_{uuid.uuid4().hex[:8]}"
                    content = f"{content_base} - Thread {thread_id} Message {i}"
                    
                    # Use synchronous version for thread safety
                    message = Message.objects.create(
                        sender=self.user1,
                        recipient=self.user2,
                        content=content,
                        client_id=client_id,
                        status='pending'
                    )
                    created_messages.append(message)
                    
                except Exception as e:
                    errors.append(f"Thread {thread_id}, Message {i}: {str(e)}")
            
            return created_messages, errors
        
        # Execute concurrent message creation
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [
                executor.submit(create_messages_in_thread, thread_id)
                for thread_id in range(thread_count)
            ]
            
            all_created_messages = []
            all_errors = []
            
            for future in as_completed(futures):
                created_messages, errors = future.result()
                all_created_messages.extend(created_messages)
                all_errors.extend(errors)
        
        # Verify results
        expected_total = thread_count * messages_per_thread
        
        # Should have no errors
        if all_errors:
            self.fail(f"Concurrent creation errors: {all_errors}")
        
        # Should have created all expected messages
        self.assertEqual(len(all_created_messages), expected_total)
        
        # Verify all messages exist in database
        db_message_count = Message.objects.filter(sender=self.user1).count()
        self.assertEqual(db_message_count, expected_total)
        
        # Verify all client_ids are unique (no duplicates)
        client_ids = [msg.client_id for msg in all_created_messages]
        self.assertEqual(len(set(client_ids)), expected_total)
        
        # Verify database integrity
        for message in all_created_messages:
            db_message = Message.objects.get(id=message.id)
            self.assertEqual(db_message.client_id, message.client_id)
            self.assertEqual(db_message.content, message.content)
    
    @given(
        concurrent_updates=st.integers(min_value=3, max_value=10),
        status_sequence=st.lists(
            st.sampled_from(['sent', 'delivered', 'read']),
            min_size=2, max_size=4
        )
    )
    @settings(max_examples=8, deadline=25000)
    def test_concurrent_status_update_safety(self, concurrent_updates, status_sequence):
        """
        **Property 18.2: Concurrent Status Update Safety**
        
        Property: Concurrent status updates are safe and consistent
        - Status updates don't interfere with each other
        - Final status is valid and consistent
        - No lost updates occur
        - Timestamps are properly maintained
        """
        # Create a message to update
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content="Concurrent status test message",
            client_id=f"status_test_{uuid.uuid4().hex[:8]}",
            status='pending'
        )
        
        def update_status_in_thread(thread_id, target_status):
            """Update message status in a separate thread"""
            try:
                # Use database-level locking for safety
                with transaction.atomic():
                    locked_message = Message.objects.select_for_update().get(id=message.id)
                    
                    # Only update if transition is valid
                    current_status = locked_message.status
                    valid_transitions = {
                        'pending': ['sent', 'failed'],
                        'sent': ['delivered', 'failed'],
                        'delivered': ['read', 'failed'],
                        'read': [],  # Final state
                        'failed': ['pending', 'sent']  # Allow retry
                    }
                    
                    if target_status in valid_transitions.get(current_status, []):
                        locked_message.status = target_status
                        
                        # Set appropriate timestamp
                        current_time = timezone.now()
                        if target_status == 'sent' and not locked_message.sent_at:
                            locked_message.sent_at = current_time
                        elif target_status == 'delivered' and not locked_message.delivered_at:
                            locked_message.delivered_at = current_time
                        elif target_status == 'read' and not locked_message.read_at:
                            locked_message.read_at = current_time
                            locked_message.is_read = True
                        
                        locked_message.save()
                        return True, target_status, current_status
                    else:
                        return False, target_status, current_status
                        
            except Exception as e:
                return False, target_status, str(e)
        
        # Execute concurrent status updates
        with ThreadPoolExecutor(max_workers=concurrent_updates) as executor:
            # Create tasks with different target statuses
            futures = []
            for i in range(concurrent_updates):
                target_status = status_sequence[i % len(status_sequence)]
                future = executor.submit(update_status_in_thread, i, target_status)
                futures.append((future, target_status))
            
            results = []
            for future, target_status in futures:
                success, attempted_status, previous_status = future.result()
                results.append((success, attempted_status, previous_status))
        
        # Verify final state
        message.refresh_from_db()
        
        # At least one update should have succeeded
        successful_updates = [r for r in results if r[0]]
        self.assertGreater(len(successful_updates), 0)
        
        # Final status should be valid
        valid_statuses = ['pending', 'sent', 'delivered', 'read', 'failed']
        self.assertIn(message.status, valid_statuses)
        
        # Verify timestamp consistency
        timestamps = [message.created_at, message.sent_at, message.delivered_at, message.read_at]
        valid_timestamps = [ts for ts in timestamps if ts is not None]
        
        if len(valid_timestamps) > 1:
            # Timestamps should be in order
            for i in range(1, len(valid_timestamps)):
                self.assertLessEqual(valid_timestamps[i-1], valid_timestamps[i])
    
    @given(
        reader_count=st.integers(min_value=2, max_value=6),
        writer_count=st.integers(min_value=1, max_value=3),
        operation_count=st.integers(min_value=5, max_value=15)
    )
    @settings(max_examples=5, deadline=40000)
    def test_concurrent_read_write_safety(self, reader_count, writer_count, operation_count):
        """
        **Property 18.3: Concurrent Read-Write Operation Safety**
        
        Property: Concurrent read and write operations are safe
        - Readers don't interfere with writers
        - Writers don't corrupt data being read
        - Consistent view of data is maintained
        - No deadlocks occur
        """
        # Create initial messages
        initial_messages = []
        for i in range(operation_count):
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Read-write test message {i}",
                client_id=f"rw_test_{i}_{uuid.uuid4().hex[:8]}",
                status='pending'
            )
            initial_messages.append(message)
        
        read_results = []
        write_results = []
        errors = []
        
        def reader_thread(reader_id):
            """Read messages concurrently"""
            try:
                for _ in range(operation_count // 2):
                    # Read conversation messages
                    messages = Message.objects.filter(
                        sender=self.user1,
                        recipient=self.user2
                    ).order_by('created_at')
                    
                    message_data = []
                    for msg in messages:
                        message_data.append({
                            'id': msg.id,
                            'content': msg.content,
                            'status': msg.status,
                            'client_id': msg.client_id
                        })
                    
                    read_results.append((reader_id, len(message_data), message_data))
                    time.sleep(0.01)  # Small delay to allow interleaving
                    
            except Exception as e:
                errors.append(f"Reader {reader_id}: {str(e)}")
        
        def writer_thread(writer_id):
            """Write/update messages concurrently"""
            try:
                for i in range(operation_count // writer_count):
                    # Create new message
                    message = Message.objects.create(
                        sender=self.user2,  # Different sender
                        recipient=self.user1,
                        content=f"Writer {writer_id} message {i}",
                        client_id=f"writer_{writer_id}_msg_{i}_{uuid.uuid4().hex[:8]}",
                        status='pending'
                    )
                    
                    # Update an existing message
                    if initial_messages:
                        target_message = initial_messages[i % len(initial_messages)]
                        with transaction.atomic():
                            locked_message = Message.objects.select_for_update().get(
                                id=target_message.id
                            )
                            locked_message.content = f"Updated by writer {writer_id}"
                            locked_message.save()
                    
                    write_results.append((writer_id, message.id))
                    time.sleep(0.01)  # Small delay to allow interleaving
                    
            except Exception as e:
                errors.append(f"Writer {writer_id}: {str(e)}")
        
        # Execute concurrent read-write operations
        threads = []
        
        # Start reader threads
        for reader_id in range(reader_count):
            thread = threading.Thread(target=reader_thread, args=(reader_id,))
            threads.append(thread)
            thread.start()
        
        # Start writer threads
        for writer_id in range(writer_count):
            thread = threading.Thread(target=writer_thread, args=(writer_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        # Verify results
        if errors:
            self.fail(f"Concurrent read-write errors: {errors}")
        
        # Should have read results from all readers
        self.assertGreaterEqual(len(read_results), reader_count)
        
        # Should have write results from all writers
        self.assertGreaterEqual(len(write_results), writer_count)
        
        # Verify database consistency
        final_message_count = Message.objects.count()
        expected_minimum = len(initial_messages)  # At least initial messages
        self.assertGreaterEqual(final_message_count, expected_minimum)
        
        # Verify no data corruption
        for message in Message.objects.all():
            self.assertIsNotNone(message.content)
            self.assertIsNotNone(message.client_id)
            self.assertIn(message.status, ['pending', 'sent', 'delivered', 'read', 'failed'])
    
    @given(
        queue_operations=st.integers(min_value=3, max_value=8),
        process_operations=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=5, deadline=30000)
    def test_concurrent_queue_operations_safety(self, queue_operations, process_operations):
        """
        **Property 18.4: Concurrent Queue Operations Safety**
        
        Property: Concurrent queue operations are safe
        - Messages are queued without conflicts
        - Queue processing doesn't interfere with queuing
        - No messages are lost or duplicated
        - Queue state remains consistent
        """
        def queue_messages_thread(thread_id):
            """Queue messages in a separate thread"""
            queued_messages = []
            errors = []
            
            try:
                for i in range(queue_operations):
                    queued_msg = QueuedMessage.objects.create(
                        sender=self.user1,
                        recipient=self.user2,
                        content=f"Queued message {thread_id}-{i}",
                        client_id=f"queue_{thread_id}_{i}_{uuid.uuid4().hex[:8]}",
                        queue_type='outgoing',
                        priority=2
                    )
                    queued_messages.append(queued_msg)
                    time.sleep(0.005)  # Small delay
                    
            except Exception as e:
                errors.append(f"Queue thread {thread_id}: {str(e)}")
            
            return queued_messages, errors
        
        def process_queue_thread(processor_id):
            """Process queued messages in a separate thread"""
            processed_messages = []
            errors = []
            
            try:
                for _ in range(process_operations):
                    # Get unprocessed messages
                    with transaction.atomic():
                        pending_messages = QueuedMessage.objects.filter(
                            is_processed=False
                        ).select_for_update()[:2]  # Process 2 at a time
                        
                        for msg in pending_messages:
                            # Simulate processing
                            msg.is_processed = True
                            msg.processed_at = timezone.now()
                            msg.save()
                            processed_messages.append(msg.id)
                    
                    time.sleep(0.01)  # Processing delay
                    
            except Exception as e:
                errors.append(f"Processor {processor_id}: {str(e)}")
            
            return processed_messages, errors
        
        # Execute concurrent queue operations
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Start queue operations
            queue_futures = [
                executor.submit(queue_messages_thread, i)
                for i in range(3)  # 3 queue threads
            ]
            
            # Start processing operations (with slight delay)
            time.sleep(0.1)
            process_futures = [
                executor.submit(process_queue_thread, i)
                for i in range(2)  # 2 processor threads
            ]
            
            # Collect results
            all_queued = []
            all_processed = []
            all_errors = []
            
            for future in queue_futures:
                queued_messages, errors = future.result()
                all_queued.extend(queued_messages)
                all_errors.extend(errors)
            
            for future in process_futures:
                processed_messages, errors = future.result()
                all_processed.extend(processed_messages)
                all_errors.extend(errors)
        
        # Verify results
        if all_errors:
            self.fail(f"Concurrent queue operation errors: {all_errors}")
        
        # Verify all messages were queued
        total_queued = 3 * queue_operations  # 3 threads * operations per thread
        self.assertEqual(len(all_queued), total_queued)
        
        # Verify database consistency
        db_queue_count = QueuedMessage.objects.count()
        self.assertEqual(db_queue_count, total_queued)
        
        # Verify no duplicate client_ids
        client_ids = [msg.client_id for msg in all_queued]
        self.assertEqual(len(set(client_ids)), total_queued)
        
        # Verify processing consistency
        processed_count = QueuedMessage.objects.filter(is_processed=True).count()
        unprocessed_count = QueuedMessage.objects.filter(is_processed=False).count()
        self.assertEqual(processed_count + unprocessed_count, total_queued)
        
        # Verify processed messages have timestamps
        processed_messages = QueuedMessage.objects.filter(is_processed=True)
        for msg in processed_messages:
            self.assertIsNotNone(msg.processed_at)
    
    @given(
        lock_contention_level=st.integers(min_value=2, max_value=6)
    )
    @settings(max_examples=5, deadline=25000)
    def test_database_lock_contention_safety(self, lock_contention_level):
        """
        **Property 18.5: Database Lock Contention Safety**
        
        Property: Database locks handle contention safely
        - High contention doesn't cause deadlocks
        - Operations complete successfully under contention
        - Lock ordering prevents circular waits
        - Performance degrades gracefully
        """
        # Create messages for lock contention testing
        test_messages = []
        for i in range(lock_contention_level):
            message = Message.objects.create(
                sender=self.user1,
                recipient=self.user2,
                content=f"Lock contention test {i}",
                client_id=f"lock_test_{i}_{uuid.uuid4().hex[:8]}",
                status='pending'
            )
            test_messages.append(message)
        
        def contend_for_locks(thread_id):
            """Create lock contention by accessing multiple messages"""
            operations_completed = 0
            errors = []
            
            try:
                for operation in range(3):  # 3 operations per thread
                    # Access messages in consistent order to prevent deadlocks
                    message_ids = sorted([msg.id for msg in test_messages])
                    
                    with transaction.atomic():
                        # Lock multiple messages in order
                        locked_messages = Message.objects.filter(
                            id__in=message_ids[:2]  # Lock first 2 messages
                        ).select_for_update().order_by('id')
                        
                        # Perform operations on locked messages
                        for msg in locked_messages:
                            msg.content = f"Modified by thread {thread_id} op {operation}"
                            msg.save()
                            operations_completed += 1
                    
                    time.sleep(0.01)  # Small delay between operations
                    
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
            
            return operations_completed, errors
        
        # Execute high contention scenario
        with ThreadPoolExecutor(max_workers=lock_contention_level) as executor:
            futures = [
                executor.submit(contend_for_locks, thread_id)
                for thread_id in range(lock_contention_level)
            ]
            
            all_operations = 0
            all_errors = []
            
            for future in as_completed(futures, timeout=20):  # 20 second timeout
                operations, errors = future.result()
                all_operations += operations
                all_errors.extend(errors)
        
        # Verify results
        if all_errors:
            self.fail(f"Lock contention errors: {all_errors}")
        
        # All operations should complete successfully
        expected_operations = lock_contention_level * 3 * 2  # threads * ops * messages
        self.assertEqual(all_operations, expected_operations)
        
        # Verify database consistency
        for message in test_messages:
            message.refresh_from_db()
            self.assertIsNotNone(message.content)
            # Content should have been modified
            self.assertIn("Modified by thread", message.content)


if __name__ == '__main__':
    pytest.main([__file__])
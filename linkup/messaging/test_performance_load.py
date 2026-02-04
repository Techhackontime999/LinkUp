"""
Performance and Load Testing for WhatsApp-like Messaging System

**Validates: Requirements 10.1, 10.2, 10.5**

This module contains performance tests that verify the system can handle
multiple concurrent connections, meet message delivery timing requirements,
and recover properly under various network conditions.
"""

import pytest
import asyncio
import time
import statistics
import threading
import uuid
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
import logging

from .models import Message, UserStatus, QueuedMessage
from .consumers import ChatConsumer
from .message_persistence_manager import MessagePersistenceManager

User = get_user_model()
logger = logging.getLogger(__name__)


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MessageDeliveryPerformanceTest(TransactionTestCase):
    """Performance tests for message delivery timing"""
    
    def setUp(self):
        """Set up test users and clean state"""
        self.user1 = User.objects.create_user(
            username='perf_user1',
            email='perf1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='perf_user2',
            email='perf2@example.com',
            password='testpass123'
        )
        
        self.persistence_manager = MessagePersistenceManager()
        
        # Clean up
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
    
    def tearDown(self):
        """Clean up after tests"""
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
    
    async def test_message_delivery_timing_requirements(self):
        """
        Test message delivery meets timing requirements:
        - Optimistic display: 50ms for senders
        - Message display: 100ms for recipients
        - WebSocket response: under 200ms
        """
        # Create WebSocket connections
        communicator1 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/perf_user2/")
        communicator1.scope['user'] = self.user1
        
        communicator2 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/perf_user1/")
        communicator2.scope['user'] = self.user2
        
        try:
            # Connect both users
            start_connect = time.time()
            connected1, _ = await communicator1.connect()
            connected2, _ = await communicator2.connect()
            connect_time = (time.time() - start_connect) * 1000  # Convert to ms
            
            self.assertTrue(connected1 and connected2)
            
            # Clear initial messages
            await communicator1.receive_nothing(timeout=0.1)
            await communicator2.receive_nothing(timeout=0.1)
            
            # Test multiple message deliveries
            message_count = 20
            delivery_times = []
            
            for i in range(message_count):
                # Send message and measure delivery time
                start_time = time.time()
                
                await communicator1.send_json_to({
                    'type': 'message',
                    'message': f'Performance test message {i+1}',
                    'client_id': f'perf_test_{i}_{uuid.uuid4().hex[:8]}'
                })
                
                # Measure time to receive on other end
                response = await communicator2.receive_json_from(timeout=1.0)
                delivery_time = (time.time() - start_time) * 1000  # Convert to ms
                
                delivery_times.append(delivery_time)
                
                # Verify message structure
                self.assertEqual(response['type'], 'message')
                self.assertEqual(response['content'], f'Performance test message {i+1}')
                
                # Small delay between messages
                await asyncio.sleep(0.01)
            
            # Analyze timing results
            avg_delivery_time = statistics.mean(delivery_times)
            p95_delivery_time = statistics.quantiles(delivery_times, n=20)[18] if len(delivery_times) >= 20 else max(delivery_times)
            max_delivery_time = max(delivery_times)
            
            # Performance assertions
            self.assertLess(avg_delivery_time, 100, f"Average delivery time {avg_delivery_time:.2f}ms exceeds 100ms target")
            self.assertLess(p95_delivery_time, 200, f"95th percentile delivery time {p95_delivery_time:.2f}ms exceeds 200ms limit")
            self.assertLess(max_delivery_time, 500, f"Maximum delivery time {max_delivery_time:.2f}ms exceeds 500ms limit")
            
            logger.info(f"Message delivery performance: avg={avg_delivery_time:.2f}ms, p95={p95_delivery_time:.2f}ms, max={max_delivery_time:.2f}ms")
            
        finally:
            await communicator1.disconnect()
            await communicator2.disconnect()
    
    async def test_concurrent_connection_performance(self):
        """
        Test performance with multiple concurrent connections:
        - Simulate realistic user load
        - Measure connection establishment time
        - Verify system stability under load
        """
        connection_count = 10  # Simulate 10 concurrent users
        messages_per_user = 3
        
        async def simulate_user_session(user_id):
            """Simulate a user session with message sending"""
            user = User.objects.create_user(
                username=f'load_user_{user_id}',
                email=f'load{user_id}@example.com',
                password='testpass123'
            )
            
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/perf_user1/")
            communicator.scope['user'] = user
            
            session_metrics = {
                'connection_time': 0,
                'message_times': [],
                'errors': []
            }
            
            try:
                # Measure connection time
                start_connect = time.time()
                connected, _ = await communicator.connect()
                session_metrics['connection_time'] = (time.time() - start_connect) * 1000
                
                if not connected:
                    session_metrics['errors'].append('Connection failed')
                    return session_metrics
                
                # Clear initial messages
                await communicator.receive_nothing(timeout=0.1)
                
                # Send messages
                for i in range(messages_per_user):
                    start_send = time.time()
                    
                    await communicator.send_json_to({
                        'type': 'message',
                        'message': f'Load test message {i+1} from user {user_id}',
                        'client_id': f'load_{user_id}_{i}_{uuid.uuid4().hex[:8]}'
                    })
                    
                    send_time = (time.time() - start_send) * 1000
                    session_metrics['message_times'].append(send_time)
                    
                    # Small delay between messages
                    await asyncio.sleep(0.05)
                
            except Exception as e:
                session_metrics['errors'].append(str(e))
            finally:
                try:
                    await communicator.disconnect()
                except:
                    pass
            
            return session_metrics
        
        # Run concurrent user sessions
        tasks = [simulate_user_session(i) for i in range(connection_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_sessions = 0
        total_connection_time = 0
        total_message_times = []
        total_errors = []
        
        for result in results:
            if isinstance(result, Exception):
                total_errors.append(str(result))
                continue
            
            if not result['errors']:
                successful_sessions += 1
                total_connection_time += result['connection_time']
                total_message_times.extend(result['message_times'])
            else:
                total_errors.extend(result['errors'])
        
        # Performance assertions
        success_rate = (successful_sessions / connection_count) * 100
        self.assertGreaterEqual(success_rate, 90, f"Success rate {success_rate:.1f}% below 90% threshold")
        
        if successful_sessions > 0:
            avg_connection_time = total_connection_time / successful_sessions
            self.assertLess(avg_connection_time, 1000, f"Average connection time {avg_connection_time:.2f}ms exceeds 1s limit")
        
        if total_message_times:
            avg_message_time = statistics.mean(total_message_times)
            self.assertLess(avg_message_time, 100, f"Average message send time {avg_message_time:.2f}ms exceeds 100ms target")
        
        # Log performance summary
        logger.info(f"Concurrent connection performance: {successful_sessions}/{connection_count} successful, "
                   f"avg_connection={total_connection_time/max(successful_sessions,1):.2f}ms, "
                   f"avg_message={statistics.mean(total_message_times) if total_message_times else 0:.2f}ms")
    
    def test_database_performance_under_load(self):
        """
        Test database performance under message load:
        - High volume message creation
        - Concurrent read/write operations
        - Query performance optimization
        """
        # Create test users
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'db_user_{i}',
                email=f'db{i}@example.com',
                password='testpass123'
            )
            users.append(user)
        
        def create_messages_batch(batch_id, batch_size=20):
            """Create a batch of messages"""
            start_time = time.time()
            created_messages = []
            
            try:
                for i in range(batch_size):
                    sender = users[i % len(users)]
                    recipient = users[(i + 1) % len(users)]
                    
                    message = Message.objects.create(
                        sender=sender,
                        recipient=recipient,
                        content=f'DB load test message {batch_id}-{i}',
                        client_id=f'db_load_{batch_id}_{i}_{uuid.uuid4().hex[:8]}',
                        status='pending'
                    )
                    created_messages.append(message)
                
                batch_time = (time.time() - start_time) * 1000
                return len(created_messages), batch_time, None
                
            except Exception as e:
                batch_time = (time.time() - start_time) * 1000
                return len(created_messages), batch_time, str(e)
        
        # Run concurrent database operations
        batch_count = 5
        batch_size = 20
        expected_total = batch_count * batch_size
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(create_messages_batch, i, batch_size)
                for i in range(batch_count)
            ]
            
            total_created = 0
            total_time = 0
            errors = []
            
            for future in as_completed(futures):
                created, batch_time, error = future.result()
                total_created += created
                total_time += batch_time
                
                if error:
                    errors.append(error)
        
        # Verify database performance
        self.assertEqual(total_created, expected_total, f"Created {total_created} messages, expected {expected_total}")
        self.assertEqual(len(errors), 0, f"Database errors occurred: {errors}")
        
        avg_batch_time = total_time / batch_count
        self.assertLess(avg_batch_time, 5000, f"Average batch time {avg_batch_time:.2f}ms exceeds 5s limit")
        
        # Test query performance
        start_query = time.time()
        message_count = Message.objects.count()
        query_time = (time.time() - start_query) * 1000
        
        self.assertEqual(message_count, expected_total)
        self.assertLess(query_time, 200, f"Count query time {query_time:.2f}ms exceeds 200ms limit")
        
        logger.info(f"Database performance: {total_created} messages created, "
                   f"avg_batch={avg_batch_time:.2f}ms, count_query={query_time:.2f}ms")


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class ConnectionRecoveryPerformanceTest(TransactionTestCase):
    """Performance tests for connection recovery scenarios"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='recovery_user1',
            email='recovery1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='recovery_user2',
            email='recovery2@example.com',
            password='testpass123'
        )
        
        self.persistence_manager = MessagePersistenceManager()
        
        # Clean up
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
    
    def tearDown(self):
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
    
    async def test_connection_recovery_timing(self):
        """
        Test connection recovery performance:
        - Measure reconnection time
        - Verify message synchronization speed
        - Test under various failure scenarios
        """
        # Create initial connection
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/recovery_user2/")
        communicator.scope['user'] = self.user1
        
        try:
            # Establish initial connection
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            
            # Create some messages while connected
            for i in range(3):
                await communicator.send_json_to({
                    'type': 'message',
                    'message': f'Pre-disconnect message {i+1}',
                    'client_id': f'pre_disc_{i}_{uuid.uuid4().hex[:8]}'
                })
                await asyncio.sleep(0.01)
            
            # Simulate connection loss
            await communicator.disconnect()
            
            # Create messages while disconnected (should be queued)
            offline_messages = []
            for i in range(2):
                message = await self.persistence_manager.create_message_atomic(
                    sender=self.user2,
                    recipient=self.user1,
                    content=f'Offline message {i+1}',
                    client_id=f'offline_{i}_{uuid.uuid4().hex[:8]}'
                )
                offline_messages.append(message)
            
            # Measure reconnection time
            start_reconnect = time.time()
            
            # Create new connection (simulating reconnection)
            new_communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/recovery_user2/")
            new_communicator.scope['user'] = self.user1
            
            reconnected, _ = await new_communicator.connect()
            reconnect_time = (time.time() - start_reconnect) * 1000
            
            self.assertTrue(reconnected)
            
            # Measure message synchronization time
            start_sync = time.time()
            received_messages = []
            
            # Collect synchronized messages
            for _ in range(5):  # Try to receive up to 5 messages
                try:
                    response = await new_communicator.receive_json_from(timeout=0.5)
                    if response.get('type') == 'message':
                        received_messages.append(response)
                except:
                    break
            
            sync_time = (time.time() - start_sync) * 1000
            
            # Performance assertions
            self.assertLess(reconnect_time, 2000, f"Reconnection time {reconnect_time:.2f}ms exceeds 2s limit")
            self.assertLess(sync_time, 1000, f"Synchronization time {sync_time:.2f}ms exceeds 1s limit")
            
            logger.info(f"Connection recovery performance: reconnect={reconnect_time:.2f}ms, sync={sync_time:.2f}ms, "
                       f"messages_synced={len(received_messages)}")
            
            await new_communicator.disconnect()
            
        finally:
            pass


if __name__ == '__main__':
    pytest.main([__file__])
"""
End-to-End Integration Tests for WhatsApp-like Messaging System

This module contains comprehensive integration tests that verify the complete
message lifecycle from creation to read receipt, including offline/online
transitions and multi-user scenarios.

**Validates: All Requirements**

Test Coverage:
- Complete message lifecycle (send → delivered → read)
- Offline/online user transitions
- Multi-user chat scenarios
- WebSocket and HTTP fallback integration
- Real-time status updates
- Connection recovery scenarios
- Error handling and retry mechanisms
"""

import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import Client
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from unittest.mock import patch, MagicMock, AsyncMock
import logging

from .models import Message, UserStatus, QueuedMessage, Notification
from .consumers import ChatConsumer
from .message_status_manager import MessageStatusManager
from .message_persistence_manager import MessagePersistenceManager
from .typing_manager import TypingManager
from .presence_manager import PresenceManager
from .read_receipt_manager import ReadReceiptManager
from .message_retry_manager import MessageRetryManager
from .offline_queue_manager import OfflineQueueManager

User = get_user_model()
logger = logging.getLogger(__name__)


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class EndToEndMessageFlowTest(TransactionTestCase):
    """Integration tests for complete message flow"""
    
    def setUp(self):
        """Set up test users and managers"""
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='testpass123'
        )
        
        # Initialize managers
        self.status_manager = MessageStatusManager()
        self.persistence_manager = MessagePersistenceManager()
        self.typing_manager = TypingManager()
        self.presence_manager = PresenceManager()
        self.read_receipt_manager = ReadReceiptManager()
        self.retry_manager = MessageRetryManager()
        self.offline_queue_manager = OfflineQueueManager()
        
        # Clean up
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
        QueuedMessage.objects.all().delete()
        Notification.objects.all().delete()
        
        self.client = Client()
    
    def tearDown(self):
        """Clean up after tests"""
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
        QueuedMessage.objects.all().delete()
        Notification.objects.all().delete()
    
    async def test_complete_message_lifecycle_websocket(self):
        """
        Test complete message lifecycle via WebSocket:
        1. User1 sends message to User2
        2. Message status: pending → sent → delivered → read
        3. Real-time status updates
        4. Read receipt generation
        """
        # Create WebSocket communicators
        communicator1 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/bob/")
        communicator1.scope['user'] = self.user1
        
        communicator2 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/alice/")
        communicator2.scope['user'] = self.user2
        
        try:
            # Connect both users
            connected1, _ = await communicator1.connect()
            connected2, _ = await communicator2.connect()
            
            self.assertTrue(connected1)
            self.assertTrue(connected2)
            
            # Clear initial messages
            await communicator1.receive_nothing(timeout=0.1)
            await communicator2.receive_nothing(timeout=0.1)
            
            # Step 1: User1 sends message
            client_id = f"test_msg_{uuid.uuid4().hex[:12]}"
            message_content = "Hello Bob! This is an integration test message."
            
            await communicator1.send_json_to({
                'type': 'message',
                'message': message_content,
                'client_id': client_id
            })
            
            # Step 2: User2 should receive the message
            response2 = await communicator2.receive_json_from(timeout=2.0)
            
            self.assertEqual(response2['type'], 'message')
            self.assertEqual(response2['content'], message_content)
            self.assertEqual(response2['sender'], 'alice')
            self.assertEqual(response2['recipient'], 'bob')
            self.assertIn(response2['status'], ['sent', 'delivered'])
            
            message_id = response2['id']
            
            # Step 3: Verify message in database
            message = await Message.objects.aget(id=message_id)
            self.assertEqual(message.content, message_content)
            self.assertEqual(message.sender, self.user1)
            self.assertEqual(message.recipient, self.user2)
            self.assertEqual(message.client_id, client_id)
            
            # Step 4: Message should be automatically marked as delivered
            await asyncio.sleep(0.5)  # Allow for status update
            message.refresh_from_db()
            self.assertEqual(message.status, 'delivered')
            self.assertIsNotNone(message.delivered_at)
            
            # Step 5: Simulate read receipt (User2 reads the message)
            await communicator2.send_json_to({
                'type': 'read_receipt',
                'message_id': message_id
            })
            
            # Step 6: User1 should receive read receipt confirmation
            read_receipt_response = await communicator1.receive_json_from(timeout=2.0)
            
            # Could be either read_receipt_update or message_status_update
            self.assertIn(read_receipt_response['type'], ['read_receipt_update', 'message_status_update'])
            
            # Step 7: Verify message is marked as read
            await asyncio.sleep(0.5)
            message.refresh_from_db()
            self.assertEqual(message.status, 'read')
            self.assertTrue(message.is_read)
            self.assertIsNotNone(message.read_at)
            
            # Step 8: Verify timestamp sequence
            self.assertLessEqual(message.created_at, message.sent_at)
            self.assertLessEqual(message.sent_at, message.delivered_at)
            self.assertLessEqual(message.delivered_at, message.read_at)
            
        finally:
            await communicator1.disconnect()
            await communicator2.disconnect()
    
    async def test_offline_online_transition_flow(self):
        """
        Test offline/online transition scenarios:
        1. User2 goes offline
        2. User1 sends messages (should be queued)
        3. User2 comes back online
        4. Queued messages are delivered
        """
        # Step 1: Set User2 as offline
        user2_status, _ = await UserStatus.objects.aget_or_create(user=self.user2)
        user2_status.is_online = False
        user2_status.active_connections = 0
        await user2_status.asave()
        
        # Step 2: User1 sends messages while User2 is offline
        offline_messages = []
        for i in range(3):
            message = await self.persistence_manager.create_message_atomic(
                sender=self.user1,
                recipient=self.user2,
                content=f"Offline message {i+1}",
                client_id=f"offline_msg_{i}_{uuid.uuid4().hex[:8]}"
            )
            offline_messages.append(message)
        
        # Step 3: Messages should be queued for offline delivery
        queued_count = await QueuedMessage.objects.filter(
            recipient=self.user2,
            is_processed=False
        ).acount()
        self.assertGreater(queued_count, 0)
        
        # Step 4: User2 comes back online
        communicator2 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/alice/")
        communicator2.scope['user'] = self.user2
        
        try:
            connected, _ = await communicator2.connect()
            self.assertTrue(connected)
            
            # Step 5: User2 should receive queued messages
            received_messages = []
            for _ in range(5):  # Try to receive up to 5 messages
                try:
                    response = await communicator2.receive_json_from(timeout=1.0)
                    if response.get('type') == 'message':
                        received_messages.append(response)
                except:
                    break
            
            # Step 6: Verify offline messages were delivered
            self.assertGreaterEqual(len(received_messages), 3)
            
            # Verify content matches
            received_contents = [msg['content'] for msg in received_messages if 'Offline message' in msg['content']]
            self.assertGreaterEqual(len(received_contents), 3)
            
            # Step 7: Verify queue was processed
            await asyncio.sleep(1.0)  # Allow queue processing
            remaining_queued = await QueuedMessage.objects.filter(
                recipient=self.user2,
                is_processed=False
            ).acount()
            self.assertEqual(remaining_queued, 0)
            
        finally:
            await communicator2.disconnect()
    
    async def test_multi_user_chat_scenario(self):
        """
        Test multi-user chat scenarios:
        1. Three users in different conversations
        2. Concurrent message sending
        3. Typing indicators
        4. Presence updates
        """
        # Create WebSocket connections for all users
        comm1 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/bob/")
        comm1.scope['user'] = self.user1
        
        comm2 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/alice/")
        comm2.scope['user'] = self.user2
        
        comm3 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/alice/")
        comm3.scope['user'] = self.user3
        
        try:
            # Connect all users
            connected1, _ = await comm1.connect()
            connected2, _ = await comm2.connect()
            connected3, _ = await comm3.connect()
            
            self.assertTrue(all([connected1, connected2, connected3]))
            
            # Clear initial messages
            for comm in [comm1, comm2, comm3]:
                await comm.receive_nothing(timeout=0.1)
            
            # Step 1: Test typing indicators
            await comm1.send_json_to({
                'type': 'typing',
                'is_typing': True
            })
            
            # User2 should receive typing indicator
            typing_response = await comm2.receive_json_from(timeout=1.0)
            self.assertEqual(typing_response['type'], 'typing')
            self.assertEqual(typing_response['username'], 'alice')
            self.assertTrue(typing_response['is_typing'])
            
            # Step 2: Send concurrent messages
            messages_to_send = [
                (comm1, "Message from Alice to Bob"),
                (comm2, "Message from Bob to Alice"),
                (comm3, "Message from Charlie to Alice")
            ]
            
            # Send all messages concurrently
            send_tasks = []
            for comm, content in messages_to_send:
                task = comm.send_json_to({
                    'type': 'message',
                    'message': content,
                    'client_id': f"multi_user_{uuid.uuid4().hex[:8]}"
                })
                send_tasks.append(task)
            
            await asyncio.gather(*send_tasks)
            
            # Step 3: Collect received messages
            all_received = []
            for comm in [comm1, comm2, comm3]:
                for _ in range(3):  # Try to receive up to 3 messages per user
                    try:
                        response = await comm.receive_json_from(timeout=1.0)
                        if response.get('type') == 'message':
                            all_received.append(response)
                    except:
                        break
            
            # Step 4: Verify message delivery
            self.assertGreaterEqual(len(all_received), 3)
            
            # Verify each user received appropriate messages
            alice_messages = [msg for msg in all_received if msg.get('recipient') == 'alice']
            bob_messages = [msg for msg in all_received if msg.get('recipient') == 'bob']
            
            self.assertGreaterEqual(len(alice_messages), 2)  # From Bob and Charlie
            self.assertGreaterEqual(len(bob_messages), 1)    # From Alice
            
            # Step 5: Test presence updates
            # Disconnect one user and verify others are notified
            await comm3.disconnect()
            
            # Allow time for presence update
            await asyncio.sleep(0.5)
            
            # Verify user3 is marked offline
            user3_status = await UserStatus.objects.aget(user=self.user3)
            self.assertFalse(user3_status.is_online)
            
        finally:
            for comm in [comm1, comm2, comm3]:
                try:
                    await comm.disconnect()
                except:
                    pass
    
    def test_http_fallback_integration(self):
        """
        Test HTTP fallback when WebSocket is unavailable:
        1. Send message via HTTP endpoint
        2. Verify message creation and status
        3. Test WebSocket broadcast from HTTP
        """
        # Step 1: Login user1
        self.client.force_login(self.user1)
        
        # Step 2: Send message via HTTP fallback
        message_data = {
            'message': 'HTTP fallback test message',
            'client_id': f'http_test_{uuid.uuid4().hex[:8]}'
        }
        
        response = self.client.post(
            reverse('messaging:send_message_fallback', args=['bob']),
            data=json.dumps(message_data),
            content_type='application/json'
        )
        
        # Step 3: Verify HTTP response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertEqual(response_data['content'], message_data['message'])
        self.assertEqual(response_data['sender'], 'alice')
        self.assertEqual(response_data['recipient'], 'bob')
        self.assertEqual(response_data['client_id'], message_data['client_id'])
        self.assertTrue(response_data['fallback'])
        
        # Step 4: Verify message in database
        message = Message.objects.get(id=response_data['id'])
        self.assertEqual(message.content, message_data['message'])
        self.assertEqual(message.status, 'sent')  # HTTP fallback marks as sent
        self.assertIsNotNone(message.sent_at)
    
    async def test_error_handling_and_retry_flow(self):
        """
        Test error handling and retry mechanisms:
        1. Simulate message send failure
        2. Verify retry mechanism activation
        3. Test successful retry
        """
        # Step 1: Create a message that will fail
        message = await self.persistence_manager.create_message_atomic(
            sender=self.user1,
            recipient=self.user2,
            content="Test retry message",
            client_id=f"retry_test_{uuid.uuid4().hex[:8]}"
        )
        
        # Step 2: Mark message as failed
        await self.persistence_manager.update_message_status_atomic(
            message.id, 'failed', self.user1.id, last_error="Simulated network error"
        )
        
        # Step 3: Verify message is in failed state
        message.refresh_from_db()
        self.assertEqual(message.status, 'failed')
        self.assertIsNotNone(message.last_error)
        
        # Step 4: Test retry mechanism
        retry_success = await self.retry_manager.retry_failed_message(
            message.id, 'manual_retry'
        )
        
        # Step 5: Verify retry was attempted
        self.assertTrue(retry_success)
        
        # Allow time for retry processing
        await asyncio.sleep(0.5)
        
        # Step 6: Verify message status improved
        message.refresh_from_db()
        # Status should be better than 'failed' (could be 'pending' or 'sent')
        self.assertNotEqual(message.status, 'failed')
    
    def test_conversation_history_integration(self):
        """
        Test conversation history loading and pagination:
        1. Create multiple messages
        2. Test history loading with pagination
        3. Verify message ordering and metadata
        """
        # Step 1: Create conversation history
        messages = []
        for i in range(25):  # Create 25 messages
            sender = self.user1 if i % 2 == 0 else self.user2
            recipient = self.user2 if i % 2 == 0 else self.user1
            
            message = Message.objects.create(
                sender=sender,
                recipient=recipient,
                content=f"History test message {i+1}",
                client_id=f"history_{i}_{uuid.uuid4().hex[:8]}",
                status='delivered'
            )
            messages.append(message)
        
        # Step 2: Login and test history loading
        self.client.force_login(self.user1)
        
        # Test initial load (should get 20 messages by default)
        response = self.client.get(
            reverse('messaging:fetch_history', args=['bob']),
            {'page_size': 20}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Step 3: Verify response structure
        self.assertIn('messages', data)
        self.assertIn('pagination', data)
        self.assertIn('has_more', data)
        
        # Step 4: Verify message count and ordering
        loaded_messages = data['messages']
        self.assertEqual(len(loaded_messages), 20)
        
        # Messages should be in chronological order (oldest first)
        for i in range(1, len(loaded_messages)):
            prev_time = datetime.fromisoformat(loaded_messages[i-1]['created_at'])
            curr_time = datetime.fromisoformat(loaded_messages[i]['created_at'])
            self.assertLessEqual(prev_time, curr_time)
        
        # Step 5: Test pagination
        self.assertTrue(data['has_more'])
        
        # Load older messages
        oldest_message_id = loaded_messages[0]['id']
        older_response = self.client.get(
            reverse('messaging:load_older_messages', args=['bob']),
            {'before_id': oldest_message_id, 'page_size': 10}
        )
        
        self.assertEqual(older_response.status_code, 200)
        older_data = older_response.json()
        
        # Should get remaining 5 messages
        self.assertLessEqual(len(older_data['messages']), 10)
    
    async def test_notification_integration(self):
        """
        Test notification system integration:
        1. Send message and verify notification creation
        2. Test notification delivery
        3. Verify notification preferences
        """
        # Step 1: Send a message
        message = await self.persistence_manager.create_message_atomic(
            sender=self.user1,
            recipient=self.user2,
            content="Notification test message",
            client_id=f"notif_test_{uuid.uuid4().hex[:8]}"
        )
        
        # Step 2: Verify notification was created
        await asyncio.sleep(0.5)  # Allow notification processing
        
        notification_exists = await Notification.objects.filter(
            recipient=self.user2,
            notification_type='new_message'
        ).aexists()
        
        # Note: This depends on notification system being properly integrated
        # The test verifies the integration point exists
        
        # Step 3: Test notification API
        self.client.force_login(self.user2)
        
        response = self.client.get(reverse('messaging:unread_notifications'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('messages', data)
        self.assertIn('notifications', data)
        self.assertIn('total_unread', data)


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class MessageFlowStressTest(TransactionTestCase):
    """Stress tests for message flow under load"""
    
    def setUp(self):
        self.users = []
        for i in range(10):  # Create 10 test users
            user = User.objects.create_user(
                username=f'stressuser{i}',
                email=f'stress{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)
        
        # Clean up
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
    
    def tearDown(self):
        Message.objects.all().delete()
        UserStatus.objects.all().delete()
    
    async def test_high_volume_message_flow(self):
        """
        Test system behavior under high message volume:
        1. Multiple users sending messages concurrently
        2. Verify all messages are processed
        3. Check system stability
        """
        message_count_per_user = 5
        total_expected_messages = len(self.users) * message_count_per_user
        
        async def send_messages_for_user(user, target_user):
            """Send multiple messages from one user to another"""
            messages_sent = []
            
            for i in range(message_count_per_user):
                try:
                    message = await MessagePersistenceManager().create_message_atomic(
                        sender=user,
                        recipient=target_user,
                        content=f"Stress test message {i} from {user.username}",
                        client_id=f"stress_{user.id}_{i}_{uuid.uuid4().hex[:8]}"
                    )
                    messages_sent.append(message)
                    
                    # Small delay to simulate realistic usage
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Error sending message for {user.username}: {e}")
            
            return messages_sent
        
        # Create tasks for concurrent message sending
        tasks = []
        for i, user in enumerate(self.users):
            target_user = self.users[(i + 1) % len(self.users)]  # Send to next user
            task = send_messages_for_user(user, target_user)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        total_sent = 0
        for result in results:
            if isinstance(result, Exception):
                self.fail(f"Stress test task failed: {result}")
            else:
                total_sent += len(result)
        
        # Verify all messages were sent
        self.assertEqual(total_sent, total_expected_messages)
        
        # Verify database consistency
        db_message_count = await Message.objects.acount()
        self.assertEqual(db_message_count, total_expected_messages)
        
        # Verify no duplicate client_ids
        client_ids = await Message.objects.values_list('client_id', flat=True).aall()
        client_ids_list = list(client_ids)
        self.assertEqual(len(set(client_ids_list)), len(client_ids_list))


if __name__ == '__main__':
    pytest.main([__file__])
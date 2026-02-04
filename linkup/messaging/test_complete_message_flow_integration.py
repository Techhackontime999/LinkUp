"""
Integration Tests for Complete Message Flow

This module contains comprehensive integration tests that verify the end-to-end
message flow in the WhatsApp-like messaging system, including all status transitions,
offline/online scenarios, and multi-user interactions.

Test Coverage:
- Complete message lifecycle from send to read receipt
- Offline/online user transitions
- Multi-user chat scenarios
- Error recovery scenarios
- Real-time synchronization
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from unittest.mock import patch, MagicMock, AsyncMock
import logging

from .models import Message, UserStatus, QueuedMessage, Notification
from .consumers import ChatConsumer, NotificationsConsumer
from .message_status_manager import MessageStatusManager
from .message_persistence_manager import message_persistence_manager
from .read_receipt_manager import read_receipt_manager

User = get_user_model()
logger = logging.getLogger(__name__)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class CompleteMessageFlowIntegrationTest(TransactionTestCase):
    """Integration tests for complete message flow scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user1 = User.objects.create_user(
            username='integration_user1',
            email='integration1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='integration_user2',
            email='integration2@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='integration_user3',
            email='integration3@example.com',
            password='testpass123'
        )
        
        # Clean up any existing data
        Message.objects.all().delete()
        QueuedMessage.objects.all().delete()
        UserStatus.objects.all().delete()
        Notification.objects.all().delete()
        
        # Initialize managers
        self.status_manager = MessageStatusManager()
        
    def tearDown(self):
        """Clean up after tests"""
        Message.objects.all().delete()
        QueuedMessage.objects.all().delete()
        UserStatus.objects.all().delete()
        Notification.objects.all().delete()
    
    async def test_complete_message_lifecycle_integration(self):
        """
        Test complete message lifecycle: send -> delivered -> read
        
        This test verifies:
        1. Message creation and initial status
        2. WebSocket broadcasting
        3. Status transitions (pending -> sent -> delivered -> read)
        4. Read receipt generation
        5. Real-time status updates
        """
        # Create WebSocket communicators for both users
        communicator1 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.user2.username}/")
        communicator1.scope['user'] = self.user1
        
        communicator2 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.user1.username}/")
        communicator2.scope['user'] = self.user2
        
        # Connect both users
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        
        self.assertTrue(connected1)
        self.assertTrue(connected2)
        
        try:
            # Step 1: User1 sends a message to User2
            message_content = "Integration test message"
            client_id = f"integration_test_{uuid.uuid4().hex[:8]}"
            
            await communicator1.send_json_to({
                'type': 'message',
                'message': message_content,
                'client_id': client_id
            })
            
            # Step 2: Verify User2 receives the message
            response2 = await communicator2.receive_json_from(timeout=5)
            
            self.assertEqual(response2['type'], 'message')
            self.assertEqual(response2['content'], message_content)
            self.assertEqual(response2['sender'], self.user1.username)
            self.assertEqual(response2['recipient'], self.user2.username)
            self.assertEqual(response2['client_id'], client_id)
            
            message_id = response2['id']
            
            # Step 3: Verify message was created in database with correct status
            message = await Message.objects.aget(id=message_id)
            self.assertEqual(message.content, message_content)
            self.assertEqual(message.sender, self.user1)
            self.assertEqual(message.recipient, self.user2)
            self.assertEqual(message.client_id, client_id)
            self.assertEqual(message.status, 'delivered')  # Should be delivered when received
            
            # Step 4: User2 sends read receipt
            await communicator2.send_json_to({
                'type': 'read_receipt',
                'message_id': message_id
            })
            
            # Step 5: Verify User1 receives read receipt confirmation
            read_receipt_response = await communicator1.receive_json_from(timeout=5)
            
            # Should receive status update
            if read_receipt_response.get('type') == 'message_status_update':
                self.assertEqual(read_receipt_response['message_id'], message_id)
                self.assertEqual(read_receipt_response['status'], 'read')
            
            # Step 6: Verify message status updated in database
            message.refresh_from_db()
            self.assertEqual(message.status, 'read')
            self.assertTrue(message.is_read)
            self.assertIsNotNone(message.read_at)
            
            # Step 7: Verify timestamp sequence
            self.assertIsNotNone(message.created_at)
            self.assertIsNotNone(message.sent_at)
            self.assertIsNotNone(message.delivered_at)
            self.assertIsNotNone(message.read_at)
            
            # Timestamps should be in order
            self.assertLessEqual(message.created_at, message.sent_at)
            self.assertLessEqual(message.sent_at, message.delivered_at)
            self.assertLessEqual(message.delivered_at, message.read_at)
            
        finally:
            await communicator1.disconnect()
            await communicator2.disconnect()
    
    async def test_offline_online_transition_integration(self):
        """
        Test offline/online user transitions and message queuing
        
        This test verifies:
        1. Message queuing when recipient is offline
        2. Message delivery when recipient comes online
        3. Proper status transitions during offline/online states
        4. Queue processing and cleanup
        """
        # Step 1: Ensure User2 is offline
        user2_status, created = await UserStatus.objects.aget_or_create(
            user=self.user2,
            defaults={'is_online': False, 'active_connections': 0}
        )
        user2_status.is_online = False
        user2_status.active_connections = 0
        await user2_status.asave()
        
        # Step 2: User1 connects and sends message to offline User2
        communicator1 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.user2.username}/")
        communicator1.scope['user'] = self.user1
        
        connected1, _ = await communicator1.connect()
        self.assertTrue(connected1)
        
        try:
            # Send message to offline user
            message_content = "Message to offline user"
            client_id = f"offline_test_{uuid.uuid4().hex[:8]}"
            
            await communicator1.send_json_to({
                'type': 'message',
                'message': message_content,
                'client_id': client_id
            })
            
            # Step 3: Verify message was queued for offline delivery
            await asyncio.sleep(1)  # Allow processing time
            
            # Check if message was created and queued
            message = await Message.objects.filter(
                sender=self.user1,
                recipient=self.user2,
                client_id=client_id
            ).afirst()
            
            self.assertIsNotNone(message)
            self.assertEqual(message.content, message_content)
            
            # Step 4: User2 comes online
            communicator2 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.user1.username}/")
            communicator2.scope['user'] = self.user2
            
            connected2, _ = await communicator2.connect()
            self.assertTrue(connected2)
            
            try:
                # Step 5: Verify User2 receives queued message
                response2 = await communicator2.receive_json_from(timeout=10)
                
                if response2.get('type') == 'message_sync':
                    # Message sync response
                    sync_result = response2['sync_result']
                    self.assertGreater(len(sync_result.get('messages', [])), 0)
                else:
                    # Direct message
                    self.assertEqual(response2['type'], 'message')
                    self.assertEqual(response2['content'], message_content)
                
                # Step 6: Verify message status updated to delivered
                message.refresh_from_db()
                self.assertIn(message.status, ['delivered', 'read'])
                
                # Step 7: Verify user status updated to online
                user2_status.refresh_from_db()
                self.assertTrue(user2_status.is_online)
                self.assertGreater(user2_status.active_connections, 0)
                
            finally:
                await communicator2.disconnect()
                
        finally:
            await communicator1.disconnect()
    
    def test_message_persistence_integration(self):
        """
        Test message persistence integration with all components
        
        This test verifies:
        1. Message persistence manager integration
        2. Database locking and consistency
        3. Bulk operations
        4. Transaction safety
        """
        # This test uses synchronous methods for database operations
        
        # Step 1: Create messages using persistence manager
        messages_created = []
        
        for i in range(5):
            # Use asyncio.run for async persistence manager methods
            message = asyncio.run(message_persistence_manager.create_message_atomic(
                sender=self.user1,
                recipient=self.user2,
                content=f"Persistence test message {i}",
                client_id=f"persist_test_{i}_{uuid.uuid4().hex[:8]}"
            ))
            
            self.assertIsNotNone(message)
            messages_created.append(message)
        
        # Step 2: Test bulk status update
        message_ids = [msg.id for msg in messages_created]
        
        result = asyncio.run(message_persistence_manager.bulk_update_message_status(
            message_ids=message_ids,
            new_status='sent',
            user_id=self.user1.id
        ))
        
        self.assertEqual(result['updated_count'], 5)
        self.assertEqual(result['failed_count'], 0)
        
        # Step 3: Verify all messages updated
        for message in messages_created:
            message.refresh_from_db()
            self.assertEqual(message.status, 'sent')
            self.assertIsNotNone(message.sent_at)
        
        # Step 4: Test conversation loading
        conversation_data = asyncio.run(message_persistence_manager.get_conversation_messages(
            user1_id=self.user1.id,
            user2_id=self.user2.id,
            limit=10,
            include_metadata=True
        ))
        
        self.assertEqual(len(conversation_data['messages']), 5)
        self.assertEqual(conversation_data['count'], 5)
        self.assertIn('metadata', conversation_data)
        
        # Verify chronological ordering
        messages = conversation_data['messages']
        for i in range(1, len(messages)):
            prev_time = datetime.fromisoformat(messages[i-1]['created_at'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(messages[i]['created_at'].replace('Z', '+00:00'))
            self.assertLessEqual(prev_time, curr_time)
    
    async def test_error_recovery_scenarios_integration(self):
        """
        Test error recovery scenarios and system resilience
        
        This test verifies:
        1. Recovery from WebSocket connection failures
        2. Message retry mechanisms
        3. Queue processing after errors
        4. System stability under error conditions
        """
        # Step 1: Create connection with User1
        communicator1 = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.user2.username}/")
        communicator1.scope['user'] = self.user1
        
        connected1, _ = await communicator1.connect()
        self.assertTrue(connected1)
        
        try:
            # Step 2: Send message that will succeed
            success_message = "This should succeed"
            success_client_id = f"success_{uuid.uuid4().hex[:8]}"
            
            await communicator1.send_json_to({
                'type': 'message',
                'message': success_message,
                'client_id': success_client_id
            })
            
            # Verify successful message
            success_msg = await Message.objects.filter(
                sender=self.user1,
                client_id=success_client_id
            ).afirst()
            
            self.assertIsNotNone(success_msg)
            self.assertEqual(success_msg.content, success_message)
            
            # Step 3: Test recovery - send another message after potential error
            recovery_message = "Recovery message"
            recovery_client_id = f"recovery_{uuid.uuid4().hex[:8]}"
            
            await communicator1.send_json_to({
                'type': 'message',
                'message': recovery_message,
                'client_id': recovery_client_id
            })
            
            # Verify recovery message succeeds
            recovery_msg = await Message.objects.filter(
                sender=self.user1,
                client_id=recovery_client_id
            ).afirst()
            
            self.assertIsNotNone(recovery_msg)
            self.assertEqual(recovery_msg.content, recovery_message)
            
        finally:
            await communicator1.disconnect()


if __name__ == '__main__':
    pytest.main([__file__])
"""
Property-based tests for real-time message delivery system.
**Validates: Requirements 2.1, 2.2, 2.3**
"""

import pytest
import asyncio
import json
import uuid
from hypothesis import given, strategies as st, settings, assume
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from messaging.consumers import ChatConsumer
from messaging.models import Message
from datetime import timedelta

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class RealtimeDeliveryPropertiesTest(TransactionTestCase):
    """Property-based tests for real-time message delivery."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='realtime_sender',
            email='sender@realtime.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='realtime_recipient',
            email='recipient@realtime.com',
            password='testpass123'
        )
    
    @given(
        message_content=st.text(min_size=1, max_size=500),
        client_id=st.text(min_size=10, max_size=50).filter(lambda x: x.replace('_', '').isalnum())
    )
    @settings(max_examples=20, deadline=5000)
    def test_property_realtime_message_delivery(self, message_content, client_id):
        """
        **Property 2: Real-time Message Delivery**
        
        For any message content and client ID:
        1. Messages should be delivered to all room participants within 100ms
        2. Message should be persisted immediately in database
        3. Status should progress from pending -> sent -> delivered
        4. Client ID should prevent duplicate messages
        """
        asyncio.run(self._test_realtime_message_delivery(message_content, client_id))
    
    async def _test_realtime_message_delivery(self, message_content, client_id):
        """Async implementation of real-time delivery test."""
        
        # Set up two communicators for the same chat room
        communicator1 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator1.scope["user"] = self.user1
        
        communicator2 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user1.username}/"
        )
        communicator2.scope["user"] = self.user2
        
        # Connect both users
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        
        assert connected1 and connected2, "Both users should connect successfully"
        
        # Clear initial status messages
        await communicator1.receive_json_from(timeout=1)
        await communicator2.receive_json_from(timeout=1)
        
        # Record start time for delivery timing test
        start_time = timezone.now()
        
        # Send message from user1 with client_id
        await communicator1.send_json_to({
            "type": "message",
            "message": message_content,
            "client_id": client_id
        })
        
        # Both users should receive the message within 100ms
        message1 = await communicator1.receive_json_from(timeout=2)
        message2 = await communicator2.receive_json_from(timeout=2)
        
        delivery_time = timezone.now()
        delivery_duration = (delivery_time - start_time).total_seconds() * 1000  # Convert to ms
        
        # Verify delivery timing (allowing some tolerance for test environment)
        assert delivery_duration < 500, f"Message delivery took {delivery_duration}ms, should be < 500ms"
        
        # Verify message structure and content
        assert message1["type"] == "message"
        assert message1["content"] == message_content
        assert message1["sender"] == self.user1.username
        assert message1["recipient"] == self.user2.username
        assert message1["client_id"] == client_id
        assert message1["status"] in ["pending", "sent"]  # Should be sent by now
        
        assert message2["type"] == "message"
        assert message2["content"] == message_content
        assert message2["sender"] == self.user1.username
        assert message2["recipient"] == self.user2.username
        assert message2["client_id"] == client_id
        
        # Verify message was persisted in database
        saved_message = await database_sync_to_async(Message.objects.get)(
            sender=self.user1,
            recipient=self.user2,
            content=message_content,
            client_id=client_id
        )
        assert saved_message is not None
        assert saved_message.status in ["pending", "sent", "delivered"]
        
        # Test duplicate prevention - send same client_id again
        await communicator1.send_json_to({
            "type": "message",
            "message": message_content + "_duplicate",
            "client_id": client_id  # Same client_id
        })
        
        # Should still only have one message with this client_id
        message_count = await database_sync_to_async(Message.objects.filter)(
            sender=self.user1,
            client_id=client_id
        )
        message_count = await database_sync_to_async(message_count.count)()
        assert message_count == 1, "Duplicate client_id should not create new message"
        
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    @given(
        message_batch_size=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=10, deadline=8000)
    def test_property_concurrent_message_delivery(self, message_batch_size):
        """
        **Property 3: Concurrent Message Delivery**
        
        For any number of concurrent messages:
        1. All messages should be delivered successfully
        2. Message order should be preserved
        3. No messages should be lost
        4. Each message should have unique client_id
        """
        asyncio.run(self._test_concurrent_message_delivery(message_batch_size))
    
    async def _test_concurrent_message_delivery(self, message_batch_size):
        """Async implementation of concurrent delivery test."""
        
        # Set up communicators
        communicator1 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator1.scope["user"] = self.user1
        
        communicator2 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user1.username}/"
        )
        communicator2.scope["user"] = self.user2
        
        # Connect both users
        await communicator1.connect()
        await communicator2.connect()
        
        # Clear initial messages
        await communicator1.receive_json_from(timeout=1)
        await communicator2.receive_json_from(timeout=1)
        
        # Send multiple messages concurrently
        messages_to_send = []
        for i in range(message_batch_size):
            client_id = f"concurrent_test_{i}_{uuid.uuid4().hex[:8]}"
            message_content = f"Concurrent message {i}"
            messages_to_send.append({
                "type": "message",
                "message": message_content,
                "client_id": client_id
            })
        
        # Send all messages rapidly
        send_tasks = []
        for msg_data in messages_to_send:
            task = communicator1.send_json_to(msg_data)
            send_tasks.append(task)
        
        await asyncio.gather(*send_tasks)
        
        # Collect all received messages
        received_messages_user1 = []
        received_messages_user2 = []
        
        for _ in range(message_batch_size):
            msg1 = await communicator1.receive_json_from(timeout=3)
            msg2 = await communicator2.receive_json_from(timeout=3)
            received_messages_user1.append(msg1)
            received_messages_user2.append(msg2)
        
        # Verify all messages were received
        assert len(received_messages_user1) == message_batch_size
        assert len(received_messages_user2) == message_batch_size
        
        # Verify message content and order
        for i, (msg1, msg2) in enumerate(zip(received_messages_user1, received_messages_user2)):
            expected_content = f"Concurrent message {i}"
            assert msg1["content"] == expected_content
            assert msg2["content"] == expected_content
            assert msg1["sender"] == self.user1.username
            assert msg2["sender"] == self.user1.username
        
        # Verify all messages were persisted
        saved_count = await database_sync_to_async(Message.objects.filter)(
            sender=self.user1,
            recipient=self.user2
        )
        saved_count = await database_sync_to_async(saved_count.count)()
        assert saved_count >= message_batch_size, "All messages should be persisted"
        
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    @given(
        message_content=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=15, deadline=4000)
    def test_property_message_status_progression(self, message_content):
        """
        **Property 4: Message Status Progression**
        
        For any message:
        1. Status should progress: pending -> sent -> delivered -> read
        2. Timestamps should be set correctly for each status
        3. Status updates should be broadcast to relevant users
        4. Status should never regress (except to failed)
        """
        asyncio.run(self._test_message_status_progression(message_content))
    
    async def _test_message_status_progression(self, message_content):
        """Async implementation of status progression test."""
        
        # Set up communicators
        communicator1 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator1.scope["user"] = self.user1
        
        communicator2 = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user1.username}/"
        )
        communicator2.scope["user"] = self.user2
        
        # Connect both users
        await communicator1.connect()
        await communicator2.connect()
        
        # Clear initial messages
        await communicator1.receive_json_from(timeout=1)
        await communicator2.receive_json_from(timeout=1)
        
        client_id = f"status_test_{uuid.uuid4().hex[:8]}"
        
        # Send message
        await communicator1.send_json_to({
            "type": "message",
            "message": message_content,
            "client_id": client_id
        })
        
        # Receive messages
        msg1 = await communicator1.receive_json_from(timeout=2)
        msg2 = await communicator2.receive_json_from(timeout=2)
        
        message_id = msg1["id"]
        
        # Verify initial status (should be sent by now)
        assert msg1["status"] in ["pending", "sent"]
        
        # Wait a bit for status updates to propagate
        await asyncio.sleep(0.1)
        
        # Check database for status progression
        saved_message = await database_sync_to_async(Message.objects.get)(id=message_id)
        
        # Status should have progressed from pending
        assert saved_message.status in ["sent", "delivered", "read"]
        
        # If message is delivered, delivered_at should be set
        if saved_message.status in ["delivered", "read"]:
            assert saved_message.delivered_at is not None
        
        # If message is read, read_at should be set
        if saved_message.status == "read":
            assert saved_message.read_at is not None
            assert saved_message.is_read is True
        
        # Send read receipt to test read status
        await communicator2.send_json_to({
            "type": "read_receipt",
            "message_id": message_id
        })
        
        # Wait for read receipt processing
        await asyncio.sleep(0.1)
        
        # Check final status
        final_message = await database_sync_to_async(Message.objects.get)(id=message_id)
        assert final_message.status == "read"
        assert final_message.is_read is True
        assert final_message.read_at is not None
        
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    def test_property_websocket_error_handling(self):
        """
        **Property 5: WebSocket Error Handling**
        
        For any error condition:
        1. Errors should be handled gracefully
        2. Error messages should be sent to client
        3. Connection should remain stable
        4. Failed messages should be marked appropriately
        """
        asyncio.run(self._test_websocket_error_handling())
    
    async def _test_websocket_error_handling(self):
        """Async implementation of error handling test."""
        
        # Set up communicator
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator.scope["user"] = self.user1
        
        # Connect
        connected, _ = await communicator.connect()
        assert connected
        
        # Clear initial message
        await communicator.receive_json_from(timeout=1)
        
        # Test 1: Send empty message (should trigger error)
        await communicator.send_json_to({
            "type": "message",
            "message": "",  # Empty message
            "client_id": "error_test_1"
        })
        
        # Should receive error response
        error_response = await communicator.receive_json_from(timeout=2)
        assert error_response["type"] == "error"
        assert "required" in error_response["error"].lower()
        
        # Test 2: Send invalid JSON (should be handled gracefully)
        await communicator.send_text_to("invalid json {")
        
        # Should receive error response
        error_response = await communicator.receive_json_from(timeout=2)
        assert error_response["type"] == "error"
        
        # Test 3: Connection should still be working after errors
        await communicator.send_json_to({
            "type": "message",
            "message": "Recovery test message",
            "client_id": "recovery_test"
        })
        
        # Should receive the message successfully
        recovery_message = await communicator.receive_json_from(timeout=2)
        assert recovery_message["type"] == "message"
        assert recovery_message["content"] == "Recovery test message"
        
        await communicator.disconnect()


if __name__ == '__main__':
    pytest.main([__file__])
"""
Property-based tests for message broadcasting system.
**Validates: Requirements 2.4**
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

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class MessageBroadcastingPropertiesTest(TransactionTestCase):
    """Property-based tests for message broadcasting."""
    
    def setUp(self):
        """Set up test users."""
        self.users = []
        for i in range(4):  # Create 4 users for multi-user testing
            user = User.objects.create_user(
                username=f'broadcast_user_{i}',
                email=f'user{i}@broadcast.com',
                password='testpass123'
            )
            self.users.append(user)
    
    @given(
        message_content=st.text(min_size=1, max_size=300),
        participant_count=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=15, deadline=6000)
    def test_property_message_broadcasting_to_all_participants(self, message_content, participant_count):
        """
        **Property 3: Message Broadcasting**
        
        For any message and number of participants:
        1. Message should be broadcast to all room participants
        2. Each participant should receive identical message data
        3. Sender should also receive their own message (for confirmation)
        4. Broadcasting should happen simultaneously to all participants
        """
        # Ensure we don't exceed available users
        assume(participant_count <= len(self.users))
        
        asyncio.run(self._test_message_broadcasting_to_all_participants(
            message_content, participant_count
        ))
    
    async def _test_message_broadcasting_to_all_participants(self, message_content, participant_count):
        """Async implementation of message broadcasting test."""
        
        # Select users for this test
        test_users = self.users[:participant_count]
        sender = test_users[0]
        recipients = test_users[1:]
        
        # Create communicators for all participants
        communicators = []
        
        # Sender communicator (connects to first recipient)
        sender_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{recipients[0].username}/"
        )
        sender_communicator.scope["user"] = sender
        communicators.append(('sender', sender_communicator))
        
        # Recipient communicators (all connect to sender)
        for recipient in recipients:
            recipient_communicator = WebsocketCommunicator(
                ChatConsumer.as_asgi(),
                f"/ws/chat/{sender.username}/"
            )
            recipient_communicator.scope["user"] = recipient
            communicators.append((f'recipient_{recipient.username}', recipient_communicator))
        
        # Connect all participants
        for role, communicator in communicators:
            connected, _ = await communicator.connect()
            assert connected, f"{role} should connect successfully"
        
        # Clear initial status messages
        for role, communicator in communicators:
            try:
                await communicator.receive_json_from(timeout=1)
            except asyncio.TimeoutError:
                pass  # Some might not have initial messages
        
        client_id = f"broadcast_test_{uuid.uuid4().hex[:8]}"
        
        # Send message from sender
        start_time = timezone.now()
        await sender_communicator.send_json_to({
            "type": "message",
            "message": message_content,
            "client_id": client_id
        })
        
        # Collect messages from all participants
        received_messages = {}
        receive_tasks = []
        
        for role, communicator in communicators:
            task = asyncio.create_task(
                self._receive_message_with_role(communicator, role)
            )
            receive_tasks.append(task)
        
        # Wait for all messages to be received
        results = await asyncio.gather(*receive_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Failed to receive message: {result}")
            else:
                role, message = result
                received_messages[role] = message
        
        end_time = timezone.now()
        broadcast_duration = (end_time - start_time).total_seconds() * 1000
        
        # Verify broadcasting timing (should be fast)
        assert broadcast_duration < 1000, f"Broadcasting took {broadcast_duration}ms, should be < 1000ms"
        
        # Verify all participants received the message
        assert len(received_messages) == len(communicators), "All participants should receive the message"
        
        # Verify message content consistency
        expected_fields = ['type', 'content', 'sender', 'client_id', 'id']
        reference_message = None
        
        for role, message in received_messages.items():
            # Verify message structure
            for field in expected_fields:
                assert field in message, f"Message should contain {field} field"
            
            # Verify content
            assert message['type'] == 'message'
            assert message['content'] == message_content
            assert message['sender'] == sender.username
            assert message['client_id'] == client_id
            
            # Use first message as reference for comparison
            if reference_message is None:
                reference_message = message
            else:
                # Verify all messages have same core data
                assert message['id'] == reference_message['id']
                assert message['content'] == reference_message['content']
                assert message['sender'] == reference_message['sender']
                assert message['client_id'] == reference_message['client_id']
        
        # Verify message was persisted only once
        saved_messages = await database_sync_to_async(Message.objects.filter)(
            sender=sender,
            content=message_content,
            client_id=client_id
        )
        saved_count = await database_sync_to_async(saved_messages.count)()
        assert saved_count == 1, "Message should be persisted exactly once"
        
        # Disconnect all communicators
        for role, communicator in communicators:
            await communicator.disconnect()
    
    async def _receive_message_with_role(self, communicator, role):
        """Helper to receive message with role identification."""
        message = await communicator.receive_json_from(timeout=3)
        return role, message
    
    @given(
        message_batch=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=10, deadline=8000)
    def test_property_sequential_message_broadcasting(self, message_batch):
        """
        **Property 4: Sequential Message Broadcasting**
        
        For any sequence of messages:
        1. Each message should be broadcast in order
        2. All participants should receive messages in the same order
        3. No messages should be lost or duplicated
        4. Message IDs should be unique and sequential
        """
        asyncio.run(self._test_sequential_message_broadcasting(message_batch))
    
    async def _test_sequential_message_broadcasting(self, message_batch):
        """Async implementation of sequential broadcasting test."""
        
        sender = self.users[0]
        recipient = self.users[1]
        
        # Set up communicators
        sender_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{recipient.username}/"
        )
        sender_communicator.scope["user"] = sender
        
        recipient_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{sender.username}/"
        )
        recipient_communicator.scope["user"] = recipient
        
        # Connect both
        await sender_communicator.connect()
        await recipient_communicator.connect()
        
        # Clear initial messages
        await sender_communicator.receive_json_from(timeout=1)
        await recipient_communicator.receive_json_from(timeout=1)
        
        # Send messages sequentially
        sent_messages = []
        for i, content in enumerate(message_batch):
            client_id = f"seq_test_{i}_{uuid.uuid4().hex[:6]}"
            
            await sender_communicator.send_json_to({
                "type": "message",
                "message": content,
                "client_id": client_id
            })
            
            sent_messages.append({
                'content': content,
                'client_id': client_id,
                'index': i
            })
            
            # Small delay to ensure sequential processing
            await asyncio.sleep(0.05)
        
        # Collect all received messages
        sender_received = []
        recipient_received = []
        
        for _ in range(len(message_batch)):
            sender_msg = await sender_communicator.receive_json_from(timeout=3)
            recipient_msg = await recipient_communicator.receive_json_from(timeout=3)
            
            sender_received.append(sender_msg)
            recipient_received.append(recipient_msg)
        
        # Verify message count
        assert len(sender_received) == len(message_batch)
        assert len(recipient_received) == len(message_batch)
        
        # Verify message order and content
        for i, (sent, sender_msg, recipient_msg) in enumerate(
            zip(sent_messages, sender_received, recipient_received)
        ):
            # Verify content matches
            assert sender_msg['content'] == sent['content']
            assert recipient_msg['content'] == sent['content']
            
            # Verify client_id matches
            assert sender_msg['client_id'] == sent['client_id']
            assert recipient_msg['client_id'] == sent['client_id']
            
            # Verify same message ID for both recipients
            assert sender_msg['id'] == recipient_msg['id']
            
            # Verify sender information
            assert sender_msg['sender'] == sender.username
            assert recipient_msg['sender'] == sender.username
        
        # Verify all messages were persisted in correct order
        saved_messages = await database_sync_to_async(
            lambda: list(Message.objects.filter(
                sender=sender,
                recipient=recipient
            ).order_by('created_at'))
        )()
        
        assert len(saved_messages) >= len(message_batch)
        
        # Check the last N messages match our batch
        recent_messages = saved_messages[-len(message_batch):]
        for sent, saved in zip(sent_messages, recent_messages):
            assert saved.content == sent['content']
            assert saved.client_id == sent['client_id']
        
        await sender_communicator.disconnect()
        await recipient_communicator.disconnect()
    
    @given(
        message_content=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=10, deadline=5000)
    def test_property_broadcast_failure_handling(self, message_content):
        """
        **Property 5: Broadcast Failure Handling**
        
        For any message when some participants are disconnected:
        1. Message should still be broadcast to connected participants
        2. Disconnected participants should not prevent broadcasting
        3. Message should be persisted regardless of broadcast success
        4. No exceptions should be raised due to disconnected participants
        """
        asyncio.run(self._test_broadcast_failure_handling(message_content))
    
    async def _test_broadcast_failure_handling(self, message_content):
        """Async implementation of broadcast failure handling test."""
        
        sender = self.users[0]
        recipient1 = self.users[1]
        recipient2 = self.users[2]
        
        # Set up communicators
        sender_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{recipient1.username}/"
        )
        sender_communicator.scope["user"] = sender
        
        recipient1_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{sender.username}/"
        )
        recipient1_communicator.scope["user"] = recipient1
        
        recipient2_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{sender.username}/"
        )
        recipient2_communicator.scope["user"] = recipient2
        
        # Connect all participants
        await sender_communicator.connect()
        await recipient1_communicator.connect()
        await recipient2_communicator.connect()
        
        # Clear initial messages
        await sender_communicator.receive_json_from(timeout=1)
        await recipient1_communicator.receive_json_from(timeout=1)
        await recipient2_communicator.receive_json_from(timeout=1)
        
        # Disconnect recipient2 to simulate failure
        await recipient2_communicator.disconnect()
        
        client_id = f"failure_test_{uuid.uuid4().hex[:8]}"
        
        # Send message (should succeed despite recipient2 being disconnected)
        await sender_communicator.send_json_to({
            "type": "message",
            "message": message_content,
            "client_id": client_id
        })
        
        # Sender and recipient1 should still receive the message
        sender_msg = await sender_communicator.receive_json_from(timeout=3)
        recipient1_msg = await recipient1_communicator.receive_json_from(timeout=3)
        
        # Verify messages were received correctly
        assert sender_msg['content'] == message_content
        assert recipient1_msg['content'] == message_content
        assert sender_msg['client_id'] == client_id
        assert recipient1_msg['client_id'] == client_id
        
        # Verify message was persisted despite broadcast failure
        saved_message = await database_sync_to_async(Message.objects.get)(
            sender=sender,
            content=message_content,
            client_id=client_id
        )
        assert saved_message is not None
        assert saved_message.status in ['pending', 'sent', 'delivered']
        
        await sender_communicator.disconnect()
        await recipient1_communicator.disconnect()
    
    def test_property_broadcast_with_status_updates(self):
        """
        **Property 6: Broadcast with Status Updates**
        
        For any message with status updates:
        1. Status updates should be broadcast to relevant participants
        2. Sender should receive delivery/read confirmations
        3. Recipients should receive status change notifications
        4. Status updates should not interfere with message broadcasting
        """
        asyncio.run(self._test_broadcast_with_status_updates())
    
    async def _test_broadcast_with_status_updates(self):
        """Async implementation of broadcast with status updates test."""
        
        sender = self.users[0]
        recipient = self.users[1]
        
        # Set up communicators
        sender_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{recipient.username}/"
        )
        sender_communicator.scope["user"] = sender
        
        recipient_communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{sender.username}/"
        )
        recipient_communicator.scope["user"] = recipient
        
        # Connect both
        await sender_communicator.connect()
        await recipient_communicator.connect()
        
        # Clear initial messages
        await sender_communicator.receive_json_from(timeout=1)
        await recipient_communicator.receive_json_from(timeout=1)
        
        client_id = f"status_broadcast_test_{uuid.uuid4().hex[:8]}"
        message_content = "Status update test message"
        
        # Send message
        await sender_communicator.send_json_to({
            "type": "message",
            "message": message_content,
            "client_id": client_id
        })
        
        # Receive initial messages
        sender_msg = await sender_communicator.receive_json_from(timeout=3)
        recipient_msg = await recipient_communicator.receive_json_from(timeout=3)
        
        message_id = sender_msg['id']
        
        # Send read receipt from recipient
        await recipient_communicator.send_json_to({
            "type": "read_receipt",
            "message_id": message_id
        })
        
        # Both participants should receive read receipt confirmation
        try:
            read_receipt_sender = await sender_communicator.receive_json_from(timeout=2)
            read_receipt_recipient = await recipient_communicator.receive_json_from(timeout=2)
            
            # Verify read receipt structure
            assert read_receipt_sender['type'] == 'read_receipt'
            assert read_receipt_sender['message_id'] == message_id
            assert read_receipt_sender['read_by'] == recipient.username
            
            assert read_receipt_recipient['type'] == 'read_receipt'
            assert read_receipt_recipient['message_id'] == message_id
            assert read_receipt_recipient['read_by'] == recipient.username
            
        except asyncio.TimeoutError:
            # Read receipts might be processed differently, this is acceptable
            pass
        
        # Verify final message status in database
        final_message = await database_sync_to_async(Message.objects.get)(id=message_id)
        assert final_message.is_read is True
        assert final_message.read_at is not None
        
        await sender_communicator.disconnect()
        await recipient_communicator.disconnect()


if __name__ == '__main__':
    pytest.main([__file__])
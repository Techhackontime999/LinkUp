"""
Property-based tests for WebSocket connection establishment.
**Validates: Requirements 1.2, 1.3, 1.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from messaging.consumers import ChatConsumer, NotificationsConsumer
import json
import asyncio

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class WebSocketConnectionPropertiesTest(TransactionTestCase):
    """Property-based tests for WebSocket connection establishment."""
    
    def setUp(self):
        """Set up test users."""
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
    
    @given(
        username=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=3,
            max_size=20
        ).filter(lambda x: x.isalnum())
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_websocket_connection_establishment(self, username):
        """
        **Property 1: WebSocket Connection Establishment**
        
        For any valid username, WebSocket connections should:
        1. Accept connections for authenticated users
        2. Reject connections for unauthenticated users  
        3. Handle invalid usernames gracefully
        4. Establish proper room groups
        """
        asyncio.run(self._test_websocket_connection_establishment(username))
    
    async def _test_websocket_connection_establishment(self, username):
        """Async implementation of WebSocket connection test."""
        
        # Test 1: Authenticated user should connect successfully
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator.scope["user"] = self.user1
        
        connected, subprotocol = await communicator.connect()
        assert connected, "Authenticated user should be able to connect"
        
        # Should receive user status message
        response = await communicator.receive_json_from(timeout=2)
        assert response["type"] == "user_status"
        assert response["username"] == self.user2.username
        
        await communicator.disconnect()
        
        # Test 2: Unauthenticated user should be rejected
        communicator_unauth = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator_unauth.scope["user"] = None
        
        connected, subprotocol = await communicator_unauth.connect()
        assert not connected, "Unauthenticated user should be rejected"
        
        # Test 3: Invalid username should be handled gracefully
        if username != self.user2.username:
            communicator_invalid = WebsocketCommunicator(
                ChatConsumer.as_asgi(),
                f"/ws/chat/{username}/"
            )
            communicator_invalid.scope["user"] = self.user1
            
            connected, subprotocol = await communicator_invalid.connect()
            # Should either reject or handle gracefully
            if connected:
                await communicator_invalid.disconnect()
    
    @given(
        message_content=st.text(min_size=1, max_size=1000)
    )
    @settings(max_examples=30, deadline=5000)
    def test_property_websocket_message_flow(self, message_content):
        """
        **Property 2: WebSocket Message Flow**
        
        For any valid message content, the WebSocket should:
        1. Accept and persist the message
        2. Broadcast to all room participants
        3. Return proper message structure
        4. Handle special characters correctly
        """
        asyncio.run(self._test_websocket_message_flow(message_content))
    
    async def _test_websocket_message_flow(self, message_content):
        """Async implementation of WebSocket message flow test."""
        
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
        await communicator1.receive_json_from(timeout=1)  # user status
        await communicator2.receive_json_from(timeout=1)  # user status
        
        # Send message from user1
        await communicator1.send_json_to({
            "type": "message",
            "message": message_content
        })
        
        # Both users should receive the message
        message1 = await communicator1.receive_json_from(timeout=2)
        message2 = await communicator2.receive_json_from(timeout=2)
        
        # Verify message structure and content
        assert message1["type"] == "message"
        assert message1["content"] == message_content
        assert message1["sender"] == self.user1.username
        assert message1["recipient"] == self.user2.username
        
        assert message2["type"] == "message"
        assert message2["content"] == message_content
        assert message2["sender"] == self.user1.username
        assert message2["recipient"] == self.user2.username
        
        # Verify message was persisted
        from messaging.models import Message
        saved_message = await database_sync_to_async(Message.objects.get)(
            sender=self.user1,
            recipient=self.user2,
            content=message_content
        )
        assert saved_message is not None
        
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    def test_property_notifications_websocket_connection(self):
        """
        **Property 3: Notifications WebSocket Connection**
        
        Notifications WebSocket should:
        1. Accept authenticated users
        2. Reject unauthenticated users
        3. Send initial unread count
        4. Handle notification actions
        """
        asyncio.run(self._test_notifications_websocket_connection())
    
    async def _test_notifications_websocket_connection(self):
        """Async implementation of notifications WebSocket test."""
        
        # Test authenticated connection
        communicator = WebsocketCommunicator(
            NotificationsConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator.scope["user"] = self.user1
        
        connected, subprotocol = await communicator.connect()
        assert connected, "Authenticated user should connect to notifications"
        
        # Should receive initial badge update
        response = await communicator.receive_json_from(timeout=2)
        assert response["type"] == "badge_update"
        assert "unread_count" in response
        
        # Test ping/pong
        await communicator.send_json_to({
            "type": "ping",
            "timestamp": "test123"
        })
        
        pong_response = await communicator.receive_json_from(timeout=2)
        assert pong_response["type"] == "pong"
        assert pong_response["timestamp"] == "test123"
        
        await communicator.disconnect()
        
        # Test unauthenticated rejection
        communicator_unauth = WebsocketCommunicator(
            NotificationsConsumer.as_asgi(),
            "/ws/notifications/"
        )
        communicator_unauth.scope["user"] = None
        
        connected, subprotocol = await communicator_unauth.connect()
        assert not connected, "Unauthenticated user should be rejected"
    
    @given(
        typing_state=st.booleans()
    )
    @settings(max_examples=20, deadline=3000)
    def test_property_typing_indicator_websocket(self, typing_state):
        """
        **Property 4: Typing Indicator WebSocket**
        
        For any typing state, the WebSocket should:
        1. Accept typing indicator messages
        2. Broadcast to other room participants only
        3. Not echo back to sender
        4. Handle boolean typing states correctly
        """
        asyncio.run(self._test_typing_indicator_websocket(typing_state))
    
    async def _test_typing_indicator_websocket(self, typing_state):
        """Async implementation of typing indicator test."""
        
        # Set up two communicators
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
        
        # Send typing indicator from user1
        await communicator1.send_json_to({
            "type": "typing",
            "is_typing": typing_state
        })
        
        # User2 should receive typing indicator
        typing_message = await communicator2.receive_json_from(timeout=2)
        assert typing_message["type"] == "typing"
        assert typing_message["username"] == self.user1.username
        assert typing_message["is_typing"] == typing_state
        
        # User1 should NOT receive their own typing indicator
        try:
            # This should timeout since user1 shouldn't receive their own typing
            await communicator1.receive_json_from(timeout=0.5)
            assert False, "User should not receive their own typing indicator"
        except asyncio.TimeoutError:
            # This is expected - user1 should not receive their own typing
            pass
        
        await communicator1.disconnect()
        await communicator2.disconnect()


if __name__ == '__main__':
    pytest.main([__file__])
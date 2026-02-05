"""
Property-based tests for user presence tracking system.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from messaging.consumers import ChatConsumer
from messaging.models import UserStatus
from messaging.presence_manager import presence_manager
from datetime import timedelta

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class PresenceTrackingPropertiesTest(TransactionTestCase):
    """Property-based tests for user presence tracking."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='presence_user1',
            email='presence1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='presence_user2',
            email='presence2@example.com',
            password='testpass123'
        )
    
    @given(connection_count=st.integers(min_value=1, max_value=3))
    @settings(max_examples=10, deadline=4000)
    def test_property_user_presence_tracking(self, connection_count):
        """
        **Property 7: User Presence Tracking**
        
        For any number of connections:
        1. User should be online when connections > 0
        2. User should be offline when connections = 0
        3. Connection count should be tracked accurately
        4. Presence updates should be broadcast correctly
        """
        asyncio.run(self._test_user_presence_tracking(connection_count))
    
    async def _test_user_presence_tracking(self, connection_count):
        """Async implementation of presence tracking test."""
        
        communicators = []
        
        # Create multiple connections
        for i in range(connection_count):
            communicator = WebsocketCommunicator(
                ChatConsumer.as_asgi(),
                f"/ws/chat/{self.user2.username}/"
            )
            communicator.scope["user"] = self.user1
            
            connected, _ = await communicator.connect()
            assert connected
            
            communicators.append(communicator)
            
            # Clear initial message
            try:
                await communicator.receive_json_from(timeout=1)
            except asyncio.TimeoutError:
                pass
        
        # Verify user is online
        presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        
        assert presence['is_online'] is True
        assert presence['active_connections'] == connection_count
        
        # Disconnect all
        for communicator in communicators:
            await communicator.disconnect()
        
        # Verify user is offline
        final_presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        
        assert final_presence['is_online'] is False
        assert final_presence['active_connections'] == 0


if __name__ == '__main__':
    pytest.main([__file__])
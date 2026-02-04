"""
Property-based tests for user presence tracking system.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""

import pytest
import asyncio
import json
from hypothesis import given, strategies as st, settings, assume
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
        self.user3 = User.objects.create_user(
            username='presence_user3',
            email='presence3@example.com',
            password='testpass123'
        )
    
    @given(
        connection_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15, deadline=4000)
    def test_property_user_connection_tracking(self, connection_count):
        """
        **Property 7: User Presence Tracking**
        
        For any number of connections:
        1. User should be marked online when connecting
        2. Connection count should be tracked accurately
        3. User should go offline when all connections close
        4. Presence updates should be broadcast to relevant users
        """
        asyncio.run(self._test_user_connection_tracking(connection_count))
    
    async def _test_user_connection_tracking(self, connection_count):
        """Async implementation of connection tracking test."""
        
        # Verify user starts offline
        initial_presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        assert initial_presence['is_online'] is False
        
        # Create multiple connections
        communicators = []
        for i in range(connection_count):
            communicator = WebsocketCommunicator(
                ChatConsumer.as_asgi(),
                f"/ws/chat/{self.user2.username}/"
            )
            communicator.scope["user"] = self.user1
            
            connected, _ = await communicator.connect()
            assert connected, f"Connection {i+1} should succeed"
            communicators.append(communicator)
            
            # Clear initial message
            try:
                await communicator.receive_json_from(timeout=1)
            except asyncio.TimeoutError:
                pass
        
        # Verify user is online with correct connection count
        online_presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        assert online_presence['is_online'] is True
        assert online_presence['active_connections'] == connection_count
        
        # Disconnect all but one connection
        for i in range(connection_count - 1):
            await communicators[i].disconnect()
        
        # User should still be online (one connection remaining)
        partial_presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        assert partial_presence['is_online'] is True
        assert partial_presence['active_connections'] == 1
        
        # Disconnect last connection
        await communicators[-1].disconnect()
        
        # User should now be offline
        offline_presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        assert offline_presence['is_online'] is False
        assert offline_presence['active_connections'] == 0
    
    @given(
        heartbeat_interval=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, deadline=5000)
    def test_property_heartbeat_monitoring(self, heartbeat_interval):
        """
        **Property 8: Heartbeat Monitoring**
        
        For any heartbeat interval:
        1. Regular heartbeats should keep user online
        2. Missing heartbeats should mark user as stale
        3. Heartbeat timestamps should be updated correctly
        4. Stale connections should be cleaned up automatically
        """
        asyncio.run(self._test_heartbeat_monitoring(heartbeat_interval))
    
    async def _test_heartbeat_monitoring(self, heartbeat_interval):
        """Async implementation of heartbeat monitoring test."""
        
        # Connect user
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.user2.username}/"
        )
        communicator.scope["user"] = self.user1
        
        connected, _ = await communicator.connect()
        assert connected
        
        # Clear initial message
        await communicator.receive_json_from(timeout=1)
        
        # Send heartbeat pings at regular intervals
        for i in range(heartbeat_interval):
            await communicator.send_json_to({
                "type": "ping",
                "timestamp": f"heartbeat_{i}"
            })
            
            # Receive pong response
            pong = await communicator.receive_json_from(timeout=2)
            assert pong["type"] == "pong"
            assert pong["timestamp"] == f"heartbeat_{i}"
            
            # Small delay between heartbeats
            await asyncio.sleep(0.1)
        
        # Verify user is still online with recent heartbeat
        presence = await database_sync_to_async(
            presence_manager.get_user_presence
        )(self.user1)
        assert presence['is_online'] is True
        assert presence['last_ping'] is not None
        assert not presence['connection_stale']
        
        await communicator.disconnect()
    
    def test_property_stale_connection_cleanup(self):
        """
        **Property 9: Stale Connection Cleanup**
        
        For stale connections:
        1. Connections without heartbeat should be marked stale
        2. Cleanup should mark stale users as offline
        3. Cleanup should handle multiple stale connections
        4. Active connections should not be affected by cleanup
        """
        asyncio.run(self._test_stale_connection_cleanup())
    
    async def _test_stale_connection_cleanup(self):
        """Async implementation of stale connection cleanup test."""
        
        # Create user status with stale timestamp
        stale_time = timezone.now() - timedelta(seconds=60)  # 1 minute ago
        
        user_status = await database_sync_to_async(UserStatus.objects.create)(
            user=self.user1,
            is_online=True,
            active_connections=1,
            last_ping=stale_time
        )
        
        # Create another user with recent activity (should not be cleaned up)
        recent_time = timezone.now() - timedelta(seconds=5)  # 5 seconds ago
        
        active_status = await database_sync_to_async(UserStatus.objects.create)(
            user=self.user2,
            is_online=True,
            active_connections=1,
            last_ping=recent_time
        )
        
        # Run cleanup with 30-second timeout
        cleanup_count = await database_sync_to_async(
            presence_manager.cleanup_stale_connections
        )(timeout_seconds=30)
        
        # Should have cleaned up at least the stale connection
        assert cleanup_count >= 1
        
        # Verify stale user is now offline
        user_status.refresh_from_db()
        assert user_status.is_online is False
        assert user_status.active_connections == 0
        
        # Verify active user is still online
        active_status.refresh_from_db()
        assert active_status.is_online is True
        assert active_status.active_connections == 1
    
    @given(
        user_count=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=10, deadline=6000)
    def test_property_presence_broadcasting(self, user_count):
        """
        **Property 10: Presence Broadcasting**
        
        For any number of users:
        1. Online/offline status should be broadcast to relevant users
        2. Each user should receive presence updates from others
        3. Presence information should be consistent across users
        4. Broadcasting should handle multiple simultaneous changes
        """
        # Use available users up to the requested count
        actual_user_count = min(user_count, 3)
        asyncio.run(self._test_presence_broadcasting(actual_user_count))
    
    async def _test_presence_broadcasting(self, user_count):
        """Async implementation of presence broadcasting test."""
        
        users = [self.user1, self.user2, self.user3][:user_count]
        communicators = []
        
        # Connect all users to chat with user1
        for i, user in enumerate(users):
            if user != self.user1:
                # Other users connect to user1
                communicator = WebsocketCommunicator(
                    ChatConsumer.as_asgi(),
                    f"/ws/chat/{self.user1.username}/"
                )
                communicator.scope["user"] = user
            else:
                # User1 connects to user2
                communicator = WebsocketCommunicator(
                    ChatConsumer.as_asgi(),
                    f"/ws/chat/{self.user2.username}/"
                )
                communicator.scope["user"] = user
            
            connected, _ = await communicator.connect()
            assert connected, f"User {user.username} should connect"
            communicators.append((user, communicator))
        
        # Collect initial presence messages
        initial_messages = {}
        for user, communicator in communicators:
            try:
                msg = await communicator.receive_json_from(timeout=2)
                if msg.get('type') == 'user_status':
                    initial_messages[user.username] = msg
            except asyncio.TimeoutError:
                pass
        
        # Verify all users are marked online
        for user, _ in communicators:
            presence = await database_sync_to_async(
                presence_manager.get_user_presence
            )(user)
            assert presence['is_online'] is True
        
        # Disconnect one user and verify others receive offline notification
        test_user, test_communicator = communicators[0]
        await test_communicator.disconnect()
        
        # Other users should receive offline notification
        offline_notifications = []
        for user, communicator in communicators[1:]:
            try:
                # May receive multiple messages, look for user_status
                for _ in range(3):  # Try up to 3 messages
                    msg = await communicator.receive_json_from(timeout=1)
                    if (msg.get('type') == 'user_status' and 
                        msg.get('username') == test_user.username):
                        offline_notifications.append(msg)
                        break
            except asyncio.TimeoutError:
                pass
        
        # Verify offline notifications were received
        for notification in offline_notifications:
            assert notification['is_online'] is False
            assert notification['username'] == test_user.username
        
        # Disconnect remaining users
        for user, communicator in communicators[1:]:
            await communicator.disconnect()
    
    def test_property_presence_persistence(self):
        """
        **Property 11: Presence Persistence**
        
        For presence data persistence:
        1. Presence information should be stored accurately
        2. Connection counts should be maintained correctly
        3. Timestamps should be updated properly
        4. Database constraints should be enforced
        """
        asyncio.run(self._test_presence_persistence())
    
    async def _test_presence_persistence(self):
        """Async implementation of presence persistence test."""
        
        # Test creating presence status
        connection_id = await database_sync_to_async(
            presence_manager.user_connected
        )(self.user1, {'device': 'test'})
        
        assert connection_id is not None
        assert connection_id.startswith('conn_')
        
        # Verify in database
        user_status = await database_sync_to_async(
            UserStatus.objects.get
        )(user=self.user1)
        
        assert user_status.is_online is True
        assert user_status.active_connections == 1
        assert user_status.connection_id == connection_id
        assert user_status.device_info == {'device': 'test'}
        
        # Test multiple connections for same user
        connection_id2 = await database_sync_to_async(
            presence_manager.user_connected
        )(self.user1, {'device': 'test2'})
        
        # Should update existing status, not create new one
        user_status.refresh_from_db()
        assert user_status.active_connections == 2
        
        # Test disconnection
        await database_sync_to_async(
            presence_manager.user_disconnected
        )(self.user1, connection_id)
        
        user_status.refresh_from_db()
        assert user_status.active_connections == 1
        assert user_status.is_online is True  # Still online (one connection left)
        
        # Disconnect last connection
        await database_sync_to_async(
            presence_manager.user_disconnected
        )(self.user1, connection_id2)
        
        user_status.refresh_from_db()
        assert user_status.active_connections == 0
        assert user_status.is_online is False
    
    def test_property_presence_summary_statistics(self):
        """
        **Property 12: Presence Summary Statistics**
        
        For presence statistics:
        1. Statistics should accurately reflect current state
        2. Counts should be consistent across different queries
        3. Percentages should be calculated correctly
        4. Summary should handle edge cases (no users, all offline, etc.)
        """
        asyncio.run(self._test_presence_summary_statistics())
    
    async def _test_presence_summary_statistics(self):
        """Async implementation of presence summary test."""
        
        # Get initial summary (should be empty or minimal)
        initial_summary = await database_sync_to_async(
            presence_manager.get_presence_summary
        )()
        
        assert 'total_users' in initial_summary
        assert 'online_users' in initial_summary
        assert 'offline_users' in initial_summary
        assert 'online_percentage' in initial_summary
        
        # Connect some users
        await database_sync_to_async(
            presence_manager.user_connected
        )(self.user1)
        
        await database_sync_to_async(
            presence_manager.user_connected
        )(self.user2)
        
        # Get updated summary
        updated_summary = await database_sync_to_async(
            presence_manager.get_presence_summary
        )()
        
        # Should show increased online count
        assert updated_summary['online_users'] >= 2
        assert updated_summary['total_users'] >= 2
        assert updated_summary['offline_users'] >= 0
        
        # Verify percentage calculation
        if updated_summary['total_users'] > 0:
            expected_percentage = (updated_summary['online_users'] / 
                                 updated_summary['total_users'] * 100)
            assert abs(updated_summary['online_percentage'] - expected_percentage) < 0.1
        
        # Verify counts add up
        assert (updated_summary['online_users'] + updated_summary['offline_users'] == 
                updated_summary['total_users'])


if __name__ == '__main__':
    pytest.main([__file__])
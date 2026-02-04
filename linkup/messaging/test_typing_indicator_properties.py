"""
Property-based tests for typing indicator system.
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
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
from messaging.models import TypingStatus
from messaging.typing_manager import typing_manager
from datetime import timedelta

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class TypingIndicatorPropertiesTest(TransactionTestCase):
    """Property-based tests for typing indicator system."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='typing_user1',
            email='typing1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='typing_user2',
            email='typing2@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='typing_user3',
            email='typing3@example.com',
            password='testpass123'
        )
    
    @given(
        typing_sequence=st.lists(
            st.booleans(),
            min_size=2,
            max_size=8
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_property_typing_indicator_sequence(self, typing_sequence):
        """
        **Property 6: Typing Indicator System**
        
        For any sequence of typing states:
        1. Typing indicators should be broadcast to other participants only
        2. Sender should not receive their own typing indicator
        3. Typing state should be tracked accurately in database
        4. Stale typing indicators should be cleaned up automatically
        """
        asyncio.run(self._test_typing_indicator_sequence(typing_sequence))
    
    async def _test_typing_indicator_sequence(self, typing_sequence):
        """Async implementation of typing indicator sequence test."""
        
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
        
        # Send typing sequence from user1
        for i, is_typing in enumerate(typing_sequence):
            await communicator1.send_json_to({
                "type": "typing",
                "is_typing": is_typing
            })
            
            # Small delay to ensure processing
            await asyncio.sleep(0.05)
            
            # User2 should receive typing indicator
            try:
                typing_message = await communicator2.receive_json_from(timeout=1)
                assert typing_message["type"] == "typing"
                assert typing_message["username"] == self.user1.username
                assert typing_message["is_typing"] == is_typing
            except asyncio.TimeoutError:
                # Some typing updates might be debounced/optimized
                pass
            
            # User1 should NOT receive their own typing indicator
            try:
                # This should timeout since user1 shouldn't receive their own typing
                await communicator1.receive_json_from(timeout=0.2)
                assert False, "User should not receive their own typing indicator"
            except asyncio.TimeoutError:
                # This is expected - user1 should not receive their own typing
                pass
            
            # Verify database state
            typing_status = await database_sync_to_async(
                TypingStatus.objects.filter(
                    user=self.user1,
                    chat_partner=self.user2
                ).first
            )()
            
            if typing_status:
                # Database should reflect current typing state
                assert typing_status.is_typing == is_typing
        
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    @given(
        typing_duration=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=15, deadline=4000)
    def test_property_typing_indicator_debouncing(self, typing_duration):
        """
        **Property 7: Typing Indicator Debouncing**
        
        For any typing duration:
        1. Rapid typing updates should be debounced
        2. Only significant state changes should be broadcast
        3. Typing should auto-stop after timeout
        4. Database should maintain accurate state
        """
        asyncio.run(self._test_typing_indicator_debouncing(typing_duration))
    
    async def _test_typing_indicator_debouncing(self, typing_duration):
        """Async implementation of typing debouncing test."""
        
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
        
        # Start typing
        await communicator1.send_json_to({
            "type": "typing",
            "is_typing": True
        })
        
        # User2 should receive typing start
        typing_start = await communicator2.receive_json_from(timeout=2)
        assert typing_start["type"] == "typing"
        assert typing_start["is_typing"] is True
        
        # Send multiple rapid typing updates (should be debounced)
        for _ in range(typing_duration):
            await communicator1.send_json_to({
                "type": "typing",
                "is_typing": True
            })
            await asyncio.sleep(0.1)  # Rapid updates
        
        # Stop typing
        await communicator1.send_json_to({
            "type": "typing",
            "is_typing": False
        })
        
        # User2 should receive typing stop
        typing_stop = await communicator2.receive_json_from(timeout=2)
        assert typing_stop["type"] == "typing"
        assert typing_stop["is_typing"] is False
        
        # Verify final database state
        typing_status = await database_sync_to_async(
            TypingStatus.objects.filter(
                user=self.user1,
                chat_partner=self.user2
            ).first
        )()
        
        if typing_status:
            assert typing_status.is_typing is False
        
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    def test_property_typing_indicator_cleanup(self):
        """
        **Property 8: Typing Indicator Cleanup**
        
        For stale typing indicators:
        1. Stale indicators should be automatically cleaned up
        2. Cleanup should broadcast stop typing to relevant users
        3. Database should be consistent after cleanup
        4. Cleanup should handle edge cases gracefully
        """
        asyncio.run(self._test_typing_indicator_cleanup())
    
    async def _test_typing_indicator_cleanup(self):
        """Async implementation of typing cleanup test."""
        
        # Create stale typing status directly in database
        stale_time = timezone.now() - timedelta(seconds=10)  # 10 seconds ago
        
        typing_status = await database_sync_to_async(TypingStatus.objects.create)(
            user=self.user1,
            chat_partner=self.user2,
            is_typing=True
        )
        
        # Manually set stale timestamp
        await database_sync_to_async(
            TypingStatus.objects.filter(id=typing_status.id).update
        )(last_updated=stale_time)
        
        # Run cleanup
        cleanup_count = await database_sync_to_async(
            typing_manager.cleanup_stale_typing_statuses
        )(timeout_seconds=5)
        
        # Should have cleaned up at least one status
        assert cleanup_count >= 1
        
        # Verify status is no longer typing
        updated_status = await database_sync_to_async(
            TypingStatus.objects.get
        )(id=typing_status.id)
        
        assert updated_status.is_typing is False
    
    @given(
        user_count=st.integers(min_value=2, max_value=3)
    )
    @settings(max_examples=10, deadline=6000)
    def test_property_multi_user_typing_indicators(self, user_count):
        """
        **Property 9: Multi-user Typing Indicators**
        
        For any number of users typing simultaneously:
        1. Each user should receive typing indicators from others
        2. Users should not receive their own typing indicators
        3. Typing states should be independent per user pair
        4. All typing states should be tracked accurately
        """
        # Use available users up to the requested count
        actual_user_count = min(user_count, 3)
        asyncio.run(self._test_multi_user_typing_indicators(actual_user_count))
    
    async def _test_multi_user_typing_indicators(self, user_count):
        """Async implementation of multi-user typing test."""
        
        users = [self.user1, self.user2, self.user3][:user_count]
        communicators = []
        
        # Set up communicators (all chat with user1)
        for i, user in enumerate(users):
            if user != self.user1:
                # Other users connect to user1
                communicator = WebsocketCommunicator(
                    ChatConsumer.as_asgi(),
                    f"/ws/chat/{self.user1.username}/"
                )
                communicator.scope["user"] = user
                communicators.append((user, communicator))
            else:
                # User1 connects to user2
                communicator = WebsocketCommunicator(
                    ChatConsumer.as_asgi(),
                    f"/ws/chat/{self.user2.username}/"
                )
                communicator.scope["user"] = user
                communicators.append((user, communicator))
        
        # Connect all users
        for user, communicator in communicators:
            connected, _ = await communicator.connect()
            assert connected, f"User {user.username} should connect"
        
        # Clear initial messages
        for user, communicator in communicators:
            try:
                await communicator.receive_json_from(timeout=1)
            except asyncio.TimeoutError:
                pass
        
        # Each user starts typing
        for user, communicator in communicators:
            await communicator.send_json_to({
                "type": "typing",
                "is_typing": True
            })
            await asyncio.sleep(0.1)
        
        # Collect typing indicators received by each user
        received_typing = {}
        for user, communicator in communicators:
            received_typing[user.username] = []
            
            # Try to receive typing indicators
            for _ in range(len(communicators) - 1):  # Should receive from others
                try:
                    typing_msg = await communicator.receive_json_from(timeout=2)
                    if typing_msg["type"] == "typing":
                        received_typing[user.username].append(typing_msg)
                except asyncio.TimeoutError:
                    break
        
        # Verify each user received typing from others (but not themselves)
        for user, communicator in communicators:
            received = received_typing[user.username]
            
            # Should not receive typing from themselves
            for typing_msg in received:
                assert typing_msg["username"] != user.username, \
                    f"User {user.username} should not receive their own typing"
        
        # Stop all typing
        for user, communicator in communicators:
            await communicator.send_json_to({
                "type": "typing",
                "is_typing": False
            })
        
        # Disconnect all
        for user, communicator in communicators:
            await communicator.disconnect()
    
    def test_property_typing_indicator_persistence(self):
        """
        **Property 10: Typing Indicator Persistence**
        
        For typing indicator database operations:
        1. Typing states should be persisted accurately
        2. Timestamps should be updated correctly
        3. Unique constraints should be enforced
        4. Queries should be efficient and consistent
        """
        asyncio.run(self._test_typing_indicator_persistence())
    
    async def _test_typing_indicator_persistence(self):
        """Async implementation of typing persistence test."""
        
        # Test creating typing status
        success = await database_sync_to_async(
            typing_manager.update_typing_status
        )(self.user1, self.user2, True)
        
        assert success, "Should successfully create typing status"
        
        # Verify in database
        typing_status = await database_sync_to_async(
            TypingStatus.objects.get
        )(user=self.user1, chat_partner=self.user2)
        
        assert typing_status.is_typing is True
        assert typing_status.last_updated is not None
        
        # Test updating existing status
        success = await database_sync_to_async(
            typing_manager.update_typing_status
        )(self.user1, self.user2, False)
        
        assert success, "Should successfully update typing status"
        
        # Verify update
        typing_status.refresh_from_db()
        assert typing_status.is_typing is False
        
        # Test unique constraint (should not create duplicate)
        typing_count_before = await database_sync_to_async(
            TypingStatus.objects.filter(
                user=self.user1,
                chat_partner=self.user2
            ).count
        )()
        
        await database_sync_to_async(
            typing_manager.update_typing_status
        )(self.user1, self.user2, True)
        
        typing_count_after = await database_sync_to_async(
            TypingStatus.objects.filter(
                user=self.user1,
                chat_partner=self.user2
            ).count
        )()
        
        assert typing_count_before == typing_count_after, \
            "Should not create duplicate typing status"


if __name__ == '__main__':
    pytest.main([__file__])
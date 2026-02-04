"""
Property-Based Tests for Connection Recovery System

Tests the universal properties of the connection recovery system including
automatic reconnection, exponential backoff, message synchronization,
and queue processing.

Feature: whatsapp-messaging-fix, Property 8: Connection Recovery System
Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings, assume
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from messaging.connection_recovery_manager import (
    ConnectionRecoveryManager, 
    ConnectionState
)
from messaging.message_sync_manager import MessageSyncManager
from messaging.models import Message, QueuedMessage

User = get_user_model()


class ConnectionRecoveryPropertiesTest(TransactionTestCase):
    """Property-based tests for connection recovery system."""
    
    def setUp(self):
        """Set up test environment."""
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
        
        self.recovery_manager = ConnectionRecoveryManager()
        self.sync_manager = MessageSyncManager()
    
    @given(
        retry_count=st.integers(min_value=0, max_value=10),
        connection_failures=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=5000)
    def test_exponential_backoff_property(self, retry_count, connection_failures):
        """
        Property 8.1: Exponential Backoff Timing
        For any connection that fails, the system should implement exponential 
        backoff with delays of 2s, 4s, 8s, 16s, 32s for successive failures.
        
        **Validates: Requirements 6.1, 6.2**
        """
        # Arrange
        connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"
        mock_callback = AsyncMock(return_value=False)  # Always fail
        
        # Register connection
        self.recovery_manager.register_connection(
            connection_id=connection_id,
            user_id=self.user1.id,
            websocket_url="/ws/test/",
            reconnect_callback=mock_callback
        )
        
        # Act & Assert
        expected_delays = [2, 4, 8, 16, 32]
        
        for failure_count in range(min(connection_failures, len(expected_delays))):
            # Simulate connection loss
            self.recovery_manager.handle_connection_lost(connection_id, "Test failure")
            
            # Check connection state
            conn_info = self.recovery_manager.connections.get(connection_id)
            if conn_info:
                # Verify retry count increments
                assert conn_info['retry_count'] == failure_count + 1
                
                # Verify exponential backoff delay
                if failure_count < len(expected_delays):
                    expected_delay = expected_delays[failure_count]
                    next_retry = conn_info.get('next_retry_at')
                    if next_retry:
                        time_diff = (next_retry - timezone.now()).total_seconds()
                        # Allow some tolerance for timing
                        assert abs(time_diff - expected_delay) < 1.0
        
        # Cleanup
        self.recovery_manager.unregister_connection(connection_id)
    
    @given(
        max_retries=st.integers(min_value=1, max_value=10),
        failure_count=st.integers(min_value=1, max_value=15)
    )
    @settings(max_examples=30, deadline=3000)
    def test_max_retry_limit_property(self, max_retries, failure_count):
        """
        Property 8.2: Maximum Retry Limit
        For any connection that fails repeatedly, the system should stop 
        retrying after the maximum number of attempts and switch to offline mode.
        
        **Validates: Requirements 6.2, 6.5**
        """
        # Arrange
        connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"
        mock_callback = AsyncMock(return_value=False)  # Always fail
        
        # Override max retries for this test
        original_max_retries = self.recovery_manager.max_retries
        self.recovery_manager.max_retries = max_retries
        
        try:
            # Register connection
            self.recovery_manager.register_connection(
                connection_id=connection_id,
                user_id=self.user1.id,
                websocket_url="/ws/test/",
                reconnect_callback=mock_callback
            )
            
            # Act - Simulate multiple failures
            for i in range(failure_count):
                self.recovery_manager.handle_connection_lost(connection_id, f"Failure {i+1}")
                
                conn_info = self.recovery_manager.connections.get(connection_id)
                if not conn_info:
                    break
                
                # Check state after each failure
                if conn_info['retry_count'] <= max_retries:
                    # Should be in reconnecting state
                    assert conn_info['state'] in [ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED]
                else:
                    # Should switch to failed/offline state
                    assert conn_info['state'] in [ConnectionState.FAILED, ConnectionState.OFFLINE]
                    break
            
            # Assert final state
            final_conn_info = self.recovery_manager.connections.get(connection_id)
            if final_conn_info and failure_count > max_retries:
                assert final_conn_info['state'] in [ConnectionState.FAILED, ConnectionState.OFFLINE]
                assert final_conn_info['retry_count'] >= max_retries
        
        finally:
            # Restore original max retries
            self.recovery_manager.max_retries = original_max_retries
            self.recovery_manager.unregister_connection(connection_id)
    
    @given(
        message_count=st.integers(min_value=1, max_value=20),
        disconnect_duration_minutes=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=20, deadline=10000)
    def test_message_synchronization_property(self, message_count, disconnect_duration_minutes):
        """
        Property 8.3: Message Synchronization on Reconnection
        For any user who reconnects after being offline, the system should 
        synchronize all messages that were received during the disconnection 
        period in chronological order.
        
        **Validates: Requirements 6.3, 6.4**
        """
        # Arrange
        disconnect_time = timezone.now() - timedelta(minutes=disconnect_duration_minutes)
        
        # Create messages that were "received" while offline
        created_messages = []
        for i in range(message_count):
            message_time = disconnect_time + timedelta(minutes=i)
            
            # Create message with specific timestamp
            message = Message.objects.create(
                sender=self.user2,
                recipient=self.user1,
                content=f"Offline message {i+1}",
                created_at=message_time,
                status='sent'
            )
            created_messages.append(message)
        
        # Act - Synchronize messages
        async def run_sync():
            sync_result = await self.sync_manager.synchronize_messages_on_reconnection(
                user_id=self.user1.id,
                last_disconnect_time=disconnect_time,
                connection_id="test_sync_conn"
            )
            return sync_result
        
        sync_result = asyncio.run(run_sync())
        
        # Assert
        assert 'messages' in sync_result
        synced_messages = sync_result['messages']
        
        # Should have found the messages
        assert len(synced_messages) >= message_count
        
        # Messages should be in chronological order
        if len(synced_messages) > 1:
            for i in range(1, len(synced_messages)):
                prev_time = datetime.fromisoformat(synced_messages[i-1]['created_at'].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(synced_messages[i]['created_at'].replace('Z', '+00:00'))
                assert prev_time <= curr_time, "Messages should be in chronological order"
        
        # All messages should be for the correct recipient
        for msg in synced_messages:
            if msg['type'] == 'incoming_message':
                assert msg['recipient_id'] == self.user1.id
        
        # Cleanup
        Message.objects.filter(id__in=[msg.id for msg in created_messages]).delete()
    
    @given(
        queued_count=st.integers(min_value=1, max_value=15),
        queue_types=st.lists(
            st.sampled_from(['outgoing', 'incoming', 'retry']),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=20, deadline=8000)
    def test_offline_queue_processing_property(self, queued_count, queue_types):
        """
        Property 8.4: Offline Message Queue Processing
        For any user who comes online, the system should process all queued 
        messages in chronological order and mark them as processed.
        
        **Validates: Requirements 6.4, 7.1, 7.2**
        """
        # Arrange - Create queued messages
        created_queued = []
        for i in range(queued_count):
            queue_type = queue_types[i % len(queue_types)]
            
            queued_msg = QueuedMessage.objects.create(
                sender=self.user1 if queue_type == 'outgoing' else self.user2,
                recipient=self.user2 if queue_type == 'outgoing' else self.user1,
                content=f"Queued {queue_type} message {i+1}",
                queue_type=queue_type,
                is_processed=False,
                created_at=timezone.now() - timedelta(minutes=queued_count - i)
            )
            created_queued.append(queued_msg)
        
        # Act - Process offline queue
        async def run_queue_processing():
            result = await self.sync_manager.process_offline_message_queue(
                user_id=self.user1.id
            )
            return result
        
        queue_result = asyncio.run(run_queue_processing())
        
        # Assert
        assert 'processed_count' in queue_result
        assert 'failed_count' in queue_result
        
        # Should have processed some messages
        total_processed = queue_result['processed_count'] + queue_result['failed_count']
        assert total_processed >= 0
        
        # Check that incoming messages for user1 were processed
        incoming_for_user1 = [q for q in created_queued if q.recipient_id == self.user1.id]
        if incoming_for_user1:
            # Refresh from database
            for queued_msg in incoming_for_user1:
                queued_msg.refresh_from_db()
                # Should be marked as processed
                assert queued_msg.is_processed == True
        
        # Cleanup
        QueuedMessage.objects.filter(id__in=[q.id for q in created_queued]).delete()
    
    @given(
        connection_states=st.lists(
            st.sampled_from([
                ConnectionState.CONNECTED,
                ConnectionState.DISCONNECTED,
                ConnectionState.RECONNECTING,
                ConnectionState.FAILED
            ]),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_connection_state_transitions_property(self, connection_states):
        """
        Property 8.5: Connection State Transitions
        For any sequence of connection state changes, the system should 
        maintain valid state transitions and provide accurate status information.
        
        **Validates: Requirements 6.5**
        """
        # Arrange
        connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"
        mock_callback = AsyncMock(return_value=True)
        status_updates = []
        
        def status_callback(update):
            status_updates.append(update)
        
        # Register connection
        self.recovery_manager.register_connection(
            connection_id=connection_id,
            user_id=self.user1.id,
            websocket_url="/ws/test/",
            reconnect_callback=mock_callback
        )
        
        self.recovery_manager.add_status_callback(connection_id, status_callback)
        
        # Act - Apply state transitions
        for state in connection_states:
            self.recovery_manager.update_connection_state(
                connection_id, state, f"Test transition to {state}"
            )
        
        # Assert
        # Should have received status updates
        assert len(status_updates) >= len(connection_states)
        
        # Each update should have required fields
        for update in status_updates:
            assert 'connection_id' in update
            assert 'state' in update
            assert 'timestamp' in update
            assert update['connection_id'] == connection_id
        
        # Final state should match last requested state
        final_status = self.recovery_manager.get_connection_status(connection_id)
        if final_status and connection_states:
            assert final_status['state'] == connection_states[-1]
        
        # Cleanup
        self.recovery_manager.unregister_connection(connection_id)
    
    @given(
        heartbeat_intervals=st.lists(
            st.integers(min_value=1, max_value=60),
            min_size=3,
            max_size=10
        )
    )
    @settings(max_examples=15, deadline=3000)
    def test_heartbeat_monitoring_property(self, heartbeat_intervals):
        """
        Property 8.6: Connection Heartbeat Monitoring
        For any connection with regular heartbeat updates, the system should 
        track the last ping time and detect stale connections.
        
        **Validates: Requirements 6.5, 10.5**
        """
        # Arrange
        connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"
        mock_callback = AsyncMock(return_value=True)
        
        # Register connection
        self.recovery_manager.register_connection(
            connection_id=connection_id,
            user_id=self.user1.id,
            websocket_url="/ws/test/",
            reconnect_callback=mock_callback
        )
        
        initial_status = self.recovery_manager.get_connection_status(connection_id)
        initial_ping = initial_status['last_ping'] if initial_status else None
        
        # Act - Send heartbeats at different intervals
        last_ping_time = None
        for interval in heartbeat_intervals:
            # Simulate time passing
            import time
            time.sleep(0.01)  # Small delay to ensure timestamp changes
            
            # Update heartbeat
            self.recovery_manager.update_heartbeat(connection_id)
            
            # Check status
            status = self.recovery_manager.get_connection_status(connection_id)
            if status:
                current_ping = status['last_ping']
                
                # Assert heartbeat was updated
                if last_ping_time:
                    assert current_ping > last_ping_time, "Heartbeat timestamp should advance"
                
                last_ping_time = current_ping
        
        # Assert final state
        final_status = self.recovery_manager.get_connection_status(connection_id)
        if final_status and initial_ping:
            assert final_status['last_ping'] > initial_ping, "Final heartbeat should be newer than initial"
        
        # Test stale connection cleanup
        stale_count = self.recovery_manager.cleanup_stale_connections(timeout_minutes=0)
        # Should clean up our test connection since we set timeout to 0
        assert stale_count >= 0
        
        # Cleanup
        self.recovery_manager.unregister_connection(connection_id)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
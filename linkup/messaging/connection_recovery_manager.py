"""
Connection Recovery Manager for WhatsApp-like Messaging System

Handles automatic WebSocket reconnection with exponential backoff,
connection status management, and message synchronization on reconnection.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class ConnectionState:
    """Connection state constants"""
    CONNECTED = 'connected'
    CONNECTING = 'connecting'
    RECONNECTING = 'reconnecting'
    DISCONNECTED = 'disconnected'
    FAILED = 'failed'
    OFFLINE = 'offline'


class ConnectionRecoveryManager:
    """
    Manages WebSocket connection recovery with exponential backoff.
    
    Features:
    - Automatic reconnection within 2 seconds
    - Exponential backoff: 2s, 4s, 8s, 16s, 32s
    - Maximum 5 retry attempts
    - Connection status indicators
    - Message synchronization on reconnection
    - Queue processing for offline messages
    """
    
    def __init__(self):
        self.connections: Dict[str, Dict] = {}
        self.retry_intervals = [2, 4, 8, 16, 32]  # Exponential backoff in seconds
        self.max_retries = 5
        self.initial_retry_delay = 2
        self.connection_timeout = 10  # seconds
        
    def register_connection(self, connection_id: str, user_id: int, 
                          websocket_url: str, reconnect_callback: Callable) -> None:
        """
        Register a WebSocket connection for recovery management.
        
        Args:
            connection_id: Unique identifier for the connection
            user_id: User ID associated with the connection
            websocket_url: WebSocket URL to reconnect to
            reconnect_callback: Function to call for reconnection
        """
        self.connections[connection_id] = {
            'user_id': user_id,
            'websocket_url': websocket_url,
            'reconnect_callback': reconnect_callback,
            'state': ConnectionState.CONNECTED,
            'retry_count': 0,
            'last_attempt': None,
            'next_retry_at': None,
            'connected_at': timezone.now(),
            'last_ping': timezone.now(),
            'missed_messages': [],
            'queued_messages': [],
            'status_callbacks': [],
            'recovery_task': None
        }
        
        logger.info(f"Registered connection {connection_id} for user {user_id}")
    
    def unregister_connection(self, connection_id: str) -> None:
        """
        Unregister a connection from recovery management.
        
        Args:
            connection_id: Connection identifier to unregister
        """
        if connection_id in self.connections:
            conn_info = self.connections[connection_id]
            
            # Cancel any ongoing recovery task
            if conn_info.get('recovery_task'):
                conn_info['recovery_task'].cancel()
            
            del self.connections[connection_id]
            logger.info(f"Unregistered connection {connection_id}")
    
    def add_status_callback(self, connection_id: str, callback: Callable) -> None:
        """
        Add a callback for connection status updates.
        
        Args:
            connection_id: Connection identifier
            callback: Function to call with status updates
        """
        if connection_id in self.connections:
            self.connections[connection_id]['status_callbacks'].append(callback)
    
    def update_connection_state(self, connection_id: str, state: str, 
                              error_message: str = None) -> None:
        """
        Update connection state and notify callbacks.
        
        Args:
            connection_id: Connection identifier
            state: New connection state
            error_message: Optional error message
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        old_state = conn_info['state']
        conn_info['state'] = state
        
        # Update timestamps
        if state == ConnectionState.CONNECTED:
            conn_info['connected_at'] = timezone.now()
            conn_info['retry_count'] = 0
            conn_info['last_ping'] = timezone.now()
        elif state == ConnectionState.DISCONNECTED:
            conn_info['last_attempt'] = timezone.now()
        
        # Notify status callbacks
        status_update = {
            'connection_id': connection_id,
            'state': state,
            'old_state': old_state,
            'retry_count': conn_info['retry_count'],
            'next_retry_at': conn_info.get('next_retry_at'),
            'error_message': error_message,
            'timestamp': timezone.now().isoformat()
        }
        
        for callback in conn_info['status_callbacks']:
            try:
                callback(status_update)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
        
        logger.info(f"Connection {connection_id} state: {old_state} -> {state}")
    
    def handle_connection_lost(self, connection_id: str, error_message: str = None) -> None:
        """
        Handle connection loss and initiate recovery.
        
        Args:
            connection_id: Connection identifier
            error_message: Optional error message
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        
        # Update state to disconnected
        self.update_connection_state(connection_id, ConnectionState.DISCONNECTED, error_message)
        
        # Start recovery process
        if conn_info['retry_count'] < self.max_retries:
            self._schedule_reconnection(connection_id)
        else:
            # Max retries exceeded, switch to offline mode
            self.update_connection_state(connection_id, ConnectionState.FAILED, 
                                       "Maximum retry attempts exceeded")
            self._switch_to_offline_mode(connection_id)
    
    def _schedule_reconnection(self, connection_id: str) -> None:
        """
        Schedule reconnection attempt with exponential backoff.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        retry_count = conn_info['retry_count']
        
        # Calculate delay with exponential backoff
        if retry_count < len(self.retry_intervals):
            delay = self.retry_intervals[retry_count]
        else:
            delay = self.retry_intervals[-1]  # Use maximum delay
        
        conn_info['next_retry_at'] = timezone.now() + timedelta(seconds=delay)
        conn_info['retry_count'] += 1
        
        # Update state to reconnecting
        self.update_connection_state(connection_id, ConnectionState.RECONNECTING)
        
        # Schedule the reconnection attempt
        conn_info['recovery_task'] = asyncio.create_task(
            self._attempt_reconnection(connection_id, delay)
        )
        
        logger.info(f"Scheduled reconnection for {connection_id} in {delay}s (attempt {retry_count + 1})")
    
    async def _attempt_reconnection(self, connection_id: str, delay: float) -> None:
        """
        Attempt to reconnect after delay.
        
        Args:
            connection_id: Connection identifier
            delay: Delay before attempting reconnection
        """
        try:
            # Wait for the delay
            await asyncio.sleep(delay)
            
            if connection_id not in self.connections:
                return
            
            conn_info = self.connections[connection_id]
            
            logger.info(f"Attempting reconnection for {connection_id}")
            
            # Update state to connecting
            self.update_connection_state(connection_id, ConnectionState.CONNECTING)
            
            # Call the reconnection callback
            success = await self._execute_reconnection(connection_id)
            
            if success:
                # Reconnection successful
                self.update_connection_state(connection_id, ConnectionState.CONNECTED)
                
                # Synchronize missed messages
                await self._synchronize_missed_messages(connection_id)
                
                # Process queued messages
                await self._process_queued_messages(connection_id)
                
                logger.info(f"Successfully reconnected {connection_id}")
            else:
                # Reconnection failed, schedule next attempt
                if conn_info['retry_count'] < self.max_retries:
                    self._schedule_reconnection(connection_id)
                else:
                    # Max retries exceeded
                    self.update_connection_state(connection_id, ConnectionState.FAILED,
                                               "Reconnection failed after maximum attempts")
                    self._switch_to_offline_mode(connection_id)
        
        except asyncio.CancelledError:
            logger.info(f"Reconnection cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error during reconnection attempt for {connection_id}: {e}")
            
            if connection_id in self.connections:
                conn_info = self.connections[connection_id]
                if conn_info['retry_count'] < self.max_retries:
                    self._schedule_reconnection(connection_id)
                else:
                    self.update_connection_state(connection_id, ConnectionState.FAILED, str(e))
                    self._switch_to_offline_mode(connection_id)
    
    async def _execute_reconnection(self, connection_id: str) -> bool:
        """
        Execute the actual reconnection attempt.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        if connection_id not in self.connections:
            return False
        
        conn_info = self.connections[connection_id]
        
        try:
            # Call the reconnection callback with timeout
            reconnect_callback = conn_info['reconnect_callback']
            
            # Execute with timeout
            success = await asyncio.wait_for(
                reconnect_callback(),
                timeout=self.connection_timeout
            )
            
            return success
        
        except asyncio.TimeoutError:
            logger.error(f"Reconnection timeout for {connection_id}")
            return False
        except Exception as e:
            logger.error(f"Reconnection error for {connection_id}: {e}")
            return False
    
    async def _synchronize_missed_messages(self, connection_id: str) -> None:
        """
        Synchronize messages that were missed during disconnection.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        user_id = conn_info['user_id']
        
        try:
            # Import here to avoid circular imports
            from .models import Message
            
            # Get messages received while disconnected
            disconnect_time = conn_info.get('last_attempt')
            if disconnect_time:
                missed_messages = Message.objects.filter(
                    recipient_id=user_id,
                    created_at__gte=disconnect_time
                ).order_by('created_at')
                
                # Store missed messages for delivery
                conn_info['missed_messages'] = [
                    {
                        'id': msg.id,
                        'sender': msg.sender.username,
                        'content': msg.content,
                        'created_at': msg.created_at.isoformat(),
                        'status': msg.status
                    }
                    for msg in missed_messages
                ]
                
                logger.info(f"Found {len(conn_info['missed_messages'])} missed messages for {connection_id}")
        
        except Exception as e:
            logger.error(f"Error synchronizing missed messages for {connection_id}: {e}")
    
    async def _process_queued_messages(self, connection_id: str) -> None:
        """
        Process messages that were queued during disconnection.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        queued_messages = conn_info.get('queued_messages', [])
        
        if not queued_messages:
            return
        
        try:
            # Process each queued message
            for message in queued_messages:
                # Attempt to send the message
                success = await self._send_queued_message(connection_id, message)
                if not success:
                    logger.warning(f"Failed to send queued message {message.get('id')}")
            
            # Clear processed messages
            conn_info['queued_messages'] = []
            
            logger.info(f"Processed {len(queued_messages)} queued messages for {connection_id}")
        
        except Exception as e:
            logger.error(f"Error processing queued messages for {connection_id}: {e}")
    
    async def _send_queued_message(self, connection_id: str, message: Dict) -> bool:
        """
        Send a queued message.
        
        Args:
            connection_id: Connection identifier
            message: Message to send
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            # This would integrate with the actual message sending mechanism
            # For now, we'll simulate success
            logger.info(f"Sending queued message {message.get('id')} for {connection_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending queued message: {e}")
            return False
    
    def _switch_to_offline_mode(self, connection_id: str) -> None:
        """
        Switch connection to offline mode after max retries exceeded.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        
        # Update state to offline
        self.update_connection_state(connection_id, ConnectionState.OFFLINE,
                                   "Switched to offline mode")
        
        logger.info(f"Connection {connection_id} switched to offline mode")
    
    def queue_message_for_retry(self, connection_id: str, message: Dict) -> None:
        """
        Queue a message for retry when connection is restored.
        
        Args:
            connection_id: Connection identifier
            message: Message to queue
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        conn_info['queued_messages'].append(message)
        
        logger.info(f"Queued message for retry on {connection_id}")
    
    def update_heartbeat(self, connection_id: str) -> None:
        """
        Update heartbeat timestamp for connection health monitoring.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connections:
            self.connections[connection_id]['last_ping'] = timezone.now()
    
    def get_connection_status(self, connection_id: str) -> Optional[Dict]:
        """
        Get current connection status information.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Dict with connection status information or None if not found
        """
        if connection_id not in self.connections:
            return None
        
        conn_info = self.connections[connection_id]
        
        return {
            'connection_id': connection_id,
            'user_id': conn_info['user_id'],
            'state': conn_info['state'],
            'retry_count': conn_info['retry_count'],
            'max_retries': self.max_retries,
            'connected_at': conn_info.get('connected_at'),
            'last_ping': conn_info.get('last_ping'),
            'next_retry_at': conn_info.get('next_retry_at'),
            'missed_messages_count': len(conn_info.get('missed_messages', [])),
            'queued_messages_count': len(conn_info.get('queued_messages', []))
        }
    
    def get_all_connections_status(self) -> List[Dict]:
        """
        Get status information for all managed connections.
        
        Returns:
            List of connection status dictionaries
        """
        return [
            self.get_connection_status(conn_id)
            for conn_id in self.connections.keys()
        ]
    
    def force_reconnect(self, connection_id: str) -> None:
        """
        Force immediate reconnection attempt (manual retry).
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        conn_info = self.connections[connection_id]
        
        # Cancel any existing recovery task
        if conn_info.get('recovery_task'):
            conn_info['recovery_task'].cancel()
        
        # Reset retry count for manual retry
        conn_info['retry_count'] = 0
        
        # Schedule immediate reconnection
        conn_info['recovery_task'] = asyncio.create_task(
            self._attempt_reconnection(connection_id, 0)
        )
        
        logger.info(f"Forced reconnection initiated for {connection_id}")
    
    def cleanup_stale_connections(self, timeout_minutes: int = 30) -> int:
        """
        Clean up connections that haven't had heartbeat updates.
        
        Args:
            timeout_minutes: Minutes without heartbeat before cleanup
            
        Returns:
            Number of connections cleaned up
        """
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)
        stale_connections = []
        
        for conn_id, conn_info in self.connections.items():
            last_ping = conn_info.get('last_ping')
            if last_ping and last_ping < cutoff_time:
                stale_connections.append(conn_id)
        
        # Clean up stale connections
        for conn_id in stale_connections:
            self.unregister_connection(conn_id)
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections")
        
        return len(stale_connections)


# Global instance
connection_recovery_manager = ConnectionRecoveryManager()
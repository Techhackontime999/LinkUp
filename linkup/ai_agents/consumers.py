"""
WebSocket consumers for AI agent real-time communication.

This module provides WebSocket support for AI agents to:
- Establish authenticated connections using JWT tokens
- Receive messages in real-time
- Maintain online/offline status
- Handle connection lifecycle events
"""
import json
import logging
from typing import Optional, Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from .models import AIAgent, AgentMessage
from .services import AgentAuthenticationService
from .metrics_tracker import SystemMetricsTracker

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for AI agent connections.
    
    Handles:
    - JWT-based authentication
    - Real-time message delivery
    - Connection state management
    - Agent online/offline status tracking
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = None
        self.agent_id = None
        self.channel_group_name = None
    
    async def connect(self):
        """
        Handle WebSocket connection with JWT authentication.
        
        Authentication flow:
        1. Extract JWT token from query parameters or headers
        2. Validate token and extract agent_id
        3. Verify agent exists and is active
        4. Accept connection and mark agent as online
        5. Add agent to their personal channel group
        
        Requirements: 13.1, 13.2
        """
        try:
            # Step 1: Extract JWT token from query string or headers
            token = await self._extract_jwt_token()
            
            if not token:
                logger.warning("WebSocket connection attempt without JWT token")
                await self.close(code=4001)  # Unauthorized
                return
            
            # Step 2: Validate JWT token and extract agent_id
            token_data = await self._validate_jwt_token(token)
            
            if not token_data or not token_data.get('valid'):
                logger.warning(f"Invalid JWT token: {token_data.get('error', 'Unknown error')}")
                await self.close(code=4001)  # Unauthorized
                return
            
            self.agent_id = token_data['agent_id']
            
            # Step 3: Retrieve and validate agent
            self.agent = await self._get_agent(self.agent_id)
            
            if not self.agent:
                logger.warning(f"Agent not found: {self.agent_id}")
                await self.close(code=4004)  # Not found
                return
            
            if not self.agent.is_active:
                logger.warning(f"Inactive agent connection attempt: {self.agent_id}")
                await self.close(code=4003)  # Forbidden
                return
            
            if self.agent.is_suspended:
                logger.warning(f"Suspended agent connection attempt: {self.agent_id}")
                await self.close(code=4003)  # Forbidden
                return
            
            # Step 4: Accept the WebSocket connection
            await self.accept()
            
            # Step 5: Assign unique channel name based on agent ID
            self.channel_group_name = f'agent_{self.agent_id}'
            
            # Step 6: Add agent to their personal channel group
            await self.channel_layer.group_add(
                self.channel_group_name,
                self.channel_name
            )
            
            # Step 7: Mark agent as online in cache
            await self._set_agent_online(self.agent_id, True)
            
            # Step 7.1: Track WebSocket connection in metrics
            await self._track_websocket_connection(self.agent_id, True)
            
            # Step 8: Log successful connection
            logger.info(f"Agent connected: {self.agent.name} (ID: {self.agent_id})")
            
            # Step 9: Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'agent_id': str(self.agent_id),
                'agent_name': self.agent.name,
                'timestamp': timezone.now().isoformat()
            }))
            
            # Step 10: Deliver any queued messages
            await self._deliver_queued_messages()
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}", exc_info=True)
            await self._log_connection_failure(str(e))
            await self.close(code=4000)  # Internal error
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Cleanup flow:
        1. Remove agent from channel group
        2. Mark agent as offline
        3. Log disconnection event
        
        Requirements: 13.4
        """
        try:
            # Step 1: Remove from channel group
            if self.channel_group_name:
                await self.channel_layer.group_discard(
                    self.channel_group_name,
                    self.channel_name
                )
            
            # Step 2: Mark agent as offline
            if self.agent_id:
                await self._set_agent_online(self.agent_id, False)
                
                # Track WebSocket disconnection in metrics
                await self._track_websocket_connection(self.agent_id, False)
                
                logger.info(f"Agent disconnected: {self.agent_id} (code: {close_code})")
            
        except Exception as e:
            logger.error(f"Error in WebSocket disconnect: {e}", exc_info=True)
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming WebSocket messages from agent.
        
        This method can be extended to handle agent-initiated messages,
        such as message acknowledgments or status updates.
        
        Args:
            text_data: Text message data
            bytes_data: Binary message data
        """
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'ping':
                    # Respond to ping with pong
                    await self.send(text_data=json.dumps({
                        'type': 'pong',
                        'timestamp': timezone.now().isoformat()
                    }))
                
                elif message_type == 'message_ack':
                    # Handle message acknowledgment
                    message_id = data.get('message_id')
                    if message_id:
                        await self._handle_message_acknowledgment(message_id)
                
                else:
                    logger.warning(f"Unknown message type from agent {self.agent_id}: {message_type}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from agent {self.agent_id}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from agent {self.agent_id}: {e}", exc_info=True)
    
    async def agent_message(self, event):
        """
        Handle agent_message event from channel layer.
        
        This method is called when a message is sent to the agent's channel group.
        It delivers the message to the connected agent via WebSocket.
        
        Args:
            event: Dictionary containing message data
        
        Requirements: 13.3, 14.3
        """
        try:
            # Extract message data from event
            message_data = {
                'type': 'agent_message',
                'message_id': event.get('message_id'),
                'sender_id': event.get('sender_id'),
                'sender_name': event.get('sender_name'),
                'content': event.get('content'),
                'metadata': event.get('metadata', {}),
                'timestamp': event.get('timestamp'),
                'parent_message_id': event.get('parent_message_id')
            }
            
            # Send message to WebSocket
            await self.send(text_data=json.dumps(message_data))
            
            # Update message status to DELIVERED
            message_id = event.get('message_id')
            if message_id:
                await self._update_message_status(message_id, 'DELIVERED')
            
            logger.debug(f"Message delivered to agent {self.agent_id}: {message_id}")
            
        except Exception as e:
            logger.error(f"Error delivering message to agent {self.agent_id}: {e}", exc_info=True)
            
            # Log delivery failure
            message_id = event.get('message_id')
            if message_id:
                await self._log_delivery_failure(message_id, str(e))
    
    # Helper methods
    
    async def _extract_jwt_token(self) -> Optional[str]:
        """
        Extract JWT token from query parameters or headers.
        
        Returns:
            JWT token string or None if not found
        """
        # Try query parameters first (e.g., ws://host/path?token=xxx)
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        if query_string:
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token = params.get('token')
            if token:
                return token
        
        # Try headers (e.g., Authorization: Bearer xxx)
        headers = dict(self.scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode('utf-8')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        return None
    
    @database_sync_to_async
    def _validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and extract agent_id.
        
        Args:
            token: JWT token string
        
        Returns:
            Dictionary with validation result and agent_id
        """
        try:
            # Use the authentication service to validate token
            import jwt
            from django.conf import settings
            
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # Extract agent_id from payload
            agent_id = payload.get('agent_id')
            
            if not agent_id:
                return {
                    'valid': False,
                    'error': 'Missing agent_id in token'
                }
            
            # Check token expiration
            import time
            expires_at = payload.get('expires_at')
            if expires_at and time.time() > expires_at:
                return {
                    'valid': False,
                    'error': 'Token expired'
                }
            
            return {
                'valid': True,
                'agent_id': agent_id,
                'scopes': payload.get('scopes', [])
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Token expired'
            }
        except jwt.InvalidTokenError as e:
            return {
                'valid': False,
                'error': f'Invalid token: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}", exc_info=True)
            return {
                'valid': False,
                'error': str(e)
            }
    
    @database_sync_to_async
    def _get_agent(self, agent_id: str) -> Optional[AIAgent]:
        """
        Retrieve agent from database.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            AIAgent instance or None if not found
        """
        try:
            return AIAgent.objects.get(id=agent_id)
        except AIAgent.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_id}: {e}", exc_info=True)
            return None
    
    async def _set_agent_online(self, agent_id: str, is_online: bool):
        """
        Set agent online/offline status in cache.
        
        Args:
            agent_id: UUID of the agent
            is_online: True if online, False if offline
        
        Requirements: 13.4
        """
        try:
            cache_key = f'agent_online:{agent_id}'
            
            if is_online:
                # Set online status with 5-minute TTL (will be refreshed by heartbeat)
                cache.set(cache_key, True, timeout=300)
            else:
                # Remove online status
                cache.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error setting agent online status: {e}", exc_info=True)
    
    @database_sync_to_async
    def _track_websocket_connection(self, agent_id: str, connected: bool):
        """
        Track WebSocket connection in system metrics.
        
        Args:
            agent_id: UUID of the agent
            connected: True if connecting, False if disconnecting
        
        Requirements: 20.4
        """
        try:
            SystemMetricsTracker.track_websocket_connection(agent_id, connected)
        except Exception as e:
            logger.error(f"Error tracking WebSocket connection: {e}", exc_info=True)
    
    @database_sync_to_async
    def _update_message_status(self, message_id: str, status: str):
        """
        Update message status in database.
        
        Args:
            message_id: UUID of the message
            status: New status (DELIVERED, READ, etc.)
        
        Requirements: 14.3
        """
        try:
            message = AgentMessage.objects.get(id=message_id)
            message.status = status
            
            if status == 'DELIVERED':
                message.delivered_at = timezone.now()
            elif status == 'READ':
                message.read_at = timezone.now()
            
            message.save()
            
        except AgentMessage.DoesNotExist:
            logger.warning(f"Message not found for status update: {message_id}")
        except Exception as e:
            logger.error(f"Error updating message status: {e}", exc_info=True)
    
    @database_sync_to_async
    def _handle_message_acknowledgment(self, message_id: str):
        """
        Handle message acknowledgment from agent.
        
        Args:
            message_id: UUID of the acknowledged message
        """
        try:
            message = AgentMessage.objects.get(id=message_id)
            
            # Update status to READ if not already
            if message.status != 'READ':
                message.status = 'READ'
                message.read_at = timezone.now()
                message.save()
                
                logger.debug(f"Message acknowledged: {message_id}")
            
        except AgentMessage.DoesNotExist:
            logger.warning(f"Message not found for acknowledgment: {message_id}")
        except Exception as e:
            logger.error(f"Error handling message acknowledgment: {e}", exc_info=True)
    
    @database_sync_to_async
    def _log_connection_failure(self, error: str):
        """
        Log connection failure to database.
        
        Args:
            error: Error message
        
        Requirements: 13.5, 15.2
        """
        try:
            # Log to Django logger
            logger.error(f"WebSocket connection failure: {error}")
            
            # Could also log to a MessagingError or similar model if needed
            # For now, we rely on Django's logging infrastructure
            
        except Exception as e:
            logger.error(f"Error logging connection failure: {e}", exc_info=True)
    
    @database_sync_to_async
    def _log_delivery_failure(self, message_id: str, error: str):
        """
        Log message delivery failure.
        
        Args:
            message_id: UUID of the message
            error: Error message
        
        Requirements: 13.5, 15.2
        """
        try:
            # Update message status to FAILED
            message = AgentMessage.objects.get(id=message_id)
            message.status = 'FAILED'
            message.save()
            
            # Log the failure
            logger.error(f"Message delivery failed: {message_id} - {error}")
            
        except AgentMessage.DoesNotExist:
            logger.warning(f"Message not found for delivery failure logging: {message_id}")
        except Exception as e:
            logger.error(f"Error logging delivery failure: {e}", exc_info=True)
    
    @database_sync_to_async
    def _deliver_queued_messages(self):
        """
        Deliver queued messages when agent comes online.
        
        Requirements: 4.3, 13.3
        """
        try:
            from .offline_queue_manager import OfflineQueueManager
            
            # Deliver queued messages
            result = OfflineQueueManager.deliver_queued_messages(str(self.agent_id))
            
            if result.get('success'):
                delivered = result.get('delivered', 0)
                failed = result.get('failed', 0)
                
                if delivered > 0:
                    logger.info(f"Delivered {delivered} queued messages to agent {self.agent_id}")
                
                if failed > 0:
                    logger.warning(f"Failed to deliver {failed} queued messages to agent {self.agent_id}")
            else:
                logger.error(f"Error delivering queued messages: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error in _deliver_queued_messages: {e}", exc_info=True)

"""
WebSocket consumer for AI Agent Social Platform real-time notifications.

This module provides WebSocket support for:
- Real-time notification delivery
- JWT authentication
- Heartbeat/ping-pong mechanism
- Connection management
"""
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class SocialNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for social platform notifications.
    
    Handles:
    - JWT-based authentication
    - Real-time notification delivery
    - Heartbeat mechanism
    - Connection state management
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = None
        self.agent_id = None
        self.channel_group_name = None
        self.heartbeat_task = None
    
    async def connect(self):
        """
        Handle WebSocket connection with JWT authentication.
        
        Requirements: 16.1, 16.2, 16.4
        """
        try:
            # Extract JWT token
            token = await self._extract_jwt_token()
            
            if not token:
                logger.warning("WebSocket connection attempt without JWT token")
                await self.close(code=4001)
                return
            
            # Validate JWT token
            token_data = await self._validate_jwt_token(token)
            
            if not token_data or not token_data.get('valid'):
                logger.warning(f"Invalid JWT token: {token_data.get('error', 'Unknown error')}")
                await self.close(code=4001)
                return
            
            self.agent_id = token_data['agent_id']
            
            # Retrieve agent
            self.agent = await self._get_agent(self.agent_id)
            
            if not self.agent:
                logger.warning(f"Agent not found: {self.agent_id}")
                await self.close(code=4004)
                return
            
            # Accept connection
            await self.accept()
            
            # Add to channel group
            self.channel_group_name = f'social_agent_{self.agent_id}'
            await self.channel_layer.group_add(
                self.channel_group_name,
                self.channel_name
            )
            
            # Mark agent as online
            await self._set_agent_online(self.agent_id, True)
            
            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"Social WebSocket connected: {self.agent_id}")
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'agent_id': str(self.agent_id),
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}", exc_info=True)
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Requirements: 16.5
        """
        try:
            # Cancel heartbeat
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            
            # Remove from channel group
            if self.channel_group_name:
                await self.channel_layer.group_discard(
                    self.channel_group_name,
                    self.channel_name
                )
            
            # Mark agent as offline
            if self.agent_id:
                await self._set_agent_online(self.agent_id, False)
                logger.info(f"Social WebSocket disconnected: {self.agent_id} (code: {close_code})")
            
        except Exception as e:
            logger.error(f"Error in WebSocket disconnect: {e}", exc_info=True)
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming WebSocket messages.
        
        Supports:
        - ping/pong for heartbeat
        - notification acknowledgments
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
                
                elif message_type == 'notification_ack':
                    # Handle notification acknowledgment
                    notification_id = data.get('notification_id')
                    if notification_id:
                        await self._mark_notification_read(notification_id)
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    async def social_notification(self, event):
        """
        Handle social_notification event from channel layer.
        
        Delivers notifications to connected agents via WebSocket.
        
        Requirements: 12.4, 12.9, 16.3, 16.6
        """
        try:
            # Extract notification data
            notification_data = {
                'type': 'notification',
                'notification_id': event.get('notification_id'),
                'notification_type': event.get('notification_type'),
                'priority': event.get('priority'),
                'title': event.get('title'),
                'message': event.get('message'),
                'metadata': event.get('metadata', {}),
                'sender_id': event.get('sender_id'),
                'sender_name': event.get('sender_name'),
                'timestamp': event.get('timestamp')
            }
            
            # Send notification to WebSocket
            await self.send(text_data=json.dumps(notification_data))
            
            logger.debug(f"Notification delivered via WebSocket: {event.get('notification_id')}")
            
        except Exception as e:
            logger.error(f"Error delivering notification: {e}", exc_info=True)
            
            # Fallback: notification remains in database for later retrieval
            notification_id = event.get('notification_id')
            if notification_id:
                logger.info(f"Notification {notification_id} will be retrieved from database")
    
    async def _heartbeat_loop(self):
        """
        Send periodic heartbeat pings to keep connection alive.
        
        Requirements: 16.4
        """
        try:
            while True:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': timezone.now().isoformat()
                }))
                
                # Refresh online status in cache
                await self._set_agent_online(self.agent_id, True)
                
        except asyncio.CancelledError:
            # Task was cancelled (connection closed)
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
    
    # Helper methods
    
    async def _extract_jwt_token(self) -> Optional[str]:
        """Extract JWT token from query parameters or headers."""
        # Try query parameters
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        if query_string:
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token = params.get('token')
            if token:
                return token
        
        # Try headers
        headers = dict(self.scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode('utf-8')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        return None
    
    @database_sync_to_async
    def _validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and extract agent_id."""
        try:
            import jwt
            from django.conf import settings
            
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            agent_id = payload.get('agent_id')
            
            if not agent_id:
                return {
                    'valid': False,
                    'error': 'Missing agent_id in token'
                }
            
            # Check expiration
            import time
            expires_at = payload.get('expires_at')
            if expires_at and time.time() > expires_at:
                return {
                    'valid': False,
                    'error': 'Token expired'
                }
            
            return {
                'valid': True,
                'agent_id': agent_id
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
    def _get_agent(self, agent_id: str):
        """Retrieve agent from database."""
        try:
            from .models import AIAgent
            return AIAgent.objects.get(id=agent_id)
        except Exception as e:
            logger.error(f"Error retrieving agent: {e}", exc_info=True)
            return None
    
    async def _set_agent_online(self, agent_id: str, is_online: bool):
        """Set agent online/offline status in cache."""
        try:
            cache_key = f'social_agent_online:{agent_id}'
            
            if is_online:
                cache.set(cache_key, True, timeout=60)  # 1-minute TTL
            else:
                cache.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error setting agent online status: {e}", exc_info=True)
    
    @database_sync_to_async
    def _mark_notification_read(self, notification_id: str):
        """Mark notification as read."""
        try:
            from .social_models import AgentNotification
            
            notification = AgentNotification.objects.get(id=notification_id)
            notification.mark_as_read()
            
            logger.debug(f"Notification marked as read: {notification_id}")
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}", exc_info=True)

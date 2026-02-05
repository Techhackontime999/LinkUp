import json
import time
from datetime import datetime
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message, UserStatus, Notification
from .async_handlers import AsyncSafeMessageHandler
from .serializers import JSONSerializer
from .connection_validator import ConnectionValidator
from .logging_utils import MessagingLogger
from .retry_handler import MessageRetryHandler, MessageValidator, RetryConfig

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_handler = AsyncSafeMessageHandler()
        self.json_serializer = JSONSerializer()
        self.connection_validator = ConnectionValidator()
        self.retry_handler = MessageRetryHandler()
        self.message_validator = MessageValidator()
    
    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            MessagingLogger.log_connection_error(
                "Unauthenticated connection attempt",
                context_data={'scope_keys': list(self.scope.keys())}
            )
            await self.close()
            return

        self.other_username = self.scope['url_route']['kwargs'].get('username')
        if not self.other_username:
            MessagingLogger.log_connection_error(
                "Missing username in URL route",
                context_data={'url_route': self.scope.get('url_route', {})}
            )
            await self.close()
            return

        try:
            self.other_user = await database_sync_to_async(User.objects.get)(username=self.other_username)
        except User.DoesNotExist:
            MessagingLogger.log_connection_error(
                f"User not found: {self.other_username}",
                context_data={'requested_username': self.other_username}
            )
            await self.close()
            return
        except Exception as e:
            MessagingLogger.log_connection_error(
                f"Database error while fetching user: {e}",
                context_data={'requested_username': self.other_username}
            )
            await self.close()
            return

        self.user = user
        
        # Deterministic room name for private chat between two users
        a, b = sorted([user.id, self.other_user.id])
        self.room_group_name = f'chat_{a}_{b}'
        
        # Add to chat room
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        
        # Add to personal user group for status updates
        self.user_group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        
        await self.accept()
        
        # Mark user as online using async-safe handler
        success = await self.message_handler.set_user_online_status(user, True)
        if not success:
            MessagingLogger.log_error(
                "Failed to set user online status",
                context_data={'user_id': user.id}
            )
        
        # Send online status to the other user
        await self.channel_layer.group_send(
            f'user_{self.other_user.id}',
            {
                'type': 'user_status',
                'user_id': user.id,
                'username': user.username,
                'is_online': True
            }
        )
        
        # Send other user's status to this user using async-safe handler
        other_status = await self.message_handler.get_user_status(self.other_user)
        status_message = {
            'type': 'user_status',
            'user_id': self.other_user.id,
            'username': self.other_user.username,
            'is_online': other_status['is_online'],
            'last_seen': other_status['last_seen']
        }
        
        # Use JSON serializer for safe transmission
        serialized_status = self.json_serializer.safe_serialize(status_message)
        await self.send(text_data=self.json_serializer.to_json_string(serialized_status))

    async def disconnect(self, close_code):
        try:
            # Mark user as offline using async-safe handler
            if hasattr(self, 'user'):
                success = await self.message_handler.set_user_online_status(self.user, False)
                if not success:
                    MessagingLogger.log_error(
                        "Failed to set user offline status",
                        context_data={'user_id': self.user.id, 'close_code': close_code}
                    )
                
                # Notify other user
                if hasattr(self, 'other_user'):
                    await self.channel_layer.group_send(
                        f'user_{self.other_user.id}',
                        {
                            'type': 'user_status',
                            'user_id': self.user.id,
                            'username': self.user.username,
                            'is_online': False
                        }
                    )
            
            # Clean up channel groups
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            if hasattr(self, 'user_group_name'):
                await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
                
        except Exception as e:
            MessagingLogger.log_connection_error(
                f"Error in disconnect: {e}",
                context_data={'close_code': close_code}
            )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            MessagingLogger.log_error("Received empty text_data")
            return
        
        # Validate and parse incoming data
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            MessagingLogger.log_json_error(
                e,
                data=text_data,
                context_data={'operation': 'parse_incoming_message'}
            )
            await self.send_error_response("Invalid JSON format")
            return
        
        # Validate connection data structure
        if not self.connection_validator.validate_message_data(data):
            MessagingLogger.log_error(
                "Invalid message data structure",
                context_data={'data_keys': list(data.keys()) if isinstance(data, dict) else 'not_dict'}
            )
            await self.send_error_response("Invalid message format")
            return
        
        # Additional message format validation for message type
        message_type = self.connection_validator.safe_get(data, 'type', 'message')
        if message_type == 'message':
            # Validate message content before processing
            message_content = self.connection_validator.safe_get(data, 'message', '')
            if not message_content.strip():
                await self.send_error_response("Message content cannot be empty")
                return
            
            # Validate message length
            if len(message_content) > 10000:
                await self.send_error_response("Message content too long")
                return
        
        # Handle different message types
        if message_type == 'typing':
            await self._handle_typing_indicator(data)
        elif message_type == 'read_receipt':
            await self._handle_read_receipt(data)
        elif message_type == 'message':
            await self._handle_message(data)
        elif message_type == 'ping':
            await self._handle_ping(data)
        else:
            MessagingLogger.log_error(
                f"Unknown message type: {message_type}",
                context_data={'message_type': message_type, 'data': data}
            )
            await self.send_error_response(f"Unknown message type: {message_type}")
    
    async def _handle_typing_indicator(self, data):
        """Handle typing indicator with validation"""
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': self.user.username,
                    'is_typing': self.connection_validator.safe_get(data, 'is_typing', False)
                }
            )
        except Exception as e:
            MessagingLogger.log_error(
                f"Error handling typing indicator: {e}",
                context_data={'user_id': self.user.id}
            )
    
    async def _handle_read_receipt(self, data):
        """Handle read receipt with async-safe operations"""
        message_id = self.connection_validator.safe_get(data, 'message_id')
        if not message_id:
            await self.send_error_response("Missing message_id for read receipt")
            return
        
        try:
            success = await self.message_handler.mark_message_read(message_id, self.user)
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'read_receipt',
                        'message_id': message_id,
                        'read_by': self.user.username
                    }
                )
            else:
                MessagingLogger.log_error(
                    f"Failed to mark message {message_id} as read",
                    context_data={'message_id': message_id, 'user_id': self.user.id}
                )
        except Exception as e:
            MessagingLogger.log_error(
                f"Error handling read receipt: {e}",
                context_data={'message_id': message_id, 'user_id': self.user.id}
            )
    
    async def _handle_message(self, data):
        """Handle regular message with async-safe operations, enhanced serialization, and retry mechanisms"""
        message_text = self.connection_validator.safe_get(data, 'message')
        retry_id = self.connection_validator.safe_get(data, 'retry_id')
        
        if not message_text:
            await self.send_error_response("Empty message content", retry_id)
            return

        # Validate message format before processing
        message_data = {
            'sender': self.user.username,
            'recipient': self.other_user.username,
            'content': message_text
        }
        
        if not self.message_validator.validate_message_format(message_data):
            await self.send_error_response("Invalid message format", retry_id)
            return

        try:
            # Use retry handler for message creation with retry mechanisms
            result = await self.retry_handler.retry_message_creation(
                sender=self.user,
                recipient=self.other_user,
                content=message_text,
                retry_id=retry_id
            )
            
            if not result:
                # If retry failed, queue the message for later processing
                queued = await self.retry_handler.queue_failed_message(
                    sender=self.user,
                    recipient=self.other_user,
                    content=message_text,
                    original_error="Message creation failed after retries",
                    retry_id=retry_id
                )
                
                if queued:
                    await self.send_error_response("Message queued for retry", retry_id)
                else:
                    await self.send_error_response("Failed to send message", retry_id)
                return
            
            # Use JSON serializer for safe transmission
            serialized_message = self.json_serializer.safe_serialize(result)
            
            # Retry WebSocket transmission with backoff
            operation_id = f"websocket_send_{result.get('id', 'unknown')}_{int(time.time())}"
            transmission_success = await self.retry_handler.retry_websocket_transmission(
                channel_layer=self.channel_layer,
                group_name=self.room_group_name,
                message_data=serialized_message,
                operation_id=operation_id
            )
            
            if not transmission_success:
                MessagingLogger.log_error(
                    f"WebSocket transmission failed after retries for message {result.get('id')}",
                    context_data={
                        'message_id': result.get('id'),
                        'operation_id': operation_id,
                        'retry_id': retry_id
                    }
                )
                # Message was created but transmission failed - this is logged for monitoring
                # The message still exists in the database and can be retrieved via other means
                    
        except Exception as e:
            MessagingLogger.log_error(
                f"Error handling message with retry mechanisms: {e}",
                context_data={
                    'sender_id': self.user.id,
                    'recipient_id': self.other_user.id,
                    'content_length': len(message_text),
                    'retry_id': retry_id
                }
            )
            await self.send_error_response("Failed to send message", retry_id)
    
    async def _handle_ping(self, data):
        """Handle ping for connection health check"""
        try:
            timestamp = self.connection_validator.safe_get(data, 'timestamp')
            response = {
                'type': 'pong',
                'timestamp': timestamp
            }
            serialized_response = self.json_serializer.safe_serialize(response)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error handling ping: {e}",
                context_data={'user_id': self.user.id}
            )
    
    async def send_error_response(self, error_message, retry_id=None):
        """Send error response with proper serialization"""
        try:
            error_data = {
                'type': 'error',
                'error': error_message,
                'timestamp': timezone.now().isoformat()
            }
            if retry_id:
                error_data['retry_id'] = retry_id
            
            serialized_error = self.json_serializer.safe_serialize(error_data)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_error))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error sending error response: {e}",
                context_data={'original_error': error_message, 'retry_id': retry_id}
            )
    
    async def validate_and_recover_message_ordering(self, messages: list) -> list:
        """
        Validate message ordering and recover from ordering issues during error recovery
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of messages with corrected ordering
        """
        try:
            if not messages or len(messages) <= 1:
                return messages
            
            # Validate current ordering
            if self.message_validator.validate_message_ordering(messages):
                return messages
            
            # Attempt to recover ordering by sorting by timestamp
            MessagingLogger.log_error(
                "Message ordering violation detected, attempting recovery",
                context_data={
                    'message_count': len(messages),
                    'user_id': self.user.id
                }
            )
            
            # Sort messages by created_at timestamp
            sorted_messages = []
            for message in messages:
                created_at = message.get('created_at')
                if created_at:
                    try:
                        from datetime import datetime
                        # Parse timestamp for sorting
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        sorted_messages.append((dt, message))
                    except ValueError:
                        # If timestamp parsing fails, append to end
                        sorted_messages.append((datetime.max, message))
                else:
                    # Messages without timestamps go to end
                    sorted_messages.append((datetime.max, message))
            
            # Sort by timestamp and extract messages
            sorted_messages.sort(key=lambda x: x[0])
            recovered_messages = [msg for _, msg in sorted_messages]
            
            # Validate recovered ordering
            if self.message_validator.validate_message_ordering(recovered_messages):
                MessagingLogger.log_debug(
                    "Message ordering successfully recovered",
                    context_data={
                        'original_count': len(messages),
                        'recovered_count': len(recovered_messages),
                        'user_id': self.user.id
                    }
                )
                return recovered_messages
            else:
                MessagingLogger.log_error(
                    "Failed to recover message ordering",
                    context_data={
                        'message_count': len(messages),
                        'user_id': self.user.id
                    }
                )
                return messages  # Return original if recovery fails
                
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in message ordering validation/recovery: {e}",
                context_data={
                    'message_count': len(messages) if messages else 0,
                    'user_id': self.user.id
                }
            )
            return messages  # Return original on error

    async def chat_message(self, event):
        """Send message to WebSocket with enhanced serialization and ordering preservation"""
        try:
            message = event['message']
            
            # Validate message format before transmission
            if not self.message_validator.validate_message_format(message):
                MessagingLogger.log_error(
                    "Invalid message format in chat_message handler",
                    context_data={'message': message, 'user_id': self.user.id}
                )
                return
            
            # Mark as delivered if recipient is receiving it
            if (self.connection_validator.safe_get(message, 'recipient') == self.user.username and 
                not self.connection_validator.safe_get(message, 'delivered_at')):
                
                message_id = self.connection_validator.safe_get(message, 'id')
                if message_id:
                    success = await self.message_handler.mark_message_delivered(message_id)
                    if success:
                        message['delivered_at'] = timezone.now().isoformat()
            
            # Preserve message ordering by adding sequence information
            message['sequence_id'] = int(time.time() * 1000000)  # Microsecond precision
            
            # Use JSON serializer for safe transmission
            serialized_message = self.json_serializer.safe_serialize(message)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
            
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in chat_message handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket with validation"""
        try:
            # Don't send typing indicator back to the person typing
            if self.connection_validator.safe_get(event, 'username') != self.user.username:
                response = {
                    'type': 'typing',
                    'username': self.connection_validator.safe_get(event, 'username'),
                    'is_typing': self.connection_validator.safe_get(event, 'is_typing', False)
                }
                serialized_response = self.json_serializer.safe_serialize(response)
                await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in typing_indicator handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def read_receipt(self, event):
        """Send read receipt to WebSocket with enhanced serialization"""
        try:
            response = {
                'type': 'read_receipt',
                'message_id': self.connection_validator.safe_get(event, 'message_id'),
                'read_by': self.connection_validator.safe_get(event, 'read_by')
            }
            serialized_response = self.json_serializer.safe_serialize(response)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in read_receipt handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def user_status(self, event):
        """Send user status update to WebSocket with enhanced serialization"""
        try:
            response = {
                'type': 'user_status',
                'user_id': self.connection_validator.safe_get(event, 'user_id'),
                'username': self.connection_validator.safe_get(event, 'username'),
                'is_online': self.connection_validator.safe_get(event, 'is_online', False)
            }
            serialized_response = self.json_serializer.safe_serialize(response)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in user_status handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )


class NotificationsConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_handler = AsyncSafeMessageHandler()
        self.json_serializer = JSONSerializer()
        self.connection_validator = ConnectionValidator()
    
    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            MessagingLogger.log_connection_error(
                "Unauthenticated notification connection attempt",
                context_data={'scope_keys': list(self.scope.keys())}
            )
            await self.close()
            return

        self.user = user
        self.user_group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        
        # Mark user as online using async-safe handler
        success = await self.message_handler.set_user_online_status(user, True)
        if not success:
            MessagingLogger.log_error(
                "Failed to set user online status in notifications",
                context_data={'user_id': user.id}
            )
        
        # Send initial unread count
        unread_count = await self.get_unread_notification_count(user)
        response = {
            'type': 'badge_update',
            'unread_count': unread_count
        }
        serialized_response = self.json_serializer.safe_serialize(response)
        await self.send(text_data=self.json_serializer.to_json_string(serialized_response))

    async def disconnect(self, close_code):
        try:
            # Mark user as offline using async-safe handler
            if hasattr(self, 'user'):
                success = await self.message_handler.set_user_online_status(self.user, False)
                if not success:
                    MessagingLogger.log_error(
                        "Failed to set user offline status in notifications",
                        context_data={'user_id': self.user.id, 'close_code': close_code}
                    )
            
            # Clean up channel group
            if hasattr(self, 'user_group_name'):
                await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        except Exception as e:
            MessagingLogger.log_connection_error(
                f"Error in notifications disconnect: {e}",
                context_data={'close_code': close_code}
            )

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages for notification actions with enhanced validation"""
        if text_data is None:
            MessagingLogger.log_error("Received empty text_data in notifications")
            return
        
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError as e:
            MessagingLogger.log_json_error(
                e,
                data=text_data,
                context_data={'operation': 'parse_notification_message'}
            )
            await self.send_error_response("Invalid JSON format")
            return
        
        # Validate message data structure
        if not self.connection_validator.validate_message_data(data):
            MessagingLogger.log_error(
                "Invalid notification message data structure",
                context_data={'data_keys': list(data.keys()) if isinstance(data, dict) else 'not_dict'}
            )
            await self.send_error_response("Invalid message format")
            return
        
        message_type = self.connection_validator.safe_get(data, 'type')
        
        try:
            if message_type == 'mark_read':
                await self._handle_mark_read(data)
            elif message_type == 'mark_all_read':
                await self._handle_mark_all_read(data)
            elif message_type == 'get_notifications':
                await self._handle_get_notifications(data)
            elif message_type == 'ping':
                await self._handle_notification_ping(data)
            else:
                MessagingLogger.log_error(
                    f"Unknown notification message type: {message_type}",
                    context_data={'message_type': message_type, 'user_id': self.user.id}
                )
                await self.send_error_response(f"Unknown message type: {message_type}")
                
        except Exception as e:
            MessagingLogger.log_error(
                f"Error processing notification request: {e}",
                context_data={'message_type': message_type, 'user_id': self.user.id}
            )
            await self.send_error_response(f"Error processing request: {str(e)}")
    
    async def _handle_mark_read(self, data):
        """Handle mark notification as read"""
        notification_id = self.connection_validator.safe_get(data, 'notification_id')
        if not notification_id:
            await self.send_error_response("Missing notification_id")
            return
        
        success = await self.mark_notification_read(notification_id)
        response = {
            'type': 'mark_read_response',
            'notification_id': notification_id,
            'success': success
        }
        serialized_response = self.json_serializer.safe_serialize(response)
        await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
    
    async def _handle_mark_all_read(self, data):
        """Handle mark all notifications as read"""
        notification_type = self.connection_validator.safe_get(data, 'notification_type')
        count = await self.mark_all_notifications_read(notification_type)
        response = {
            'type': 'mark_all_read_response',
            'marked_count': count
        }
        serialized_response = self.json_serializer.safe_serialize(response)
        await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
    
    async def _handle_get_notifications(self, data):
        """Handle get notifications request"""
        limit = self.connection_validator.safe_get(data, 'limit', 20)
        offset = self.connection_validator.safe_get(data, 'offset', 0)
        unread_only = self.connection_validator.safe_get(data, 'unread_only', False)
        
        notifications = await self.get_notifications(limit, offset, unread_only)
        response = {
            'type': 'notifications_list',
            'notifications': notifications,
            'limit': limit,
            'offset': offset
        }
        serialized_response = self.json_serializer.safe_serialize(response)
        await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
    
    async def _handle_notification_ping(self, data):
        """Handle ping for notifications connection"""
        timestamp = self.connection_validator.safe_get(data, 'timestamp')
        response = {
            'type': 'pong',
            'timestamp': timestamp
        }
        serialized_response = self.json_serializer.safe_serialize(response)
        await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
    
    async def send_error_response(self, error_message):
        """Send error response for notifications"""
        try:
            error_data = {
                'type': 'error',
                'message': error_message
            }
            serialized_error = self.json_serializer.safe_serialize(error_data)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_error))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error sending notification error response: {e}",
                context_data={'original_error': error_message}
            )

    async def notification_message(self, event):
        """Send notification to the connected client with enhanced serialization"""
        try:
            message = self.connection_validator.safe_get(event, 'message', {})
            serialized_message = self.json_serializer.safe_serialize(message)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in notification_message handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def badge_update(self, event):
        """Send badge count update to the connected client with enhanced serialization"""
        try:
            message = self.connection_validator.safe_get(event, 'message', {})
            serialized_message = self.json_serializer.safe_serialize(message)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in badge_update handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def notification(self, event):
        """Send notification payload to the connected client (legacy support) with enhanced serialization"""
        try:
            message = self.connection_validator.safe_get(event, 'message', {})
            serialized_message = self.json_serializer.safe_serialize(message)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in notification handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    @database_sync_to_async
    def get_unread_notification_count(self, user):
        """Get total unread notification count with error handling"""
        try:
            return Notification.objects.filter(recipient=user, is_read=False).count()
        except Exception as e:
            MessagingLogger.log_error(
                f"Error getting unread notification count: {e}",
                context_data={'user_id': user.id}
            )
            return 0

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a specific notification as read with error handling"""
        try:
            notification = Notification.objects.get(id=notification_id, recipient=self.user)
            notification.mark_as_read()
            MessagingLogger.log_debug(
                f"Notification {notification_id} marked as read",
                {'user_id': self.user.id}
            )
            return True
        except Notification.DoesNotExist:
            MessagingLogger.log_debug(
                f"Notification {notification_id} not found for user {self.user.id}",
                {'notification_id': notification_id, 'user_id': self.user.id}
            )
            return False
        except Exception as e:
            MessagingLogger.log_error(
                f"Error marking notification as read: {e}",
                context_data={'notification_id': notification_id, 'user_id': self.user.id}
            )
            return False

    @database_sync_to_async
    def mark_all_notifications_read(self, notification_type=None):
        """Mark all notifications as read for the user with error handling"""
        try:
            query = Notification.objects.filter(recipient=self.user, is_read=False)
            if notification_type:
                query = query.filter(notification_type=notification_type)
            
            count = 0
            for notification in query:
                notification.mark_as_read()
                count += 1
            
            MessagingLogger.log_debug(
                f"Marked {count} notifications as read",
                {'user_id': self.user.id, 'notification_type': notification_type}
            )
            return count
        except Exception as e:
            MessagingLogger.log_error(
                f"Error marking all notifications as read: {e}",
                context_data={'user_id': self.user.id, 'notification_type': notification_type}
            )
            return 0

    @database_sync_to_async
    def get_notifications(self, limit=20, offset=0, unread_only=False):
        """Get notifications for the user with enhanced serialization"""
        try:
            query = Notification.objects.filter(recipient=self.user)
            
            if unread_only:
                query = query.filter(is_read=False)
            
            notifications = query.select_related('sender').order_by('-created_at')[offset:offset+limit]
            
            result = []
            for notification in notifications:
                # Use JSON serializer for safe notification serialization
                serialized_notification = self.json_serializer.serialize_notification(notification)
                result.append(serialized_notification)
            
            return result
        except Exception as e:
            MessagingLogger.log_error(
                f"Error getting notifications: {e}",
                context_data={
                    'user_id': self.user.id,
                    'limit': limit,
                    'offset': offset,
                    'unread_only': unread_only
                }
            )
            return []

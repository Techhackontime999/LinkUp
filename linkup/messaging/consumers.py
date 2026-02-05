import json
import time
from datetime import datetime
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message, UserStatus, Notification
# Our comprehensive messaging system fixes
from .async_handlers import AsyncSafeMessageHandler
from .serializers import JSONSerializer
from .connection_validator import ConnectionValidator
from .logging_utils import MessagingLogger
from .async_error_handler import AsyncErrorHandler, log_websocket_error, log_async_context_error
from .retry_handler import MessageRetryHandler, MessageValidator, RetryConfig
# WhatsApp messaging features
from .message_status_manager import message_status_manager
from .typing_manager import typing_manager
from .presence_manager import presence_manager
from .connection_recovery_manager import connection_recovery_manager
from .message_sync_manager import message_sync_manager
from .read_receipt_manager import read_receipt_manager
from .message_retry_manager import MessageRetryManager
from .message_persistence_manager import message_persistence_manager
import logging
import uuid
import asyncio

User = get_user_model()
logger = logging.getLogger(__name__)

# Initialize retry managers (both systems)
retry_manager = MessageRetryManager()


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Our comprehensive messaging system components
        self.message_handler = AsyncSafeMessageHandler()
        self.json_serializer = JSONSerializer()
        self.connection_validator = ConnectionValidator()
        self.retry_handler = MessageRetryHandler()
        self.message_validator = MessageValidator()
    
    async def connect(self):
        """Enhanced connect method with comprehensive error handling"""
        try:
            user = self.scope.get('user')
            if user is None or not user.is_authenticated:
                await log_websocket_error(
                    Exception("Unauthenticated connection attempt"),
                    "connect",
                    context_data={'scope_keys': list(self.scope.keys())}
                )
                await self.close()
                return

            self.other_username = self.scope['url_route']['kwargs'].get('username')
            if not self.other_username:
                await log_websocket_error(
                    Exception("Missing username in URL route"),
                    "connect",
                    user,
                    context_data={'url_route': self.scope.get('url_route', {})}
                )
                await self.close()
                return

            try:
                self.other_user = await database_sync_to_async(User.objects.get)(username=self.other_username)
            except User.DoesNotExist:
                await log_websocket_error(
                    Exception(f"User not found: {self.other_username}"),
                    "connect",
                    user,
                    context_data={'requested_username': self.other_username}
                )
                await self.close()
                return
            except Exception as e:
                await log_async_context_error(
                    e,
                    "database_user_fetch",
                    user,
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
            
            # Handle user connection with presence manager (WhatsApp features)
            self.connection_id = await self.handle_user_connected()
            
            # Mark user as online using async-safe handler (our fixes)
            success = await self.message_handler.set_user_online_status(user, True)
            if not success:
                await log_websocket_error(
                    Exception("Failed to set user online status"),
                    "connect",
                    user,
                    context_data={'user_id': user.id}
                )
            
            # Register connection with recovery manager
            await self.register_connection_recovery()
            
            # Enable automatic read receipts for active chat windows
            self.auto_read_receipts = True
            
            # Check for missed messages and synchronize
            await self.synchronize_missed_messages()
            
            # Send other user's status to this user (integrated approach)
            other_presence = await self.get_user_presence(self.other_user)
            status_message = {
                'type': 'user_status',
                'user_id': self.other_user.id,
                'username': self.other_user.username,
                'is_online': other_presence['is_online'],
                'last_seen': other_presence['last_seen'],
                'last_seen_display': other_presence['last_seen_display']
            }
            
            # Use JSON serializer for safe transmission (our fixes)
            serialized_status = self.json_serializer.safe_serialize(status_message)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_status))
            
        except Exception as e:
            # Catch any unexpected errors in connect
            await log_async_context_error(
                e,
                "websocket_connect",
                getattr(self, 'user', None),
                context_data={'connection_stage': 'connect_method'}
            )
            await self.close()

    async def disconnect(self, close_code):
        """Enhanced disconnect handler with comprehensive cleanup and error handling"""
        disconnect_errors = []

        try:
            # Stop all typing indicators for this user
            await self.stop_all_typing()
        except Exception as e:
            disconnect_errors.append(f"Failed to stop typing indicators: {e}")
            logger.error(f"Error stopping typing indicators during disconnect: {e}")

        try:
            # Unregister from connection recovery manager
            await self.unregister_connection_recovery()
        except Exception as e:
            disconnect_errors.append(f"Failed to unregister connection recovery: {e}")
            logger.error(f"Error unregistering connection recovery during disconnect: {e}")

        try:
            # Handle user disconnection with presence manager
            await self.handle_user_disconnected()
        except Exception as e:
            disconnect_errors.append(f"Failed to handle user disconnection: {e}")
            logger.error(f"Error handling user disconnection: {e}")

        try:
            # Process any pending retry queue before disconnecting
            if hasattr(self, 'connection_id'):
                await retry_manager.process_retry_queue()
        except Exception as e:
            disconnect_errors.append(f"Failed to process retry queue: {e}")
            logger.error(f"Error processing retry queue during disconnect: {e}")

        try:
            # Mark user as offline using async-safe handler (our fixes)
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
        except Exception as e:
            disconnect_errors.append(f"Failed to update user status: {e}")
            logger.error(f"Error updating user status during disconnect: {e}")

        try:
            # Clean up channel layer groups
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            if hasattr(self, 'user_group_name'):
                await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        except Exception as e:
            disconnect_errors.append(f"Failed to clean up channel groups: {e}")
            logger.error(f"Error cleaning up channel groups during disconnect: {e}")

        # Log summary of disconnect process
        if disconnect_errors:
            logger.warning(f"Disconnect completed with {len(disconnect_errors)} errors for user {getattr(self, 'user', 'unknown')}")
        else:
            logger.info(f"Clean disconnect completed for user {getattr(self, 'user', 'unknown')}")

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
        validation_result = self.connection_validator.validate_message_data(data)
        if not validation_result.get('is_valid', False):
            MessagingLogger.log_error(
                "Invalid message data structure",
                context_data={'data_keys': list(data.keys()) if isinstance(data, dict) else 'not_dict'}
            )
            await self.send_error_response("Invalid message format")
            return

        message_type = data.get('type', 'message')

        try:
            if message_type == 'typing':
                # Handle typing indicator with enhanced debouncing
                is_typing = data.get('is_typing', False)
                await self.update_typing_status(is_typing)

            elif message_type == 'read_receipt':
                # Handle single read receipt with enhanced processing
                message_id = data.get('message_id')
                if message_id:
                    success = await read_receipt_manager.mark_message_as_read(
                        message_id=message_id,
                        reader_user_id=self.user.id
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'read_receipt_processed',
                        'message_id': message_id,
                        'success': success,
                        'timestamp': timezone.now().isoformat()
                    }))

            elif message_type == 'bulk_read_receipt':
                # Handle bulk read receipts
                message_ids = data.get('message_ids', [])
                if message_ids:
                    result = await read_receipt_manager.mark_multiple_messages_as_read(
                        message_ids=message_ids,
                        reader_user_id=self.user.id
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'bulk_read_receipt_processed',
                        'result': result
                    }))

            elif message_type == 'mark_chat_read':
                # Handle marking entire chat as read
                result = await read_receipt_manager.mark_visible_messages_as_read(
                    user_id=self.user.id,
                    chat_partner_id=self.other_user.id,
                    visible_message_ids=data.get('visible_message_ids')
                )
                await self.send(text_data=json.dumps({
                    'type': 'chat_marked_read',
                    'result': result
                }))

            elif message_type == 'message':
                await self._handle_message(data)

            elif message_type == 'ping':
                await self._handle_ping(data)

            elif message_type == 'force_reconnect':
                await self.force_reconnect()
                await self.send(text_data=json.dumps({
                    'type': 'reconnect_initiated',
                    'timestamp': timezone.now().isoformat()
                }))

            elif message_type == 'sync_request':
                await self.synchronize_missed_messages()
                await self.send(text_data=json.dumps({
                    'type': 'sync_completed',
                    'timestamp': timezone.now().isoformat()
                }))

            elif message_type == 'get_connection_status':
                await self._handle_get_connection_status(data)

            else:
                MessagingLogger.log_error(
                    f"Unknown message type: {message_type}",
                    context_data={'message_type': message_type, 'data': data}
                )
                await self.send_error_response(f"Unknown message type: {message_type}")

        except Exception as e:
            logger.error(f"Error in receive: {e}")
            # Use the new async error handler
            await log_async_context_error(
                e,
                "websocket_receive",
                self.user,
                context_data={
                    'message_type': message_type,
                    'data_keys': list(data.keys()) if isinstance(data, dict) else 'not_dict'
                }
            )
            await self.send_error_response(
                "Internal server error",
                error_type="internal_error",
                error_details=str(e) if logger.isEnabledFor(logging.DEBUG) else None
            )

    async def _handle_message(self, data):
        """Handle regular message with async-safe operations, enhanced serialization, and retry mechanisms"""
        message_text = self.connection_validator.safe_get(data, 'message')
        client_id = data.get('client_id') or f"client_{uuid.uuid4().hex[:12]}"
        retry_id = self.connection_validator.safe_get(data, 'retry_id')

        if not message_text or not message_text.strip():
            await self.send_error_response("Message content cannot be empty", client_id=client_id)
            return

        if len(message_text) > 5000:
            await self.send_error_response("Message too long (max 5000 characters)", client_id=client_id)
            return

        try:
            # Persist message with immediate status tracking
            msg = await message_persistence_manager.create_message_atomic(
                sender=self.user,
                recipient=self.other_user,
                content=message_text,
                client_id=client_id,
                retry_id=retry_id
            )

            if msg:
                # Create optimized payload for real-time delivery
                payload = await self.create_message_payload(msg, retry_id)

                # Attempt WebSocket broadcast with error handling
                broadcast_success = await self.safe_broadcast_message(payload)

                if broadcast_success:
                    # Update status to sent immediately after successful broadcasting
                    await message_persistence_manager.update_message_status_atomic(
                        msg.id, 'sent', self.user.id
                    )
                    # Create notification for the recipient
                    await self.create_message_notification(msg)
                else:
                    # Broadcasting failed, initiate retry mechanism
                    logger.warning(f"Message {msg.id} broadcast failed, initiating retry")
                    await retry_manager.retry_failed_message(msg.id, 'broadcast_failed')
                    await self.send_error_response(
                        "Message delivery failed, retrying automatically",
                        client_id=client_id,
                        retry_available=True,
                        message_id=msg.id
                    )
            else:
                await self.send_error_response("Failed to create message", client_id=client_id)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error_response(
                "Failed to send message",
                client_id=client_id,
                error_details=str(e) if logger.isEnabledFor(logging.DEBUG) else None
            )

    async def _handle_ping(self, data):
        """Handle ping for connection health check"""
        try:
            await self.update_heartbeat()
            connection_recovery_manager.update_heartbeat(self.connection_id)
            
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

    async def _handle_get_connection_status(self, data):
        """Handle get connection status request"""
        try:
            connection_id = getattr(self, 'connection_id', None)
            if connection_id:
                status = connection_recovery_manager.get_connection_status(connection_id)
                response = {
                    'type': 'connection_status',
                    'connection_id': connection_id,
                    'status': status,
                    'timestamp': timezone.now().isoformat()
                }
            else:
                response = {
                    'type': 'connection_status',
                    'error': 'No connection ID available',
                    'timestamp': timezone.now().isoformat()
                }
            
            serialized_response = self.json_serializer.safe_serialize(response)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error handling get connection status: {e}",
                context_data={'user_id': self.user.id}
            )

    async def send_error_response(self, error_message, retry_id=None, client_id=None, error_type=None,
                                error_details=None, retry_available=False, message_id=None):
        """Send enhanced error message to client with comprehensive error information"""
        try:
            error_data = {
                'type': 'error',
                'error': error_message,
                'timestamp': timezone.now().isoformat(),
                'error_id': f"err_{uuid.uuid4().hex[:8]}"
            }
            
            if retry_id:
                error_data['retry_id'] = retry_id
            if client_id:
                error_data['client_id'] = client_id
            if error_type:
                error_data['error_type'] = error_type
            if error_details:
                error_data['error_details'] = error_details
            if retry_available:
                error_data['retry_available'] = retry_available
            if message_id:
                error_data['message_id'] = message_id

            logger.error(f"WebSocket error for user {self.user.id}: {error_message} (ID: {error_data['error_id']})")
            
            serialized_error = self.json_serializer.safe_serialize(error_data)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_error))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error sending error response: {e}",
                context_data={'original_error': error_message, 'retry_id': retry_id}
            )

    async def safe_broadcast_message(self, payload):
        """Safely broadcast message with error handling and circuit breaker logic"""
        try:
            await asyncio.wait_for(
                self.channel_layer.group_send(self.room_group_name, {
                    'type': 'chat_message',
                    'message': payload,
                }),
                timeout=5.0
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Message broadcast timeout for room {self.room_group_name}")
            return False
        except Exception as e:
            logger.error(f"Message broadcast error for room {self.room_group_name}: {e}")
            return False

    async def chat_message(self, event):
        """Send message to WebSocket with enhanced status tracking, automatic read receipts, and error handling"""
        try:
            message = event['message']

            # Mark as delivered if recipient is receiving it
            if message['recipient'] == self.user.username and message.get('status') != 'delivered':
                delivery_success = await message_persistence_manager.update_message_status_atomic(
                    message['id'], 'delivered', self.user.id
                )
                if delivery_success:
                    message['status'] = 'delivered'
                    message['delivered_at'] = timezone.now().isoformat()

            # Send message to client with error handling
            try:
                serialized_message = self.json_serializer.safe_serialize(message)
                await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
            except Exception as e:
                logger.error(f"Failed to send message {message['id']} to client: {e}")
                await retry_manager.retry_failed_message(message['id'], 'client_send_failed')
                return

            # Auto-generate read receipt if this is for the recipient and chat is active
            if (message['recipient'] == self.user.username and
                message.get('type') == 'message' and
                hasattr(self, 'auto_read_receipts') and
                self.auto_read_receipts):

                try:
                    await asyncio.sleep(0.5)  # Small delay to simulate user viewing
                    await read_receipt_manager.mark_message_as_read(
                        message_id=message['id'],
                        reader_user_id=self.user.id
                    )
                except Exception as e:
                    logger.error(f"Failed to generate auto read receipt for message {message['id']}: {e}")

        except Exception as e:
            logger.error(f"Error in chat_message handler: {e}")
            await self.send_error_response(
                "Error processing incoming message",
                error_type="message_processing_error",
                error_details=str(e) if logger.isEnabledFor(logging.DEBUG) else None
            )

    async def message_status_update(self, event):
        """Send message status update to WebSocket"""
        try:
            serialized_message = self.json_serializer.safe_serialize(event['message'])
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
        except Exception as e:
            logger.error(f"Error in message_status_update handler: {e}")

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        try:
            # Don't send typing indicator back to the person typing
            if event['username'] != self.user.username:
                response = {
                    'type': 'typing',
                    'username': event['username'],
                    'is_typing': event['is_typing']
                }
                serialized_response = self.json_serializer.safe_serialize(response)
                await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in typing_indicator handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def multi_tab_sync(self, event):
        """Handle cross-tab synchronization events"""
        try:
            # Forward the sync event to the client so other tabs can update their UI
            sync_payload = {
                'type': 'multi_tab_sync',
                'sync_type': event.get('sync_type'),
                'data': event.get('data'),
                'timestamp': event.get('timestamp')
            }
            serialized_payload = self.json_serializer.safe_serialize(sync_payload)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_payload))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in multi_tab_sync handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
            )

    async def read_receipt_update(self, event):
        """Send enhanced read receipt update to WebSocket"""
        try:
            serialized_message = self.json_serializer.safe_serialize(event['message'])
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
        except Exception as e:
            logger.error(f"Error in read_receipt_update handler: {e}")

    async def user_status(self, event):
        """Send user status update to WebSocket"""
        try:
            response = {
                'type': 'user_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_online': event['is_online']
            }
            serialized_response = self.json_serializer.safe_serialize(response)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in user_status handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
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

    # Database operations with async decorators
    @database_sync_to_async
    def create_message_payload(self, msg, retry_id=None):
        """Create optimized message payload for real-time delivery"""
        return {
            'type': 'message',
            'id': msg.id,
            'sender': msg.sender.username,
            'recipient': msg.recipient.username,
            'content': msg.content,
            'status': msg.status,
            'client_id': msg.client_id,
            'created_at': msg.created_at.isoformat(),
            'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
            'delivered_at': msg.delivered_at.isoformat() if msg.delivered_at else None,
            'read_at': msg.read_at.isoformat() if msg.read_at else None,
            'is_read': msg.is_read,
            'retry_id': retry_id,
            'status_icon': msg.get_status_icon()
        }

    @database_sync_to_async
    def update_typing_status(self, is_typing):
        """Update typing status using the typing manager"""
        try:
            return typing_manager.update_typing_status(
                self.user,
                self.other_user, 
                is_typing
            )
        except Exception as e:
            logger.error(f"Failed to update typing status: {e}")
            return False

    @database_sync_to_async
    def stop_all_typing(self):
        """Stop all typing indicators for this user"""
        try:
            return typing_manager.stop_all_typing_for_user(self.user)
        except Exception as e:
            logger.error(f"Failed to stop typing for user: {e}")
            return 0

    @database_sync_to_async
    def handle_user_connected(self):
        """Handle user connection with presence manager"""
        try:
            # Safely extract headers from scope
            headers = {}
            scope_headers = self.scope.get('headers', [])
            
            if isinstance(scope_headers, (list, tuple)):
                for header_item in scope_headers:
                    try:
                        if isinstance(header_item, (list, tuple)) and len(header_item) >= 2:
                            key = header_item[0]
                            value = header_item[1]
                            
                            # Convert bytes to string if needed
                            if isinstance(key, bytes):
                                key = key.decode('utf-8', errors='ignore')
                            if isinstance(value, bytes):
                                value = value.decode('utf-8', errors='ignore')
                            
                            headers[str(key)] = str(value)
                    except Exception:
                        continue
            
            connection_info = {
                'user_agent': headers.get('user-agent', ''),
                'connected_at': timezone.now().isoformat()
            }
            return presence_manager.user_connected(self.user, connection_info)
        except Exception as e:
            logger.error(f"Failed to handle user connection: {e}")
            return f"conn_{self.user.id}_{uuid.uuid4().hex[:8]}"

    @database_sync_to_async
    def handle_user_disconnected(self):
        """Handle user disconnection with presence manager"""
        try:
            connection_id = getattr(self, 'connection_id', None)
            presence_manager.user_disconnected(self.user, connection_id)
        except Exception as e:
            logger.error(f"Failed to handle user disconnection: {e}")

    @database_sync_to_async
    def update_heartbeat(self):
        """Update user heartbeat"""
        try:
            connection_id = getattr(self, 'connection_id', None)
            return presence_manager.update_heartbeat(self.user, connection_id)
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")
            return False

    @database_sync_to_async
    def get_user_presence(self, user):
        """Get user presence information"""
        try:
            return presence_manager.get_user_presence(user)
        except Exception as e:
            logger.error(f"Failed to get user presence: {e}")
            return {
                'is_online': False,
                'last_seen': None,
                'last_seen_display': 'Unknown'
            }

    @database_sync_to_async
    def create_message_notification(self, message):
        """Create a notification for a new message"""
        try:
            from .notification_service import notify_new_message
            notify_new_message(
                sender=message.sender,
                recipient=message.recipient,
                message_obj=message
            )
        except Exception as e:
            logger.error(f"Error creating message notification: {e}")

    # Connection Recovery Integration Methods
    async def register_connection_recovery(self):
        """Register this connection with the recovery manager"""
        try:
            websocket_url = f"/ws/chat/{self.other_username}/"
            
            async def reconnect_callback():
                try:
                    return True
                except Exception as e:
                    logger.error(f"Reconnection callback error: {e}")
                    return False

            connection_recovery_manager.register_connection(
                connection_id=self.connection_id,
                user_id=self.user.id,
                websocket_url=websocket_url,
                reconnect_callback=reconnect_callback
            )

            connection_recovery_manager.add_status_callback(
                self.connection_id,
                self.handle_connection_status_update
            )

            logger.info(f"Registered connection recovery for {self.connection_id}")

        except Exception as e:
            logger.error(f"Error registering connection recovery: {e}")

    async def unregister_connection_recovery(self):
        """Unregister this connection from the recovery manager"""
        try:
            connection_recovery_manager.unregister_connection(self.connection_id)
            logger.info(f"Unregistered connection recovery for {self.connection_id}")
        except Exception as e:
            logger.error(f"Error unregistering connection recovery: {e}")

    async def handle_connection_status_update(self, status_update):
        """Handle connection status updates from recovery manager"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'connection_status',
                'connection_id': status_update['connection_id'],
                'state': status_update['state'],
                'retry_count': status_update['retry_count'],
                'next_retry_at': status_update.get('next_retry_at'),
                'error_message': status_update.get('error_message'),
                'timestamp': status_update['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error handling connection status update: {e}")

    async def synchronize_missed_messages(self):
        """Synchronize messages that were missed during disconnection"""
        try:
            user_presence = await self.get_user_presence(self.user)
            last_disconnect = user_presence.get('last_disconnect')

            if last_disconnect:
                from datetime import datetime
                if isinstance(last_disconnect, str):
                    last_disconnect_time = datetime.fromisoformat(last_disconnect.replace('Z', '+00:00'))
                else:
                    last_disconnect_time = last_disconnect

                sync_result = await message_sync_manager.synchronize_messages_on_reconnection(
                    user_id=self.user.id,
                    last_disconnect_time=last_disconnect_time,
                    connection_id=self.connection_id
                )

                if sync_result.get('messages'):
                    await self.send(text_data=json.dumps({
                        'type': 'message_sync',
                        'sync_result': sync_result
                    }))

                queue_result = await message_sync_manager.process_offline_message_queue(
                    user_id=self.user.id
                )

                if queue_result.get('processed_count', 0) > 0:
                    await self.send(text_data=json.dumps({
                        'type': 'queue_processed',
                        'result': queue_result
                    }))

                logger.info(f"Message synchronization completed for user {self.user.id}")

        except Exception as e:
            logger.error(f"Error synchronizing missed messages: {e}")

    async def force_reconnect(self):
        """Force immediate reconnection attempt"""
        try:
            connection_recovery_manager.force_reconnect(self.connection_id)
        except Exception as e:
            logger.error(f"Error forcing reconnect: {e}")


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
        validation_result = self.connection_validator.validate_message_data(data)
        if not validation_result.get('is_valid', False):
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



    async def user_status(self, event):
        """Send user status update to WebSocket"""
        try:
            response = {
                'type': 'user_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_online': event['is_online']
            }
            serialized_response = self.json_serializer.safe_serialize(response)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_response))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in user_status handler: {e}",
                context_data={"event": event, "user_id": self.user.id}
            )

    async def read_receipt_update(self, event):
        """Send read receipt update to WebSocket"""
        try:
            serialized_message = self.json_serializer.safe_serialize(event["message"])
            await self.send(text_data=self.json_serializer.to_json_string(serialized_message))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in read_receipt_update handler: {e}",
                context_data={"event": event, "user_id": self.user.id}
            )

    async def multi_tab_sync(self, event):
        """Handle cross-tab synchronization events"""
        try:
            # Forward the sync event to the client so other tabs can update their UI
            sync_payload = {
                'type': 'multi_tab_sync',
                'sync_type': event.get('sync_type'),
                'data': event.get('data'),
                'timestamp': event.get('timestamp')
            }
            serialized_payload = self.json_serializer.safe_serialize(sync_payload)
            await self.send(text_data=self.json_serializer.to_json_string(serialized_payload))
        except Exception as e:
            MessagingLogger.log_error(
                f"Error in multi_tab_sync handler: {e}",
                context_data={'event': event, 'user_id': self.user.id}
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

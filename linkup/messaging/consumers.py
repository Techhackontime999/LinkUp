import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message, UserStatus, Notification
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

# Initialize retry manager
retry_manager = MessageRetryManager()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.other_username = self.scope['url_route']['kwargs'].get('username')
        if not self.other_username:
            await self.close()
            return

        try:
            self.other_user = await database_sync_to_async(User.objects.get)(username=self.other_username)
        except User.DoesNotExist:
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
        
        # Handle user connection with presence manager
        self.connection_id = await self.handle_user_connected()
        
        # Register connection with recovery manager
        await self.register_connection_recovery()
        
        # Enable automatic read receipts for active chat windows
        self.auto_read_receipts = True
        
        # Check for missed messages and synchronize
        await self.synchronize_missed_messages()
        
        # Send other user's status to this user
        other_presence = await self.get_user_presence(self.other_user)
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': self.other_user.id,
            'username': self.other_user.username,
            'is_online': other_presence['is_online'],
            'last_seen': other_presence['last_seen'],
            'last_seen_display': other_presence['last_seen_display']
        }))

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
        
        # Store disconnect errors for debugging if needed
        if disconnect_errors and hasattr(self, 'user'):
            try:
                # Could store in a disconnect error log table if needed
                pass
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'typing':
                # Handle typing indicator with enhanced debouncing
                is_typing = data.get('is_typing', False)
                
                # Update typing status in database
                await self.update_typing_status(is_typing)
                
                # Note: Broadcasting is handled by typing_manager
                # No need to manually broadcast here
            
            elif message_type == 'read_receipt':
                # Handle single read receipt with enhanced processing
                message_id = data.get('message_id')
                if message_id:
                    success = await read_receipt_manager.mark_message_as_read(
                        message_id=message_id,
                        reader_user_id=self.user.id
                    )
                    
                    # Send confirmation back to client
                    await self.send(text_data=json.dumps({
                        'type': 'read_receipt_processed',
                        'message_id': message_id,
                        'success': success,
                        'timestamp': timezone.now().isoformat()
                    }))
            
            elif message_type == 'bulk_read_receipt':
                # Handle bulk read receipts (when user views multiple messages)
                message_ids = data.get('message_ids', [])
                if message_ids:
                    result = await read_receipt_manager.mark_multiple_messages_as_read(
                        message_ids=message_ids,
                        reader_user_id=self.user.id
                    )
                    
                    # Send bulk processing result
                    await self.send(text_data=json.dumps({
                        'type': 'bulk_read_receipt_processed',
                        'result': result
                    }))
            
            elif message_type == 'mark_chat_read':
                # Handle marking entire chat as read (when user opens/views chat)
                result = await read_receipt_manager.mark_visible_messages_as_read(
                    user_id=self.user.id,
                    chat_partner_id=self.other_user.id,
                    visible_message_ids=data.get('visible_message_ids')
                )
                
                # Send chat read result
                await self.send(text_data=json.dumps({
                    'type': 'chat_marked_read',
                    'result': result
                }))
            
            elif message_type == 'message':
                # Handle regular message with enhanced status tracking and error handling
                message_text = data.get('message')
                client_id = data.get('client_id') or f"client_{uuid.uuid4().hex[:12]}"
                retry_id = data.get('retry_id')  # For message retry functionality
                
                if not message_text:
                    await self.send_error("Message content is required", client_id=client_id)
                    return

                # Validate message content
                if len(message_text.strip()) == 0:
                    await self.send_error("Message cannot be empty", client_id=client_id)
                    return
                
                if len(message_text) > 5000:  # Reasonable message length limit
                    await self.send_error("Message too long (max 5000 characters)", client_id=client_id)
                    return

                # Persist message with immediate status tracking and comprehensive error handling
                try:
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
                            
                            # Send error to client with retry option
                            await self.send_error(
                                "Message delivery failed, retrying automatically", 
                                client_id=client_id,
                                retry_available=True,
                                message_id=msg.id
                            )
                    else:
                        await self.send_error("Failed to create message", client_id=client_id)
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.send_error(
                        "Failed to send message", 
                        client_id=client_id,
                        error_details=str(e) if logger.isEnabledFor(logging.DEBUG) else None
                    )
            
            elif message_type == 'ping':
                # Handle ping for connection health check and heartbeat
                await self.update_heartbeat()
                
                # Update connection recovery manager heartbeat
                connection_recovery_manager.update_heartbeat(self.connection_id)
                
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
            elif message_type == 'force_reconnect':
                # Handle manual reconnection request
                await self.force_reconnect()
                await self.send(text_data=json.dumps({
                    'type': 'reconnect_initiated',
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'get_connection_status':
                # Handle connection status request
                status = connection_recovery_manager.get_connection_status(self.connection_id)
                await self.send(text_data=json.dumps({
                    'type': 'connection_status',
                    'status': status,
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'sync_request':
                # Handle manual sync request
                await self.synchronize_missed_messages()
                await self.send(text_data=json.dumps({
                    'type': 'sync_completed',
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'set_auto_read_receipts':
                # Handle enabling/disabling automatic read receipts
                enabled = data.get('enabled', True)
                self.auto_read_receipts = enabled
                await self.send(text_data=json.dumps({
                    'type': 'auto_read_receipts_updated',
                    'enabled': enabled,
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'get_read_receipt_stats':
                # Handle read receipt statistics request
                stats = await read_receipt_manager.get_read_receipt_statistics(
                    user_id=self.user.id
                )
                await self.send(text_data=json.dumps({
                    'type': 'read_receipt_stats',
                    'stats': stats
                }))
            
            elif message_type == 'retry_message':
                # Handle manual message retry request
                message_id = data.get('message_id')
                if message_id:
                    success = await retry_manager.retry_failed_message(message_id, 'manual_retry')
                    await self.send(text_data=json.dumps({
                        'type': 'retry_result',
                        'message_id': message_id,
                        'success': success,
                        'timestamp': timezone.now().isoformat()
                    }))
                else:
                    await self.send_error("Message ID required for retry")
            
            elif message_type == 'get_retry_stats':
                # Handle retry statistics request
                stats = await retry_manager.get_retry_statistics()
                await self.send(text_data=json.dumps({
                    'type': 'retry_stats',
                    'stats': stats
                }))
            
            elif message_type == 'force_retry_failed':
                # Handle force retry of all failed messages for this user
                retry_count = await retry_manager.force_retry_failed_messages(self.user.id)
                await self.send(text_data=json.dumps({
                    'type': 'force_retry_result',
                    'retry_count': retry_count,
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'get_error_log':
                # Handle error log request for debugging
                error_log = await self.get_user_error_log()
                await self.send(text_data=json.dumps({
                    'type': 'error_log',
                    'errors': error_log
                }))
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format", error_type="json_decode_error")
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send_error(
                "Internal server error", 
                error_type="internal_error",
                error_details=str(e) if logger.isEnabledFor(logging.DEBUG) else None
            )

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
                else:
                    logger.warning(f"Failed to mark message {message['id']} as delivered")
            
            # Send message to client with error handling
            try:
                await self.send(text_data=json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message {message['id']} to client: {e}")
                # Attempt retry via retry manager
                await retry_manager.retry_failed_message(message['id'], 'client_send_failed')
                return
            
            # Auto-generate read receipt if this is for the recipient and chat is active
            # (This simulates the user viewing the message in an active chat window)
            if (message['recipient'] == self.user.username and 
                message.get('type') == 'message' and 
                hasattr(self, 'auto_read_receipts') and 
                self.auto_read_receipts):
                
                try:
                    # Small delay to simulate user viewing the message
                    await asyncio.sleep(0.5)
                    
                    # Generate automatic read receipt
                    await read_receipt_manager.mark_message_as_read(
                        message_id=message['id'],
                        reader_user_id=self.user.id
                    )
                except Exception as e:
                    logger.error(f"Failed to generate auto read receipt for message {message['id']}: {e}")
                    # Don't fail the entire message delivery for read receipt errors
                    
        except Exception as e:
            logger.error(f"Error in chat_message handler: {e}")
            # Send error notification to client
            await self.send_error(
                "Error processing incoming message",
                error_type="message_processing_error",
                error_details=str(e) if logger.isEnabledFor(logging.DEBUG) else None
            )

    async def message_status_update(self, event):
        """Send message status update to WebSocket"""
        await self.send(text_data=json.dumps(event['message']))

    async def send_error(self, error_message, retry_id=None, client_id=None, error_type=None, 
                        error_details=None, retry_available=False, message_id=None):
        """Send enhanced error message to client with comprehensive error information"""
        error_payload = {
            'type': 'error',
            'error': error_message,
            'timestamp': timezone.now().isoformat(),
            'error_id': f"err_{uuid.uuid4().hex[:8]}"  # Unique error ID for tracking
        }
        
        # Add optional fields
        if retry_id:
            error_payload['retry_id'] = retry_id
        if client_id:
            error_payload['client_id'] = client_id
        if error_type:
            error_payload['error_type'] = error_type
        if error_details:
            error_payload['error_details'] = error_details
        if retry_available:
            error_payload['retry_available'] = retry_available
        if message_id:
            error_payload['message_id'] = message_id
        
        # Log error for monitoring
        logger.error(f"WebSocket error for user {self.user.id}: {error_message} (ID: {error_payload['error_id']})")
        
        await self.send(text_data=json.dumps(error_payload))
    
    async def safe_broadcast_message(self, payload):
        """Safely broadcast message with error handling and circuit breaker logic"""
        try:
            # Check if we should use circuit breaker logic
            endpoint_key = f"{self.user.id}_{self.other_user.id}"
            
            # Attempt broadcast with timeout
            await asyncio.wait_for(
                self.channel_layer.group_send(self.room_group_name, {
                    'type': 'chat_message',
                    'message': payload,
                }),
                timeout=5.0  # 5 second timeout for broadcast
            )
            
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Message broadcast timeout for room {self.room_group_name}")
            return False
        except Exception as e:
            logger.error(f"Message broadcast error for room {self.room_group_name}: {e}")
            return False
    
    @database_sync_to_async
    def get_user_error_log(self, limit=50):
        """Get recent error log for the user (for debugging)"""
        try:
            # Get recent failed messages for this user
            failed_messages = Message.objects.filter(
                sender=self.user,
                status='failed'
            ).order_by('-created_at')[:limit]
            
            error_log = []
            for msg in failed_messages:
                error_log.append({
                    'message_id': msg.id,
                    'content_preview': msg.content[:50] + '...' if len(msg.content) > 50 else msg.content,
                    'recipient': msg.recipient.username,
                    'error': msg.last_error,
                    'retry_count': msg.retry_count,
                    'created_at': msg.created_at.isoformat(),
                    'failed_at': msg.updated_at.isoformat()
                })
            
            return error_log
            
        except Exception as e:
            logger.error(f"Error getting user error log: {e}")
            return []

    @database_sync_to_async
    def create_message_with_status(self, message_text, client_id, retry_id):
        """Create message with enhanced status tracking"""
        try:
            # Check for duplicate client_id to prevent double-sending
            existing_message = Message.objects.filter(
                sender=self.user,
                client_id=client_id
            ).first()
            
            if existing_message:
                logger.warning(f"Duplicate message with client_id {client_id}")
                return existing_message
            
            # Create new message with pending status
            msg = Message.objects.create(
                sender=self.user,
                recipient=self.other_user,
                content=message_text,
                client_id=client_id,
                status='pending'
            )
            
            logger.info(f"Created message {msg.id} with client_id {client_id}")
            return msg
            
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            return None

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
    def update_message_status(self, message_id, new_status):
        """Update message status using the status manager"""
        try:
            message = Message.objects.get(id=message_id)
            return message_status_manager.update_message_status(message, new_status)
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found for status update")
            return False
        except Exception as e:
            logger.error(f"Failed to update message {message_id} status: {e}")
            return False

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
    def get_typing_users(self):
        """Get users currently typing in this chat"""
        try:
            return typing_manager.get_typing_users_for_chat(self.user, self.other_user)
        except Exception as e:
            logger.error(f"Failed to get typing users: {e}")
            return []

    @database_sync_to_async
    def handle_user_connected(self):
        """Handle user connection with presence manager"""
        try:
            connection_info = {
                'user_agent': self.scope.get('headers', {}).get('user-agent', ''),
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

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send typing indicator back to the person typing
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket (legacy support)"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'read_by': event['read_by']
        }))
    
    async def read_receipt_update(self, event):
        """Send enhanced read receipt update to WebSocket"""
        await self.send(text_data=json.dumps(event['message']))
    
    async def bulk_read_receipts(self, event):
        """Send bulk read receipts update to WebSocket"""
        await self.send(text_data=json.dumps(event['message']))

    async def user_status(self, event):
        """Send user status update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online']
        }))

    @database_sync_to_async
    def set_user_online(self, user, is_online):
        """Set user online/offline status"""
        status, created = UserStatus.objects.get_or_create(user=user)
        status.is_online = is_online
        status.save()

    @database_sync_to_async
    def get_user_status(self, user):
        """Get user online status"""
        try:
            status = UserStatus.objects.get(user=user)
            return {
                'is_online': status.is_online,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None
            }
        except UserStatus.DoesNotExist:
            return {'is_online': False, 'last_seen': None}

    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark a message as read using the enhanced status system"""
        try:
            message = Message.objects.get(id=message_id, recipient=self.user)
            return message_status_manager.update_message_status(message, 'read')
        except Message.DoesNotExist:
            logger.warning(f"Message {message_id} not found or not for user {self.user.username}")
            return False
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as read: {e}")
            return False

    @database_sync_to_async
    def mark_message_delivered(self, message_id):
        """Mark a message as delivered using the enhanced status system"""
        try:
            message = Message.objects.get(id=message_id)
            return message_status_manager.update_message_status(message, 'delivered')
        except Message.DoesNotExist:
            logger.warning(f"Message {message_id} not found for delivery update")
            return False
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as delivered: {e}")
            return False

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
            print(f"Error creating message notification: {e}")

    # Connection Recovery Integration Methods
    
    async def register_connection_recovery(self):
        """Register this connection with the recovery manager"""
        try:
            websocket_url = f"/ws/chat/{self.other_username}/"
            
            # Create reconnection callback
            async def reconnect_callback():
                try:
                    # This would be implemented by the frontend JavaScript
                    # For now, we'll return True to indicate success
                    return True
                except Exception as e:
                    logger.error(f"Reconnection callback error: {e}")
                    return False
            
            # Register with recovery manager
            connection_recovery_manager.register_connection(
                connection_id=self.connection_id,
                user_id=self.user.id,
                websocket_url=websocket_url,
                reconnect_callback=reconnect_callback
            )
            
            # Add status callback for UI updates
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
            # Send status update to client
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
            # Get last disconnect time from presence manager
            user_presence = await self.get_user_presence(self.user)
            last_disconnect = user_presence.get('last_disconnect')
            
            if last_disconnect:
                # Parse the disconnect time
                from datetime import datetime
                if isinstance(last_disconnect, str):
                    last_disconnect_time = datetime.fromisoformat(last_disconnect.replace('Z', '+00:00'))
                else:
                    last_disconnect_time = last_disconnect
                
                # Synchronize messages
                sync_result = await message_sync_manager.synchronize_messages_on_reconnection(
                    user_id=self.user.id,
                    last_disconnect_time=last_disconnect_time,
                    connection_id=self.connection_id
                )
                
                # Send sync result to client
                if sync_result.get('messages'):
                    await self.send(text_data=json.dumps({
                        'type': 'message_sync',
                        'sync_result': sync_result
                    }))
                
                # Process offline message queue
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
    
    async def handle_connection_lost(self, error_message=None):
        """Handle connection loss and initiate recovery"""
        try:
            connection_recovery_manager.handle_connection_lost(
                self.connection_id,
                error_message
            )
        except Exception as e:
            logger.error(f"Error handling connection loss: {e}")
    
    async def force_reconnect(self):
        """Force immediate reconnection attempt"""
        try:
            connection_recovery_manager.force_reconnect(self.connection_id)
        except Exception as e:
            logger.error(f"Error forcing reconnect: {e}")


class NotificationsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.user_group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        
        # Mark user as online
        await self.set_user_online(user, True)
        
        # Send initial unread count
        unread_count = await self.get_unread_notification_count(user)
        await self.send(text_data=json.dumps({
            'type': 'badge_update',
            'unread_count': unread_count
        }))

    async def disconnect(self, close_code):
        try:
            # Mark user as offline
            await self.set_user_online(self.user, False)
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        except Exception:
            pass

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages for notification actions"""
        if text_data is None:
            return
        
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                # Mark specific notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    success = await self.mark_notification_read(notification_id)
                    await self.send(text_data=json.dumps({
                        'type': 'mark_read_response',
                        'notification_id': notification_id,
                        'success': success
                    }))
            
            elif message_type == 'mark_all_read':
                # Mark all notifications as read
                notification_type = data.get('notification_type')  # Optional filter
                count = await self.mark_all_notifications_read(notification_type)
                await self.send(text_data=json.dumps({
                    'type': 'mark_all_read_response',
                    'marked_count': count
                }))
            
            elif message_type == 'get_notifications':
                # Get notifications with pagination
                limit = data.get('limit', 20)
                offset = data.get('offset', 0)
                unread_only = data.get('unread_only', False)
                notifications = await self.get_notifications(limit, offset, unread_only)
                await self.send(text_data=json.dumps({
                    'type': 'notifications_list',
                    'notifications': notifications,
                    'limit': limit,
                    'offset': offset
                }))
            
            elif message_type == 'ping':
                # Health check
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error processing request: {str(e)}'
            }))

    async def notification_message(self, event):
        """Send notification to the connected client"""
        await self.send(text_data=json.dumps(event['message']))

    async def badge_update(self, event):
        """Send badge count update to the connected client"""
        await self.send(text_data=json.dumps(event['message']))

    async def notification(self, event):
        """Send notification payload to the connected client (legacy support)"""
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def set_user_online(self, user, is_online):
        """Set user online/offline status"""
        status, created = UserStatus.objects.get_or_create(user=user)
        status.is_online = is_online
        status.save()

    @database_sync_to_async
    def get_unread_notification_count(self, user):
        """Get total unread notification count"""
        try:
            return Notification.objects.filter(recipient=user, is_read=False).count()
        except Exception:
            return 0

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a specific notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, recipient=self.user)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
        except Exception:
            return False

    @database_sync_to_async
    def mark_all_notifications_read(self, notification_type=None):
        """Mark all notifications as read for the user"""
        try:
            query = Notification.objects.filter(recipient=self.user, is_read=False)
            if notification_type:
                query = query.filter(notification_type=notification_type)
            
            count = 0
            for notification in query:
                notification.mark_as_read()
                count += 1
            
            return count
        except Exception:
            return 0

    @database_sync_to_async
    def get_notifications(self, limit=20, offset=0, unread_only=False):
        """Get notifications for the user"""
        try:
            query = Notification.objects.filter(recipient=self.user)
            
            if unread_only:
                query = query.filter(is_read=False)
            
            notifications = query.select_related('sender').order_by('-created_at')[offset:offset+limit]
            
            result = []
            for notification in notifications:
                result.append({
                    'id': notification.id,
                    'notification_type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'sender': notification.sender.username if notification.sender else None,
                    'sender_avatar': notification.sender.profile.avatar.url if notification.sender and hasattr(notification.sender, 'profile') and notification.sender.profile.avatar else None,
                    'is_read': notification.is_read,
                    'read_at': notification.read_at.isoformat() if notification.read_at else None,
                    'created_at': notification.created_at.isoformat(),
                    'action_url': notification.action_url,
                    'is_grouped': notification.is_grouped,
                    'group_count': notification.group_count,
                })
            
            return result
        except Exception:
            return []

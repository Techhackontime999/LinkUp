import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message, UserStatus, Notification

User = get_user_model()


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
        
        # Mark user as online
        await self.set_user_online(user, True)
        
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
        
        # Send other user's status to this user
        other_status = await self.get_user_status(self.other_user)
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': self.other_user.id,
            'username': self.other_user.username,
            'is_online': other_status['is_online'],
            'last_seen': other_status['last_seen']
        }))

    async def disconnect(self, close_code):
        try:
            # Mark user as offline
            await self.set_user_online(self.user, False)
            
            # Notify other user
            await self.channel_layer.group_send(
                f'user_{self.other_user.id}',
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_online': False
                }
            )
            
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        except Exception as e:
            print(f"Error in disconnect: {e}")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'typing':
            # Handle typing indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': self.user.username,
                    'is_typing': data.get('is_typing', False)
                }
            )
        
        elif message_type == 'read_receipt':
            # Handle read receipt
            message_id = data.get('message_id')
            if message_id:
                await self.mark_message_read(message_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'read_receipt',
                        'message_id': message_id,
                        'read_by': self.user.username
                    }
                )
        
        elif message_type == 'message':
            # Handle regular message
            message_text = data.get('message')
            retry_id = data.get('retry_id')  # For message retry functionality
            
            if not message_text:
                return

            # Persist message
            try:
                msg = await database_sync_to_async(Message.objects.create)(
                    sender=self.user, 
                    recipient=self.other_user, 
                    content=message_text
                )

                payload = {
                    'type': 'message',
                    'id': msg.id,
                    'sender': self.user.username,
                    'recipient': self.other_user.username,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'is_read': msg.is_read,
                    'read_at': msg.read_at.isoformat() if msg.read_at else None,
                    'delivered_at': msg.delivered_at.isoformat() if msg.delivered_at else None,
                    'retry_id': retry_id  # Include retry_id if this was a retry
                }

                # Broadcast to room
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'chat_message',
                    'message': payload,
                })

                # Create notification for the recipient
                await self.create_message_notification(msg)
                    
            except Exception as e:
                # Send error response for failed message
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': 'Failed to send message',
                    'retry_id': retry_id
                }))
        
        elif message_type == 'ping':
            # Handle ping for connection health check
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': data.get('timestamp')
            }))

    async def chat_message(self, event):
        """Send message to WebSocket"""
        message = event['message']
        
        # Mark as delivered if recipient is receiving it
        if message['recipient'] == self.user.username and not message.get('delivered_at'):
            await self.mark_message_delivered(message['id'])
            message['delivered_at'] = timezone.now().isoformat()
        
        await self.send(text_data=json.dumps(message))

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
        """Send read receipt to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'read_by': event['read_by']
        }))

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
        """Mark a message as read"""
        try:
            message = Message.objects.get(id=message_id, recipient=self.user)
            message.mark_as_read()
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def mark_message_delivered(self, message_id):
        """Mark a message as delivered"""
        try:
            message = Message.objects.get(id=message_id)
            message.mark_as_delivered()
        except Message.DoesNotExist:
            pass

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

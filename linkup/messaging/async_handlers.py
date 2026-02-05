"""
Async-safe database operation handlers for messaging system
"""
from typing import List, Optional, Dict, Any
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import Message, UserStatus, Notification
from .logging_utils import MessagingLogger

User = get_user_model()


class AsyncSafeMessageHandler:
    """Handler for async-safe database operations in messaging system"""
    
    @database_sync_to_async
    def create_message(self, sender: User, recipient: User, content: str) -> Optional[Message]:
        """
        Create a message with proper async context handling
        
        Args:
            sender: User sending the message
            recipient: User receiving the message  
            content: Message content
            
        Returns:
            Created Message instance or None if creation failed
        """
        try:
            with transaction.atomic():
                message = Message.objects.create(
                    sender=sender,
                    recipient=recipient,
                    content=content
                )
                MessagingLogger.log_debug(
                    f"Message created successfully: {message.id}",
                    {'sender_id': sender.id, 'recipient_id': recipient.id}
                )
                return message
                
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e, 
                context_data={
                    'operation': 'create_message',
                    'sender_id': sender.id,
                    'recipient_id': recipient.id,
                    'content_length': len(content)
                },
                user=sender
            )
            return None
    
    @database_sync_to_async
    def get_messages(self, sender: User, recipient: User, limit: int = 50) -> List[Message]:
        """
        Get messages between two users with proper async context handling
        
        Args:
            sender: First user in conversation
            recipient: Second user in conversation
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of Message instances
        """
        try:
            from django.db.models import Q
            
            messages = Message.objects.filter(
                (Q(sender=sender) & Q(recipient=recipient)) |
                (Q(sender=recipient) & Q(recipient=sender))
            ).select_related('sender', 'recipient').order_by('-created_at')[:limit]
            
            return list(messages)
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'get_messages',
                    'sender_id': sender.id,
                    'recipient_id': recipient.id,
                    'limit': limit
                },
                user=sender
            )
            return []
    
    @database_sync_to_async
    def mark_message_read(self, message_id: int, user: User) -> bool:
        """
        Mark a message as read with proper async context handling
        
        Args:
            message_id: ID of message to mark as read
            user: User marking the message as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message = Message.objects.get(id=message_id, recipient=user)
            message.mark_as_read()
            MessagingLogger.log_debug(
                f"Message {message_id} marked as read",
                {'user_id': user.id}
            )
            return True
            
        except Message.DoesNotExist:
            MessagingLogger.log_debug(
                f"Message {message_id} not found for user {user.id}",
                {'message_id': message_id, 'user_id': user.id}
            )
            return False
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'mark_message_read',
                    'message_id': message_id,
                    'user_id': user.id
                },
                user=user
            )
            return False
    
    @database_sync_to_async
    def mark_message_delivered(self, message_id: int) -> bool:
        """
        Mark a message as delivered with proper async context handling
        
        Args:
            message_id: ID of message to mark as delivered
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message = Message.objects.get(id=message_id)
            message.mark_as_delivered()
            MessagingLogger.log_debug(
                f"Message {message_id} marked as delivered"
            )
            return True
            
        except Message.DoesNotExist:
            MessagingLogger.log_debug(
                f"Message {message_id} not found for delivery marking",
                {'message_id': message_id}
            )
            return False
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'mark_message_delivered',
                    'message_id': message_id
                }
            )
            return False
    
    @database_sync_to_async
    def set_user_online_status(self, user: User, is_online: bool) -> bool:
        """
        Set user online/offline status with proper async context handling
        
        Args:
            user: User to update status for
            is_online: Online status to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            status, created = UserStatus.objects.get_or_create(user=user)
            status.is_online = is_online
            status.save()
            
            MessagingLogger.log_debug(
                f"User {user.id} status set to {'online' if is_online else 'offline'}",
                {'user_id': user.id, 'is_online': is_online}
            )
            return True
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'set_user_online_status',
                    'user_id': user.id,
                    'is_online': is_online
                },
                user=user
            )
            return False
    
    @database_sync_to_async
    def get_user_status(self, user: User) -> Dict[str, Any]:
        """
        Get user online status with proper async context handling
        
        Args:
            user: User to get status for
            
        Returns:
            Dictionary with user status information
        """
        try:
            status = UserStatus.objects.get(user=user)
            return {
                'is_online': status.is_online,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None
            }
            
        except UserStatus.DoesNotExist:
            return {'is_online': False, 'last_seen': None}
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'get_user_status',
                    'user_id': user.id
                },
                user=user
            )
            return {'is_online': False, 'last_seen': None}
    
    @database_sync_to_async
    def create_notification(self, recipient: User, notification_type: str, title: str, 
                          message: str, sender: Optional[User] = None, 
                          priority: str = 'normal', action_url: Optional[str] = None) -> Optional[Notification]:
        """
        Create a notification with proper async context handling
        
        Args:
            recipient: User to receive notification
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            sender: User sending notification (optional)
            priority: Notification priority
            action_url: URL for notification action (optional)
            
        Returns:
            Created Notification instance or None if creation failed
        """
        try:
            notification = Notification.create_notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                sender=sender,
                priority=priority,
                action_url=action_url
            )
            
            MessagingLogger.log_debug(
                f"Notification created: {notification.id}",
                {
                    'recipient_id': recipient.id,
                    'notification_type': notification_type,
                    'sender_id': sender.id if sender else None
                }
            )
            return notification
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'create_notification',
                    'recipient_id': recipient.id,
                    'notification_type': notification_type,
                    'sender_id': sender.id if sender else None
                },
                user=sender or recipient
            )
            return None
    
    async def handle_message_creation(self, sender: User, recipient: User, content: str) -> Optional[Dict[str, Any]]:
        """
        Handle complete message creation process with error handling
        
        Args:
            sender: User sending the message
            recipient: User receiving the message
            content: Message content
            
        Returns:
            Dictionary with message data or None if creation failed
        """
        try:
            # Create the message
            message = await self.create_message(sender, recipient, content)
            if not message:
                return None
            
            # Create notification for recipient
            await self.create_notification(
                recipient=recipient,
                notification_type='new_message',
                title='New Message',
                message=f'{sender.get_full_name() or sender.username}: {content[:100]}...' if len(content) > 100 else f'{sender.get_full_name() or sender.username}: {content}',
                sender=sender,
                action_url=f'/messages/chat/{sender.username}/'
            )
            
            # Return message data for WebSocket transmission
            return {
                'id': message.id,
                'sender': sender.username,
                'recipient': recipient.username,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'is_read': message.is_read,
                'read_at': message.read_at.isoformat() if message.read_at else None,
                'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
            }
            
        except Exception as e:
            MessagingLogger.log_async_context_error(
                e,
                context_data={
                    'operation': 'handle_message_creation',
                    'sender_id': sender.id,
                    'recipient_id': recipient.id,
                    'content_length': len(content)
                },
                user=sender
            )
            return None
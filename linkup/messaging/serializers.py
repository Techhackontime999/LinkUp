"""
Enhanced JSON serialization for messaging system
"""
import json
import uuid
from datetime import datetime, date, time
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from .models import Message, Notification, UserStatus
from .logging_utils import MessagingLogger

User = get_user_model()


class MessagingJSONEncoder(DjangoJSONEncoder):
    """Enhanced JSON encoder for messaging system objects"""
    
    def default(self, obj):
        """Convert non-serializable objects to JSON-serializable format"""
        try:
            # Handle datetime objects
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, time):
                return obj.isoformat()
            
            # Handle UUID objects
            elif isinstance(obj, uuid.UUID):
                return str(obj)
            
            # Handle Decimal objects
            elif isinstance(obj, Decimal):
                return float(obj)
            
            # Handle Django model instances
            elif isinstance(obj, models.Model):
                return self._serialize_model(obj)
            
            # Handle querysets
            elif hasattr(obj, '__iter__') and hasattr(obj, 'model'):
                return [self._serialize_model(item) for item in obj]
            
            # Fall back to parent implementation
            return super().default(obj)
            
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=obj,
                context_data={'encoder_method': 'default', 'object_type': type(obj).__name__}
            )
            # Return a safe fallback
            return f"<{type(obj).__name__}: serialization_error>"
    
    def _serialize_model(self, obj: models.Model) -> Dict[str, Any]:
        """Serialize Django model instances safely"""
        try:
            if isinstance(obj, Message):
                return self._serialize_message(obj)
            elif isinstance(obj, User):
                return self._serialize_user(obj)
            elif isinstance(obj, Notification):
                return self._serialize_notification(obj)
            elif isinstance(obj, UserStatus):
                return self._serialize_user_status(obj)
            else:
                # Generic model serialization
                return {
                    'id': obj.pk,
                    'model': obj._meta.label,
                    'str': str(obj)
                }
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=obj,
                context_data={'method': '_serialize_model', 'model_type': type(obj).__name__}
            )
            return {'id': getattr(obj, 'pk', None), 'error': 'serialization_failed'}
    
    def _serialize_message(self, message: Message) -> Dict[str, Any]:
        """Serialize Message model safely"""
        return {
            'id': message.id,
            'sender': message.sender.username,
            'recipient': message.recipient.username,
            'content': message.content,
            'is_read': message.is_read,
            'read_at': message.read_at.isoformat() if message.read_at else None,
            'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
            'created_at': message.created_at.isoformat(),
        }
    
    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize User model safely"""
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'is_active': user.is_active,
        }
    
    def _serialize_notification(self, notification: Notification) -> Dict[str, Any]:
        """Serialize Notification model safely"""
        return {
            'id': notification.id,
            'notification_type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'sender': notification.sender.username if notification.sender else None,
            'is_read': notification.is_read,
            'read_at': notification.read_at.isoformat() if notification.read_at else None,
            'created_at': notification.created_at.isoformat(),
            'action_url': notification.action_url,
            'is_grouped': notification.is_grouped,
            'group_count': notification.group_count,
        }
    
    def _serialize_user_status(self, status: UserStatus) -> Dict[str, Any]:
        """Serialize UserStatus model safely"""
        return {
            'user': status.user.username,
            'is_online': status.is_online,
            'last_seen': status.last_seen.isoformat() if status.last_seen else None,
        }


class JSONSerializer:
    """Enhanced JSON serializer for messaging system"""
    
    def __init__(self):
        self.encoder = MessagingJSONEncoder()
    
    def serialize_message(self, message: Message) -> Dict[str, Any]:
        """
        Serialize a Message object to JSON-safe dictionary
        
        Args:
            message: Message instance to serialize
            
        Returns:
            JSON-serializable dictionary
        """
        try:
            return {
                'id': message.id,
                'sender': message.sender.username,
                'recipient': message.recipient.username,
                'content': message.content,
                'is_read': message.is_read,
                'read_at': self.serialize_datetime(message.read_at),
                'delivered_at': self.serialize_datetime(message.delivered_at),
                'created_at': self.serialize_datetime(message.created_at),
                'attachment_url': message.attachment.url if message.attachment else None,
            }
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=message,
                context_data={'method': 'serialize_message', 'message_id': getattr(message, 'id', None)}
            )
            return self._get_error_fallback('message', message)
    
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """
        Serialize datetime to ISO format string
        
        Args:
            dt: Datetime object to serialize
            
        Returns:
            ISO format string or None
        """
        if dt is None:
            return None
        
        try:
            return dt.isoformat()
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=dt,
                context_data={'method': 'serialize_datetime'}
            )
            return str(dt)  # Fallback to string representation
    
    def serialize_user_status(self, status: UserStatus) -> Dict[str, Any]:
        """
        Serialize UserStatus object to JSON-safe dictionary
        
        Args:
            status: UserStatus instance to serialize
            
        Returns:
            JSON-serializable dictionary
        """
        try:
            return {
                'user': status.user.username,
                'is_online': status.is_online,
                'last_seen': self.serialize_datetime(status.last_seen),
            }
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=status,
                context_data={'method': 'serialize_user_status', 'user_id': getattr(status.user, 'id', None)}
            )
            return self._get_error_fallback('user_status', status)
    
    def serialize_notification(self, notification: Notification) -> Dict[str, Any]:
        """
        Serialize Notification object to JSON-safe dictionary
        
        Args:
            notification: Notification instance to serialize
            
        Returns:
            JSON-serializable dictionary
        """
        try:
            return {
                'id': notification.id,
                'notification_type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'priority': notification.priority,
                'sender': notification.sender.username if notification.sender else None,
                'sender_avatar': self._get_user_avatar_url(notification.sender),
                'is_read': notification.is_read,
                'read_at': self.serialize_datetime(notification.read_at),
                'created_at': self.serialize_datetime(notification.created_at),
                'action_url': notification.action_url,
                'is_grouped': notification.is_grouped,
                'group_count': notification.group_count,
            }
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=notification,
                context_data={'method': 'serialize_notification', 'notification_id': getattr(notification, 'id', None)}
            )
            return self._get_error_fallback('notification', notification)
    
    def safe_serialize(self, obj: Any) -> Union[Dict[str, Any], str, None]:
        """
        Safely serialize any object to JSON-compatible format
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable representation
        """
        try:
            # Handle None
            if obj is None:
                return None
            
            # Handle basic types
            if isinstance(obj, (str, int, float, bool)):
                return obj
            
            # Handle datetime objects
            if isinstance(obj, (datetime, date, time)):
                return self.serialize_datetime(obj) if isinstance(obj, datetime) else obj.isoformat()
            
            # Handle Django models
            if isinstance(obj, Message):
                return self.serialize_message(obj)
            elif isinstance(obj, Notification):
                return self.serialize_notification(obj)
            elif isinstance(obj, UserStatus):
                return self.serialize_user_status(obj)
            elif isinstance(obj, User):
                return self._serialize_user_safe(obj)
            elif isinstance(obj, models.Model):
                return self._serialize_generic_model(obj)
            
            # Handle collections
            if isinstance(obj, (list, tuple)):
                return [self.safe_serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: self.safe_serialize(value) for key, value in obj.items()}
            
            # Handle querysets
            if hasattr(obj, '__iter__') and hasattr(obj, 'model'):
                return [self.safe_serialize(item) for item in obj]
            
            # Fallback to string representation
            return str(obj)
            
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=obj,
                context_data={'method': 'safe_serialize', 'object_type': type(obj).__name__}
            )
            return f"<{type(obj).__name__}: serialization_error>"
    
    def validate_serializable(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data can be serialized to JSON
        
        Args:
            data: Dictionary to validate
            
        Returns:
            True if serializable, False otherwise
        """
        try:
            json.dumps(data, cls=MessagingJSONEncoder)
            return True
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=data,
                context_data={'method': 'validate_serializable'}
            )
            return False
    
    def to_json_string(self, obj: Any) -> str:
        """
        Convert object to JSON string with error handling
        
        Args:
            obj: Object to convert to JSON
            
        Returns:
            JSON string representation
        """
        try:
            serialized = self.safe_serialize(obj)
            return json.dumps(serialized, cls=MessagingJSONEncoder)
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=obj,
                context_data={'method': 'to_json_string'}
            )
            return json.dumps({'error': 'serialization_failed', 'type': type(obj).__name__})
    
    def _serialize_user_safe(self, user: User) -> Dict[str, Any]:
        """Safely serialize User object"""
        try:
            return {
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'is_active': user.is_active,
                'avatar_url': self._get_user_avatar_url(user),
            }
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=user,
                context_data={'method': '_serialize_user_safe', 'user_id': getattr(user, 'id', None)}
            )
            return {'id': getattr(user, 'id', None), 'username': getattr(user, 'username', 'unknown')}
    
    def _serialize_generic_model(self, obj: models.Model) -> Dict[str, Any]:
        """Serialize generic Django model"""
        try:
            return {
                'id': obj.pk,
                'model': obj._meta.label,
                'str': str(obj),
            }
        except Exception as e:
            MessagingLogger.log_serialization_error(
                e,
                data=obj,
                context_data={'method': '_serialize_generic_model', 'model_type': type(obj).__name__}
            )
            return {'id': getattr(obj, 'pk', None), 'error': 'serialization_failed'}
    
    def _get_user_avatar_url(self, user: Optional[User]) -> Optional[str]:
        """Safely get user avatar URL"""
        if not user:
            return None
        
        try:
            if hasattr(user, 'profile') and user.profile and user.profile.avatar:
                return user.profile.avatar.url
        except Exception:
            pass  # Ignore avatar errors
        
        return None
    
    def _get_error_fallback(self, object_type: str, obj: Any) -> Dict[str, Any]:
        """Get error fallback representation"""
        return {
            'id': getattr(obj, 'id', None) or getattr(obj, 'pk', None),
            'type': object_type,
            'error': 'serialization_failed',
            'str': str(obj) if obj else None,
        }
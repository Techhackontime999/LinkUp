"""
Logging utilities for messaging system with error categorization
"""
import logging
import traceback
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from .models import MessagingError

logger = logging.getLogger(__name__)
User = get_user_model()


class MessagingLogger:
    """Enhanced logger for messaging system with structured error handling"""
    
    @staticmethod
    def log_async_context_error(error: Exception, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log async context related errors"""
        error_message = f"Async context error: {str(error)}"
        context = {
            'error_type': 'async_context',
            'exception_type': type(error).__name__,
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        # Store in database for monitoring
        MessagingError.log_error(
            error_type='async_context',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='high'
        )
    
    @staticmethod
    def log_serialization_error(error: Exception, data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log JSON serialization errors"""
        error_message = f"JSON serialization error: {str(error)}"
        context = {
            'error_type': 'json_serialization',
            'exception_type': type(error).__name__,
            'problematic_data_type': type(data).__name__ if data is not None else 'unknown',
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        # Don't include the actual data in logs for privacy/size reasons
        if data is not None:
            context['data_repr'] = repr(data)[:500]  # Truncate for safety
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='json_serialization',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='medium'
        )
    
    @staticmethod
    def log_connection_error(error: Exception, connection_data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log WebSocket connection handling errors"""
        error_message = f"Connection handling error: {str(error)}"
        context = {
            'error_type': 'connection_handling',
            'exception_type': type(error).__name__,
            'connection_data_type': type(connection_data).__name__ if connection_data is not None else 'unknown',
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='connection_handling',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='medium'
        )
    
    @staticmethod
    def log_routing_error(error: Exception, pattern: str = None, context_data: Dict[str, Any] = None):
        """Log routing pattern errors"""
        error_message = f"Routing pattern error: {str(error)}"
        context = {
            'error_type': 'routing_pattern',
            'exception_type': type(error).__name__,
            'pattern': pattern,
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='routing_pattern',
            error_message=error_message,
            context_data=context,
            severity='critical'  # Routing errors are critical
        )
    
    @staticmethod
    def log_websocket_error(error: Exception, message_data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log WebSocket transmission errors"""
        error_message = f"WebSocket transmission error: {str(error)}"
        context = {
            'error_type': 'websocket_transmission',
            'exception_type': type(error).__name__,
            'message_data_type': type(message_data).__name__ if message_data is not None else 'unknown',
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='websocket_transmission',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='high'
        )
    
    @staticmethod
    def log_database_error(error: Exception, operation: str = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log database operation errors"""
        error_message = f"Database operation error: {str(error)}"
        context = {
            'error_type': 'database_operation',
            'exception_type': type(error).__name__,
            'operation': operation,
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='database_operation',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='high'
        )
    
    @staticmethod
    def log_notification_error(error: Exception, notification_data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log notification delivery errors"""
        error_message = f"Notification delivery error: {str(error)}"
        context = {
            'error_type': 'notification_delivery',
            'exception_type': type(error).__name__,
            'notification_data_type': type(notification_data).__name__ if notification_data is not None else 'unknown',
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='notification_delivery',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='medium'
        )
    
    @staticmethod
    def log_message_processing_error(error: Exception, message_data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log message processing errors"""
        error_message = f"Message processing error: {str(error)}"
        context = {
            'error_type': 'message_processing',
            'exception_type': type(error).__name__,
            'message_data_type': type(message_data).__name__ if message_data is not None else 'unknown',
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        MessagingError.log_error(
            error_type='message_processing',
            error_message=error_message,
            context_data=context,
            user=user,
            severity='medium'
        )
    
    @staticmethod
    def log_info(message: str, context_data: Dict[str, Any] = None):
        """Log informational messages"""
        logger.info(message, extra=context_data or {})
    
    @staticmethod
    def log_debug(message: str, context_data: Dict[str, Any] = None):
        """Log debug messages"""
        logger.debug(message, extra=context_data or {})
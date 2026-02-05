"""
Logging utilities for messaging system with error categorization
"""
import logging
import traceback
import asyncio
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from .models import MessagingError

logger = logging.getLogger(__name__)
User = get_user_model()


class MessagingLogger:
    """Enhanced logger for messaging system with structured error handling"""
    
    @staticmethod
    def _is_async_context():
        """Check if we're in an async context"""
        try:
            asyncio.current_task()
            return True
        except RuntimeError:
            return False
    
    @staticmethod
    async def _log_error_safe(error_type, error_message, context_data=None, user=None, severity='medium'):
        """Safely log error to database, handling both sync and async contexts"""
        try:
            if MessagingLogger._is_async_context():
                # Use async-safe method
                await MessagingError.log_error_async(
                    error_type=error_type,
                    error_message=error_message,
                    context_data=context_data,
                    user=user,
                    severity=severity
                )
            else:
                # Use regular sync method
                MessagingError.log_error(
                    error_type=error_type,
                    error_message=error_message,
                    context_data=context_data,
                    user=user,
                    severity=severity
                )
        except Exception as db_error:
            # If database logging fails, at least log to console
            logger.error(f"Failed to log error to database: {db_error}")
            logger.error(f"Original error: {error_message}")
    
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
        
        # Store in database for monitoring - use sync version since this is typically called from sync context
        try:
            MessagingError.log_error(
                error_type='async_context',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='high'
            )
        except Exception as db_error:
            logger.error(f"Failed to log async context error to database: {db_error}")
    
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
        
        try:
            MessagingError.log_error(
                error_type='json_serialization',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='medium'
            )
        except Exception as db_error:
            logger.error(f"Failed to log serialization error to database: {db_error}")
    
    @staticmethod
    def log_connection_error(error_message: str, connection_data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log WebSocket connection handling errors - updated to handle string messages"""
        if isinstance(error_message, Exception):
            error_message = f"Connection handling error: {str(error_message)}"
        elif not error_message.startswith("Connection handling error:"):
            error_message = f"Connection handling error: {error_message}"
            
        context = {
            'error_type': 'connection_handling',
            'connection_data_type': type(connection_data).__name__ if connection_data is not None else 'unknown',
            'traceback': traceback.format_exc(),
            **(context_data or {})
        }
        
        logger.error(error_message, extra=context)
        
        try:
            MessagingError.log_error(
                error_type='connection_handling',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='medium'
            )
        except Exception as db_error:
            logger.error(f"Failed to log connection error to database: {db_error}")
    
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
        
        try:
            MessagingError.log_error(
                error_type='routing_pattern',
                error_message=error_message,
                context_data=context,
                severity='critical'  # Routing errors are critical
            )
        except Exception as db_error:
            logger.error(f"Failed to log routing error to database: {db_error}")
    
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
        
        try:
            MessagingError.log_error(
                error_type='websocket_transmission',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='high'
            )
        except Exception as db_error:
            logger.error(f"Failed to log websocket error to database: {db_error}")
    
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
        
        try:
            MessagingError.log_error(
                error_type='database_operation',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='high'
            )
        except Exception as db_error:
            logger.error(f"Failed to log database error to database: {db_error}")
    
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
        
        try:
            MessagingError.log_error(
                error_type='notification_delivery',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='medium'
            )
        except Exception as db_error:
            logger.error(f"Failed to log notification error to database: {db_error}")
    
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
        
        try:
            MessagingError.log_error(
                error_type='message_processing',
                error_message=error_message,
                context_data=context,
                user=user,
                severity='medium'
            )
        except Exception as db_error:
            logger.error(f"Failed to log message processing error to database: {db_error}")
    
    @staticmethod
    def log_error(message: str, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log general error messages"""
        logger.error(message, extra=context_data or {})
        
        try:
            MessagingError.log_error(
                error_type='message_processing',
                error_message=message,
                context_data=context_data or {},
                user=user,
                severity='medium'
            )
        except Exception as db_error:
            logger.error(f"Failed to log general error to database: {db_error}")
    
    @staticmethod
    def log_json_error(error: Exception, data: Any = None, context_data: Dict[str, Any] = None, user: Optional[User] = None):
        """Log JSON-related errors - alias for log_serialization_error"""
        MessagingLogger.log_serialization_error(error, data, context_data, user)
    
    @staticmethod
    def log_info(message: str, context_data: Dict[str, Any] = None):
        """Log informational messages"""
        logger.info(message, extra=context_data or {})
    
    @staticmethod
    def log_debug(message: str, context_data: Dict[str, Any] = None):
        """Log debug messages"""
        logger.debug(message, extra=context_data or {})
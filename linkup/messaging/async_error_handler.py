"""
Comprehensive async error handler for messaging system
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Union
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import MessagingError

logger = logging.getLogger(__name__)
User = get_user_model()


class AsyncErrorHandler:
    """
    Centralized async error handler that safely manages database operations
    in both sync and async contexts
    """
    
    @staticmethod
    def is_async_context() -> bool:
        """Check if we're currently in an async context"""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            return loop is not None
        except RuntimeError:
            # No event loop running, we're in sync context
            return False
    
    @staticmethod
    async def log_error_safe(
        error_type: str,
        error_message: str,
        context_data: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
        severity: str = 'medium'
    ) -> Optional[MessagingError]:
        """
        Safely log error to database, automatically handling async/sync contexts
        """
        try:
            if AsyncErrorHandler.is_async_context():
                # We're in async context, use the async method
                return await MessagingError.log_error_async(
                    error_type=error_type,
                    error_message=error_message,
                    context_data=context_data,
                    user=user,
                    severity=severity
                )
            else:
                # We're in sync context, use the regular method
                return MessagingError.log_error(
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
            return None
    
    @staticmethod
    def log_error_sync(
        error_type: str,
        error_message: str,
        context_data: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
        severity: str = 'medium'
    ) -> Optional[MessagingError]:
        """
        Synchronous error logging - safe to call from sync contexts
        """
        try:
            return MessagingError.log_error(
                error_type=error_type,
                error_message=error_message,
                context_data=context_data,
                user=user,
                severity=severity
            )
        except Exception as db_error:
            logger.error(f"Failed to log error to database: {db_error}")
            logger.error(f"Original error: {error_message}")
            return None
    
    @staticmethod
    async def handle_websocket_error(
        error: Exception,
        context: str,
        user: Optional[User] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle WebSocket-specific errors with proper async context management
        """
        error_message = f"WebSocket error in {context}: {str(error)}"
        context_data = {
            'context': context,
            'error_type': type(error).__name__,
            'user_id': user.id if user else None,
            **(additional_context or {})
        }
        
        # Log to console immediately
        logger.error(error_message, extra=context_data)
        
        # Try to log to database
        await AsyncErrorHandler.log_error_safe(
            error_type='websocket_transmission',
            error_message=error_message,
            context_data=context_data,
            user=user,
            severity='high'
        )
    
    @staticmethod
    async def handle_async_context_error(
        error: Exception,
        operation: str,
        user: Optional[User] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle async context errors specifically
        """
        error_message = f"Async context error in {operation}: {str(error)}"
        context_data = {
            'operation': operation,
            'error_type': type(error).__name__,
            'user_id': user.id if user else None,
            'is_async_context': AsyncErrorHandler.is_async_context(),
            **(additional_context or {})
        }
        
        # Log to console immediately
        logger.error(error_message, extra=context_data)
        
        # Use sync logging to avoid recursive async context issues
        try:
            MessagingError.log_error(
                error_type='async_context',
                error_message=error_message,
                context_data=context_data,
                user=user,
                severity='critical'
            )
        except Exception as db_error:
            logger.error(f"Failed to log async context error to database: {db_error}")


# Convenience functions for common error scenarios
async def log_websocket_error(error: Exception, context: str, user: Optional[User] = None, **kwargs):
    """Convenience function for WebSocket errors"""
    await AsyncErrorHandler.handle_websocket_error(error, context, user, kwargs)

async def log_async_context_error(error: Exception, operation: str, user: Optional[User] = None, **kwargs):
    """Convenience function for async context errors"""
    await AsyncErrorHandler.handle_async_context_error(error, operation, user, kwargs)

def log_sync_error(error_type: str, message: str, user: Optional[User] = None, **kwargs):
    """Convenience function for sync context errors"""
    return AsyncErrorHandler.log_error_sync(error_type, message, kwargs, user)
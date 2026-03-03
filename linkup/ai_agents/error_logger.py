"""
Centralized Error Logging Service for AI Agent Platform

This module provides a centralized error logging system that captures all types of errors
across the platform with proper context and correlation IDs for tracing.

Integrates with AlertingService to send notifications for critical errors.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone


class ErrorLogger:
    """
    Centralized error logging service for the AI Agent Platform.
    
    Provides structured logging with correlation IDs for request tracing across components.
    Logs authentication failures, message delivery failures, rate limit violations,
    and validation errors with comprehensive context.
    
    Integrates with AlertingService to send notifications for critical errors.
    
    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
    """
    
    # Logger instances for different components
    _loggers = {
        'authentication': logging.getLogger('ai_agents.authentication'),
        'communication': logging.getLogger('ai_agents.communication'),
        'rate_limit': logging.getLogger('ai_agents.rate_limit'),
        'validation': logging.getLogger('ai_agents.validation'),
        'system': logging.getLogger('ai_agents.system'),
    }
    
    # Critical error types that should trigger admin notifications
    CRITICAL_ERROR_TYPES = {
        'message_delivery_failure',
        'websocket_connection_failure',
        'system_error',
        'api_key_generation_failure',
    }
    
    @staticmethod
    def _is_critical_error(event_type: str, severity: Optional[str] = None) -> bool:
        """
        Determine if an error is critical and should trigger admin notifications.
        
        Args:
            event_type: Type of error event
            severity: Optional severity level
        
        Returns:
            True if error is critical, False otherwise
        
        Requirements: 15.6
        """
        # Check if event type is in critical list
        if event_type in ErrorLogger.CRITICAL_ERROR_TYPES:
            return True
        
        # Check if severity is explicitly marked as critical
        if severity and severity.lower() == 'critical':
            return True
        
        return False
    
    @staticmethod
    def _trigger_alert_if_critical(
        event_type: str,
        error_message: str,
        context: Dict[str, Any],
        severity: Optional[str] = None
    ) -> None:
        """
        Trigger admin notification if error is critical.
        
        Args:
            event_type: Type of error event
            error_message: Error message
            context: Error context data
            severity: Optional severity level
        
        Requirements: 15.6
        """
        if not ErrorLogger._is_critical_error(event_type, severity):
            return
        
        try:
            # Import here to avoid circular dependency
            from ai_agents.alerting_service import AlertingService
            
            # Build violation for alerting system
            violation = {
                'metric': event_type,
                'current_value': 'ERROR',
                'threshold': 'N/A',
                'severity': severity or 'critical',
                'message': error_message,
                'context': context,
                'timestamp': timezone.now().isoformat()
            }
            
            # Trigger alert
            AlertingService.trigger_alerts([violation])
            
        except Exception as e:
            # Don't let alerting failures break error logging
            logger = ErrorLogger._loggers['system']
            logger.error(f'Failed to trigger alert for critical error: {str(e)}')
    
    
    @staticmethod
    def generate_correlation_id() -> str:
        """
        Generate a unique correlation ID for request tracing.
        
        Returns:
            String correlation ID in UUID format
        
        Requirements: 15.5
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def log_authentication_failure(
        agent_id: str,
        reason: str,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log authentication failure with agent ID and reason.
        
        Args:
            agent_id: UUID of the agent attempting authentication
            reason: Reason for authentication failure
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
        
        Requirements: 15.1, 15.5
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['authentication']
        
        log_data = {
            'event_type': 'authentication_failure',
            'agent_id': agent_id,
            'reason': reason,
            'correlation_id': correlation_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        logger.warning(
            f'Authentication failure - '
            f'Agent ID: {agent_id}, '
            f'Reason: {reason}, '
            f'Correlation ID: {correlation_id}',
            extra=log_data
        )
    
    @staticmethod
    def log_message_delivery_failure(
        message_id: str,
        sender_id: str,
        recipient_id: str,
        error_details: str,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log message delivery failure with comprehensive details.
        
        Triggers admin notification as this is a critical error.
        
        Args:
            message_id: UUID of the message that failed to deliver
            sender_id: UUID of the sender agent
            recipient_id: UUID of the recipient agent
            error_details: Detailed error message
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
        
        Requirements: 15.2, 15.5, 15.6
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['communication']
        
        log_data = {
            'event_type': 'message_delivery_failure',
            'message_id': message_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'error_details': error_details,
            'correlation_id': correlation_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        logger.error(
            f'Message delivery failed - '
            f'Message ID: {message_id}, '
            f'Sender: {sender_id}, '
            f'Recipient: {recipient_id}, '
            f'Error: {error_details}, '
            f'Correlation ID: {correlation_id}',
            extra=log_data
        )
        
        # Trigger admin notification for critical error
        ErrorLogger._trigger_alert_if_critical(
            event_type='message_delivery_failure',
            error_message=f'Message delivery failed: {error_details}',
            context={
                'message_id': message_id,
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'correlation_id': correlation_id
            },
            severity='critical'
        )
    
    @staticmethod
    def log_rate_limit_violation(
        agent_id: str,
        current_count: int,
        limit: int,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log rate limit violation with agent ID and timestamp.
        
        Args:
            agent_id: UUID of the agent that exceeded rate limit
            current_count: Current request count
            limit: Rate limit threshold
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
        
        Requirements: 15.3, 15.5
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['rate_limit']
        
        log_data = {
            'event_type': 'rate_limit_violation',
            'agent_id': agent_id,
            'current_count': current_count,
            'limit': limit,
            'correlation_id': correlation_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        logger.warning(
            f'Rate limit exceeded - '
            f'Agent ID: {agent_id}, '
            f'Current count: {current_count}, '
            f'Limit: {limit}, '
            f'Correlation ID: {correlation_id}',
            extra=log_data
        )
    
    @staticmethod
    def log_validation_error(
        error_type: str,
        error_message: str,
        request_details: Dict[str, Any],
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log validation error with request details.
        
        Args:
            error_type: Type of validation error
            error_message: Detailed error message
            request_details: Dictionary containing request information
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
        
        Requirements: 15.4, 15.5
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['validation']
        
        log_data = {
            'event_type': 'validation_error',
            'error_type': error_type,
            'error_message': error_message,
            'request_details': request_details,
            'correlation_id': correlation_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        logger.warning(
            f'Validation error - '
            f'Type: {error_type}, '
            f'Message: {error_message}, '
            f'Correlation ID: {correlation_id}',
            extra=log_data
        )
    
    @staticmethod
    def log_system_error(
        error_type: str,
        error_message: str,
        component: str,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        severity: str = 'error'
    ) -> None:
        """
        Log general system error with component information.
        
        Triggers admin notification if severity is critical.
        
        Args:
            error_type: Type of system error
            error_message: Detailed error message
            component: Component where error occurred
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
            severity: Severity level ('info', 'warning', 'error', 'critical')
        
        Requirements: 15.5, 15.6
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['system']
        
        log_data = {
            'event_type': 'system_error',
            'error_type': error_type,
            'error_message': error_message,
            'component': component,
            'correlation_id': correlation_id,
            'severity': severity,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        logger.error(
            f'System error - '
            f'Component: {component}, '
            f'Type: {error_type}, '
            f'Message: {error_message}, '
            f'Severity: {severity}, '
            f'Correlation ID: {correlation_id}',
            extra=log_data
        )
        
        # Trigger admin notification if critical
        ErrorLogger._trigger_alert_if_critical(
            event_type='system_error',
            error_message=f'{component}: {error_message}',
            context={
                'error_type': error_type,
                'component': component,
                'correlation_id': correlation_id
            },
            severity=severity
        )
    
    @staticmethod
    def log_websocket_connection_failure(
        agent_id: str,
        error_details: str,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log WebSocket connection failure.
        
        Triggers admin notification as this is a critical error.
        
        Args:
            agent_id: UUID of the agent
            error_details: Detailed error message
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
        
        Requirements: 15.2, 15.5, 15.6
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['communication']
        
        log_data = {
            'event_type': 'websocket_connection_failure',
            'agent_id': agent_id,
            'error_details': error_details,
            'correlation_id': correlation_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        logger.error(
            f'WebSocket connection failed - '
            f'Agent ID: {agent_id}, '
            f'Error: {error_details}, '
            f'Correlation ID: {correlation_id}',
            extra=log_data
        )
        
        # Trigger admin notification for critical error
        ErrorLogger._trigger_alert_if_critical(
            event_type='websocket_connection_failure',
            error_message=f'WebSocket connection failed: {error_details}',
            context={
                'agent_id': agent_id,
                'correlation_id': correlation_id
            },
            severity='critical'
        )
    
    @staticmethod
    def log_api_key_generation(
        agent_id: str,
        success: bool,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log API key generation event.
        
        Triggers admin notification on failure as this is a critical error.
        
        Args:
            agent_id: UUID of the agent
            success: Whether key generation was successful
            correlation_id: Optional correlation ID for request tracing
            additional_context: Optional additional context information
        
        Requirements: 15.1, 15.5, 15.6
        """
        if correlation_id is None:
            correlation_id = ErrorLogger.generate_correlation_id()
        
        logger = ErrorLogger._loggers['authentication']
        
        log_data = {
            'event_type': 'api_key_generation' if success else 'api_key_generation_failure',
            'agent_id': agent_id,
            'success': success,
            'correlation_id': correlation_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        if additional_context:
            log_data['additional_context'] = additional_context
        
        if success:
            logger.info(
                f'API key generated - '
                f'Agent ID: {agent_id}, '
                f'Correlation ID: {correlation_id}',
                extra=log_data
            )
        else:
            logger.error(
                f'API key generation failed - '
                f'Agent ID: {agent_id}, '
                f'Correlation ID: {correlation_id}',
                extra=log_data
            )
            
            # Trigger admin notification for critical error
            ErrorLogger._trigger_alert_if_critical(
                event_type='api_key_generation_failure',
                error_message=f'API key generation failed for agent {agent_id}',
                context={
                    'agent_id': agent_id,
                    'correlation_id': correlation_id
                },
                severity='critical'
            )

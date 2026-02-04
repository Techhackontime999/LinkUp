"""
Comprehensive Error Handler for WhatsApp-like Messaging System

Provides centralized error handling, logging, monitoring, and recovery mechanisms
for the messaging system with circuit breaker patterns and user feedback.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import transaction
from enum import Enum
import uuid

User = get_user_model()
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    WEBSOCKET = "websocket"
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    USER_INPUT = "user_input"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class MessagingErrorHandler:
    """
    Comprehensive error handler for the messaging system.
    
    Features:
    - Centralized error logging and classification
    - Circuit breaker patterns for high load scenarios
    - User-friendly error messages and recovery suggestions
    - Error rate monitoring and alerting
    - Automatic error recovery mechanisms
    """
    
    def __init__(self):
        self.circuit_breakers = {}
        self.error_counters = {}
        self.recovery_callbacks = {}
        
        # Configuration
        self.circuit_breaker_config = {
            'failure_threshold': 10,
            'timeout_seconds': 60,
            'half_open_max_calls': 3
        }
        
        self.error_rate_config = {
            'window_minutes': 5,
            'alert_threshold': 50,  # errors per window
            'critical_threshold': 100
        }
    
    def handle_error(self, 
                    error: Exception, 
                    context: Dict[str, Any],
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    user_id: Optional[int] = None,
                    recovery_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging, classification, and recovery.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            severity: Error severity level
            category: Error category for classification
            user_id: ID of the affected user (if applicable)
            recovery_callback: Optional callback for automatic recovery
            
        Returns:
            Dict containing error handling result and user-friendly information
        """
        error_id = f"err_{uuid.uuid4().hex[:12]}"
        timestamp = timezone.now()
        
        # Create comprehensive error record
        error_record = {
            'error_id': error_id,
            'timestamp': timestamp.isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity.value,
            'category': category.value,
            'context': context,
            'user_id': user_id,
            'stack_trace': self._get_stack_trace(error) if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
        
        # Log error with appropriate level
        self._log_error(error_record)
        
        # Update error counters and check rates
        self._update_error_counters(category, severity)
        
        # Check and update circuit breakers
        circuit_key = self._get_circuit_key(category, context)
        circuit_action = self._update_circuit_breaker(circuit_key, error_record)
        
        # Attempt automatic recovery if callback provided
        recovery_result = None
        if recovery_callback and circuit_action != 'circuit_open':
            try:
                recovery_result = recovery_callback()
                if recovery_result:
                    error_record['recovery_attempted'] = True
                    error_record['recovery_successful'] = recovery_result
            except Exception as recovery_error:
                logger.error(f"Recovery callback failed for error {error_id}: {recovery_error}")
                error_record['recovery_error'] = str(recovery_error)
        
        # Generate user-friendly response
        user_response = self._generate_user_response(error_record, circuit_action)
        
        # Store error for monitoring (using cache for recent errors)
        self._store_error_for_monitoring(error_record)
        
        # Check if we need to send alerts
        self._check_alert_conditions(category, severity)
        
        return {
            'error_id': error_id,
            'handled': True,
            'circuit_action': circuit_action,
            'user_message': user_response['message'],
            'user_actions': user_response['actions'],
            'severity': severity.value,
            'recovery_attempted': recovery_result is not None,
            'recovery_successful': recovery_result if recovery_result is not None else False
        }
    
    def _get_stack_trace(self, error: Exception) -> str:
        """Get formatted stack trace for debugging"""
        import traceback
        return traceback.format_exc()
    
    def _log_error(self, error_record: Dict[str, Any]):
        """Log error with appropriate level based on severity"""
        severity = ErrorSeverity(error_record['severity'])
        
        log_message = (
            f"Error {error_record['error_id']}: {error_record['error_message']} "
            f"[{error_record['category']}] User: {error_record.get('user_id', 'N/A')}"
        )
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=error_record)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=error_record)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=error_record)
        else:
            logger.info(log_message, extra=error_record)
    
    def _update_error_counters(self, category: ErrorCategory, severity: ErrorSeverity):
        """Update error counters for rate monitoring"""
        current_minute = timezone.now().replace(second=0, microsecond=0)
        
        # Counter keys
        category_key = f"error_count_{category.value}_{current_minute.isoformat()}"
        severity_key = f"error_count_{severity.value}_{current_minute.isoformat()}"
        total_key = f"error_count_total_{current_minute.isoformat()}"
        
        # Increment counters (expire after window + buffer)
        cache_timeout = (self.error_rate_config['window_minutes'] + 1) * 60
        
        cache.set(category_key, cache.get(category_key, 0) + 1, cache_timeout)
        cache.set(severity_key, cache.get(severity_key, 0) + 1, cache_timeout)
        cache.set(total_key, cache.get(total_key, 0) + 1, cache_timeout)
    
    def _get_circuit_key(self, category: ErrorCategory, context: Dict[str, Any]) -> str:
        """Generate circuit breaker key based on category and context"""
        if category == ErrorCategory.WEBSOCKET:
            return f"circuit_websocket_{context.get('room_name', 'default')}"
        elif category == ErrorCategory.DATABASE:
            return f"circuit_database_{context.get('operation', 'default')}"
        elif category == ErrorCategory.NETWORK:
            return f"circuit_network_{context.get('endpoint', 'default')}"
        else:
            return f"circuit_{category.value}_default"
    
    def _update_circuit_breaker(self, circuit_key: str, error_record: Dict[str, Any]) -> str:
        """Update circuit breaker state and return action taken"""
        if circuit_key not in self.circuit_breakers:
            self.circuit_breakers[circuit_key] = {
                'state': CircuitBreakerState.CLOSED,
                'failure_count': 0,
                'last_failure_time': None,
                'half_open_attempts': 0
            }
        
        breaker = self.circuit_breakers[circuit_key]
        current_time = timezone.now()
        
        # Check if circuit should be reset from OPEN to HALF_OPEN
        if (breaker['state'] == CircuitBreakerState.OPEN and 
            breaker['last_failure_time'] and
            current_time - breaker['last_failure_time'] > timedelta(seconds=self.circuit_breaker_config['timeout_seconds'])):
            breaker['state'] = CircuitBreakerState.HALF_OPEN
            breaker['half_open_attempts'] = 0
            logger.info(f"Circuit breaker {circuit_key} moved to HALF_OPEN")
        
        # Handle failure based on current state
        if breaker['state'] == CircuitBreakerState.CLOSED:
            breaker['failure_count'] += 1
            breaker['last_failure_time'] = current_time
            
            if breaker['failure_count'] >= self.circuit_breaker_config['failure_threshold']:
                breaker['state'] = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker {circuit_key} OPENED due to {breaker['failure_count']} failures")
                return 'circuit_opened'
            
            return 'failure_recorded'
        
        elif breaker['state'] == CircuitBreakerState.HALF_OPEN:
            breaker['half_open_attempts'] += 1
            
            if breaker['half_open_attempts'] >= self.circuit_breaker_config['half_open_max_calls']:
                breaker['state'] = CircuitBreakerState.OPEN
                breaker['last_failure_time'] = current_time
                logger.warning(f"Circuit breaker {circuit_key} returned to OPEN after failed half-open attempts")
                return 'circuit_reopened'
            
            return 'half_open_failure'
        
        else:  # OPEN
            return 'circuit_open'
    
    def _generate_user_response(self, error_record: Dict[str, Any], circuit_action: str) -> Dict[str, Any]:
        """Generate user-friendly error response with actionable suggestions"""
        category = ErrorCategory(error_record['category'])
        severity = ErrorSeverity(error_record['severity'])
        
        # Base response structure
        response = {
            'message': 'An error occurred',
            'actions': []
        }
        
        # Category-specific messages and actions
        if category == ErrorCategory.WEBSOCKET:
            if circuit_action == 'circuit_open':
                response['message'] = 'Connection issues detected. Please wait a moment before trying again.'
                response['actions'] = [
                    {'type': 'wait', 'duration': 60, 'label': 'Wait 1 minute'},
                    {'type': 'refresh', 'label': 'Refresh page'},
                    {'type': 'retry', 'label': 'Try again'}
                ]
            else:
                response['message'] = 'Connection temporarily unavailable. Your message will be sent automatically.'
                response['actions'] = [
                    {'type': 'retry', 'label': 'Retry now'},
                    {'type': 'refresh', 'label': 'Refresh connection'}
                ]
        
        elif category == ErrorCategory.DATABASE:
            response['message'] = 'Data synchronization issue. Your messages are safe and will be delivered.'
            response['actions'] = [
                {'type': 'sync', 'label': 'Sync messages'},
                {'type': 'retry', 'label': 'Try again'}
            ]
        
        elif category == ErrorCategory.NETWORK:
            response['message'] = 'Network connectivity issue. Check your internet connection.'
            response['actions'] = [
                {'type': 'check_connection', 'label': 'Check connection'},
                {'type': 'retry', 'label': 'Retry'},
                {'type': 'offline_mode', 'label': 'Continue offline'}
            ]
        
        elif category == ErrorCategory.VALIDATION:
            response['message'] = 'Invalid input. Please check your message and try again.'
            response['actions'] = [
                {'type': 'edit', 'label': 'Edit message'},
                {'type': 'clear', 'label': 'Clear and start over'}
            ]
        
        elif category == ErrorCategory.RATE_LIMIT:
            response['message'] = 'Too many requests. Please wait a moment before sending more messages.'
            response['actions'] = [
                {'type': 'wait', 'duration': 30, 'label': 'Wait 30 seconds'},
                {'type': 'queue', 'label': 'Queue message for later'}
            ]
        
        else:
            # Generic error handling
            if severity == ErrorSeverity.CRITICAL:
                response['message'] = 'A critical error occurred. Please refresh the page or contact support.'
                response['actions'] = [
                    {'type': 'refresh', 'label': 'Refresh page'},
                    {'type': 'contact_support', 'label': 'Contact support'}
                ]
            else:
                response['message'] = 'Something went wrong. Please try again.'
                response['actions'] = [
                    {'type': 'retry', 'label': 'Try again'},
                    {'type': 'refresh', 'label': 'Refresh'}
                ]
        
        return response
    
    def _store_error_for_monitoring(self, error_record: Dict[str, Any]):
        """Store error record for monitoring and analytics"""
        # Store in cache for recent error tracking
        cache_key = f"recent_errors_{error_record['user_id'] or 'system'}"
        recent_errors = cache.get(cache_key, [])
        
        # Keep only essential info for cache storage
        cache_record = {
            'error_id': error_record['error_id'],
            'timestamp': error_record['timestamp'],
            'category': error_record['category'],
            'severity': error_record['severity'],
            'message': error_record['error_message']
        }
        
        recent_errors.append(cache_record)
        
        # Keep only last 20 errors per user
        if len(recent_errors) > 20:
            recent_errors = recent_errors[-20:]
        
        # Store for 1 hour
        cache.set(cache_key, recent_errors, 3600)
    
    def _check_alert_conditions(self, category: ErrorCategory, severity: ErrorSeverity):
        """Check if error rates exceed alert thresholds"""
        current_time = timezone.now()
        window_start = current_time - timedelta(minutes=self.error_rate_config['window_minutes'])
        
        # Count errors in the current window
        total_errors = 0
        for minute_offset in range(self.error_rate_config['window_minutes']):
            minute = (current_time - timedelta(minutes=minute_offset)).replace(second=0, microsecond=0)
            minute_key = f"error_count_total_{minute.isoformat()}"
            total_errors += cache.get(minute_key, 0)
        
        # Check thresholds
        if total_errors >= self.error_rate_config['critical_threshold']:
            self._send_critical_alert(total_errors, category, severity)
        elif total_errors >= self.error_rate_config['alert_threshold']:
            self._send_warning_alert(total_errors, category, severity)
    
    def _send_critical_alert(self, error_count: int, category: ErrorCategory, severity: ErrorSeverity):
        """Send critical error rate alert"""
        logger.critical(
            f"CRITICAL: Error rate exceeded threshold - {error_count} errors in "
            f"{self.error_rate_config['window_minutes']} minutes. "
            f"Latest: {category.value}/{severity.value}"
        )
        
        # Here you could integrate with external alerting systems
        # like Slack, email, PagerDuty, etc.
    
    def _send_warning_alert(self, error_count: int, category: ErrorCategory, severity: ErrorSeverity):
        """Send warning error rate alert"""
        logger.warning(
            f"WARNING: High error rate - {error_count} errors in "
            f"{self.error_rate_config['window_minutes']} minutes. "
            f"Latest: {category.value}/{severity.value}"
        )
    
    def get_circuit_breaker_status(self, circuit_key: str) -> Dict[str, Any]:
        """Get current status of a circuit breaker"""
        if circuit_key not in self.circuit_breakers:
            return {'state': 'closed', 'failure_count': 0}
        
        breaker = self.circuit_breakers[circuit_key]
        return {
            'state': breaker['state'].value,
            'failure_count': breaker['failure_count'],
            'last_failure_time': breaker['last_failure_time'].isoformat() if breaker['last_failure_time'] else None,
            'half_open_attempts': breaker.get('half_open_attempts', 0)
        }
    
    def reset_circuit_breaker(self, circuit_key: str) -> bool:
        """Manually reset a circuit breaker"""
        if circuit_key in self.circuit_breakers:
            self.circuit_breakers[circuit_key] = {
                'state': CircuitBreakerState.CLOSED,
                'failure_count': 0,
                'last_failure_time': None,
                'half_open_attempts': 0
            }
            logger.info(f"Circuit breaker {circuit_key} manually reset")
            return True
        return False
    
    def get_error_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        current_time = timezone.now()
        
        # Get error counts by category and severity for the current window
        stats = {
            'window_minutes': self.error_rate_config['window_minutes'],
            'current_time': current_time.isoformat(),
            'categories': {},
            'severities': {},
            'total_errors': 0,
            'circuit_breakers': {}
        }
        
        # Count errors in the current window
        for minute_offset in range(self.error_rate_config['window_minutes']):
            minute = (current_time - timedelta(minutes=minute_offset)).replace(second=0, microsecond=0)
            
            # Total errors
            total_key = f"error_count_total_{minute.isoformat()}"
            minute_total = cache.get(total_key, 0)
            stats['total_errors'] += minute_total
            
            # By category
            for category in ErrorCategory:
                category_key = f"error_count_{category.value}_{minute.isoformat()}"
                category_count = cache.get(category_key, 0)
                stats['categories'][category.value] = stats['categories'].get(category.value, 0) + category_count
            
            # By severity
            for severity in ErrorSeverity:
                severity_key = f"error_count_{severity.value}_{minute.isoformat()}"
                severity_count = cache.get(severity_key, 0)
                stats['severities'][severity.value] = stats['severities'].get(severity.value, 0) + severity_count
        
        # Circuit breaker status
        for circuit_key, breaker in self.circuit_breakers.items():
            stats['circuit_breakers'][circuit_key] = self.get_circuit_breaker_status(circuit_key)
        
        # User-specific recent errors if requested
        if user_id:
            cache_key = f"recent_errors_{user_id}"
            stats['user_recent_errors'] = cache.get(cache_key, [])
        
        return stats
    
    def is_circuit_breaker_open(self, circuit_key: str) -> bool:
        """Check if a circuit breaker is currently open"""
        if circuit_key not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[circuit_key]
        
        # Check if OPEN circuit should transition to HALF_OPEN
        if (breaker['state'] == CircuitBreakerState.OPEN and 
            breaker['last_failure_time'] and
            timezone.now() - breaker['last_failure_time'] > timedelta(seconds=self.circuit_breaker_config['timeout_seconds'])):
            breaker['state'] = CircuitBreakerState.HALF_OPEN
            breaker['half_open_attempts'] = 0
            return False
        
        return breaker['state'] == CircuitBreakerState.OPEN


# Global error handler instance
error_handler = MessagingErrorHandler()
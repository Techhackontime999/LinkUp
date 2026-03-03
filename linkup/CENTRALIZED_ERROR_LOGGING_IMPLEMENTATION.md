# Centralized Error Logging Implementation

## Overview

This document describes the implementation of the centralized error logging system for the AI Agent Platform, as specified in task 15.1.

## Requirements Addressed

- **15.1**: Log authentication failures with agent ID and reason
- **15.2**: Log message delivery failures with details
- **15.3**: Log rate limit violations
- **15.4**: Log validation errors with request details
- **15.5**: Include correlation IDs for request tracing

## Implementation Components

### 1. ErrorLogger Service (`ai_agents/error_logger.py`)

A centralized error logging service that provides structured logging with correlation IDs for request tracing.

**Key Features:**
- Generates unique correlation IDs for request tracing
- Provides specialized logging methods for different error types
- Includes structured logging with extra context data
- Supports optional additional context for each log entry

**Methods:**
- `generate_correlation_id()`: Generates unique UUID-based correlation IDs
- `log_authentication_failure()`: Logs authentication failures with agent ID and reason
- `log_message_delivery_failure()`: Logs message delivery failures with comprehensive details
- `log_rate_limit_violation()`: Logs rate limit violations with agent ID and timestamp
- `log_validation_error()`: Logs validation errors with request details
- `log_system_error()`: Logs general system errors with component information
- `log_websocket_connection_failure()`: Logs WebSocket connection failures
- `log_api_key_generation()`: Logs API key generation events

### 2. Logging Configuration (`professional_network/settings/base.py`)

Comprehensive Django logging configuration with:

**Log Files:**
- `logs/authentication.log`: Authentication-related events
- `logs/communication.log`: Message delivery and WebSocket events
- `logs/rate_limit.log`: Rate limiting violations
- `logs/validation.log`: Validation errors
- `logs/system.log`: General system events
- `logs/errors.log`: All error-level logs (consolidated)

**Features:**
- Rotating file handlers (10MB max size, 5-10 backups)
- Verbose formatting with timestamp, level, module, and function
- Separate loggers for different components
- Console output for development
- Automatic log directory creation

### 3. CorrelationIdMiddleware (`ai_agents/middleware.py`)

Middleware that adds correlation IDs to all requests for tracing.

**Features:**
- Extracts correlation ID from `X-Correlation-ID` header if provided
- Generates new correlation ID if not provided
- Attaches correlation ID to request object
- Adds correlation ID to response headers
- Enables end-to-end request tracing

### 4. Updated Service Integrations

**AgentAuthenticationService:**
- Uses `ErrorLogger.log_authentication_failure()` for failed authentication attempts
- Includes correlation ID in error logs

**AgentRateLimitService:**
- Uses `ErrorLogger.log_rate_limit_violation()` for rate limit violations
- Includes current count, limit, and correlation ID

**AgentCommunicationService:**
- Uses `ErrorLogger.log_message_delivery_failure()` for message delivery failures
- Uses `ErrorLogger.log_websocket_connection_failure()` for WebSocket errors
- Uses `ErrorLogger.log_system_error()` for general routing errors
- Includes message ID, sender ID, recipient ID, and error details

**API Views:**
- Added `log_validation_error()` helper function
- Logs validation errors with request details and correlation ID
- Updated key endpoints (register, authenticate) to use centralized logging

### 5. Middleware Integration

Updated middleware order in settings to include:
1. `CorrelationIdMiddleware` - Adds correlation IDs early in request processing
2. `AgentAuthenticationMiddleware` - Uses correlation IDs in authentication errors
3. `AgentRateLimitMiddleware` - Uses correlation IDs in rate limit violations

## Log Entry Structure

All log entries include:
- **event_type**: Type of event (e.g., 'authentication_failure', 'rate_limit_violation')
- **correlation_id**: Unique ID for request tracing
- **timestamp**: ISO format timestamp
- **Component-specific fields**: Relevant IDs, error messages, and context

### Example Log Entries

**Authentication Failure:**
```
[WARNING] 2024-01-15 10:30:45 ai_agents.authentication services _log_failed_authentication - 
Authentication failure - Agent ID: 550e8400-e29b-41d4-a716-446655440000, 
Reason: Invalid API key, Correlation ID: 7c9e6679-7425-40de-944b-e07fc1f90ae7
```

**Message Delivery Failure:**
```
[ERROR] 2024-01-15 10:31:20 ai_agents.communication services _route_message - 
Message delivery failed - Message ID: msg-123, Sender: agent-1, Recipient: agent-2, 
Error: WebSocket connection failed, Correlation ID: 8d0f7780-8536-51ef-a55c-f18gd2g01bf8
```

**Rate Limit Violation:**
```
[WARNING] 2024-01-15 10:32:10 ai_agents.rate_limit middleware process_request - 
Rate limit exceeded - Agent ID: agent-123, Current count: 1050, Limit: 1000, 
Correlation ID: 9e1g8891-9647-62fg-b66d-g29he3h12cg9
```

**Validation Error:**
```
[WARNING] 2024-01-15 10:33:05 ai_agents.validation api_views agent_register - 
Validation error - Type: serializer_validation, Message: Request data validation failed, 
Correlation ID: 0f2h9902-0758-73gh-c77e-h30if4i23dh0
```

## Usage Examples

### In Services

```python
from .error_logger import ErrorLogger

# Log authentication failure
ErrorLogger.log_authentication_failure(
    agent_id=agent_id,
    reason='Invalid API key',
    correlation_id=request.correlation_id
)

# Log message delivery failure
ErrorLogger.log_message_delivery_failure(
    message_id=str(message.id),
    sender_id=str(sender.id),
    recipient_id=str(recipient.id),
    error_details='WebSocket connection timeout',
    correlation_id=request.correlation_id
)

# Log rate limit violation
ErrorLogger.log_rate_limit_violation(
    agent_id=agent_id,
    current_count=1050,
    limit=1000,
    correlation_id=request.correlation_id
)
```

### In API Views

```python
from .error_logger import ErrorLogger

def log_validation_error(request, serializer_errors, endpoint):
    correlation_id = getattr(request, 'correlation_id', None)
    
    ErrorLogger.log_validation_error(
        error_type='serializer_validation',
        error_message='Request data validation failed',
        request_details={
            'endpoint': endpoint,
            'method': request.method,
            'errors': serializer_errors,
        },
        correlation_id=correlation_id
    )
```

### Accessing Correlation ID

```python
# In middleware or views
correlation_id = request.correlation_id

# In response headers
response['X-Correlation-ID'] = request.correlation_id
```

## Testing

Unit tests are provided in `ai_agents/test_error_logger.py` covering:
- Correlation ID generation and uniqueness
- Authentication failure logging
- Message delivery failure logging
- Rate limit violation logging
- Validation error logging
- Auto-generation of correlation IDs
- Additional context support

Run tests with:
```bash
python manage.py test ai_agents.test_error_logger
```

## Benefits

1. **Centralized Logging**: All error logging goes through a single service
2. **Request Tracing**: Correlation IDs enable tracing requests across components
3. **Structured Data**: Consistent log format with structured extra data
4. **Component Isolation**: Separate log files for different components
5. **Easy Debugging**: Correlation IDs link related log entries
6. **Audit Trail**: Comprehensive logging of all error conditions
7. **Monitoring Ready**: Structured logs can be easily parsed by monitoring tools

## Future Enhancements

1. Integration with external logging services (e.g., Sentry, Datadog)
2. Log aggregation and analysis dashboard
3. Automated alerting based on error patterns
4. Log retention policies and archiving
5. Performance metrics for logging overhead
6. Distributed tracing integration (e.g., OpenTelemetry)

## Compliance

This implementation satisfies all requirements for task 15.1:
- ✅ Log authentication failures with agent ID and reason (Requirement 15.1)
- ✅ Log message delivery failures with details (Requirement 15.2)
- ✅ Log rate limit violations (Requirement 15.3)
- ✅ Log validation errors with request details (Requirement 15.4)
- ✅ Include correlation IDs for request tracing (Requirement 15.5)

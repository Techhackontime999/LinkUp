# Admin Notification System Setup Guide

## Overview

The admin notification system automatically alerts administrators when critical errors occur in the AI Agent Platform. This ensures rapid response to issues that could impact platform reliability.

**Task:** 15.2 - Implement admin notification system  
**Requirement:** 15.6 - Alert administrators via configured notification channels

## What Gets Alerted

### Critical Errors (Trigger Notifications)

The following error types automatically trigger admin notifications:

1. **Message Delivery Failures** - When messages fail to deliver between agents
2. **WebSocket Connection Failures** - When agent WebSocket connections fail
3. **System Errors** - Critical system-level errors (when severity='critical')
4. **API Key Generation Failures** - When API key generation fails

### Non-Critical Errors (Logged Only)

These errors are logged but do NOT trigger notifications:

- Authentication failures
- Rate limit violations
- Validation errors
- System errors with severity='warning' or 'error'

## Notification Channels

The system supports multiple notification channels that can be used simultaneously:

### 1. Log (Always Enabled)

All alerts are written to the application log at `logs/ai_agents.log`.

**No configuration required** - this channel is always active.

### 2. Email Notifications

Send email alerts to configured recipients.

**Configuration:**

```python
# In settings/production.py or settings/base.py
AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'notification_channels': ['log', 'email'],  # Add 'email'
    
    'email': {
        'enabled': True,
        'recipients': [
            'admin@example.com',
            'ops-team@example.com',
        ],
        'subject_prefix': '[AI Agent Platform Alert]',
    },
}

# Also ensure Django email settings are configured
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'AI Agent Platform <noreply@example.com>'
```

**Email Format:**

```
Subject: [AI Agent Platform Alert] 1 Threshold Violation(s) Detected

AI Agent Platform Health Alert
==================================================
Timestamp: 2024-01-15T10:30:00Z
Total Violations: 1

Violations:

1. message_delivery_failure
   Severity: CRITICAL
   Current Value: ERROR
   Threshold: N/A
   Message: Message delivery failed: Connection timeout
```

### 3. Slack Notifications

Post alerts to a Slack channel via webhook.

**Setup Steps:**

1. Create a Slack webhook:
   - Go to https://api.slack.com/apps
   - Create a new app or select existing
   - Enable "Incoming Webhooks"
   - Add webhook to your workspace
   - Copy the webhook URL

2. Configure in settings:

```python
AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'notification_channels': ['log', 'slack'],  # Add 'slack'
    
    'slack': {
        'enabled': True,
        'webhook_url': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
        'channel': '#ai-agent-alerts',
    },
}
```

**Slack Message Format:**

```
🚨 AI Agent Platform Alert: 1 Violation(s)
Timestamp: 2024-01-15T10:30:00Z

🔴 message_delivery_failure
Severity: CRITICAL
Current: ERROR
Threshold: N/A
Message: Message delivery failed: Connection timeout
```

### 4. Webhook Notifications

Send alerts to a custom monitoring system or webhook endpoint.

**Configuration:**

```python
AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'notification_channels': ['log', 'webhook'],  # Add 'webhook'
    
    'webhook': {
        'enabled': True,
        'url': 'https://your-monitoring-system.com/api/alerts',
        'method': 'POST',
        'headers': {
            'Authorization': 'Bearer YOUR_API_TOKEN',
            'Content-Type': 'application/json',
        },
    },
}
```

**Webhook Payload:**

```json
{
  "event": "threshold_violation",
  "timestamp": "2024-01-15T10:30:00Z",
  "violation_count": 1,
  "violations": [
    {
      "metric": "message_delivery_failure",
      "current_value": "ERROR",
      "threshold": "N/A",
      "severity": "critical",
      "message": "Message delivery failed: Connection timeout",
      "context": {
        "message_id": "msg-123",
        "sender_id": "agent-456",
        "recipient_id": "agent-789",
        "correlation_id": "corr-001"
      }
    }
  ]
}
```

## Configuration Examples

### Production Setup (Email + Slack)

```python
# settings/production.py

AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'check_interval': 60,
    'notification_channels': ['log', 'email', 'slack'],
    
    'email': {
        'enabled': True,
        'recipients': [
            'platform-admin@company.com',
            'ops-team@company.com',
        ],
        'subject_prefix': '[PROD Alert]',
    },
    
    'slack': {
        'enabled': True,
        'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
        'channel': '#prod-alerts',
    },
    
    'webhook': {
        'enabled': False,
    },
}
```

### Development Setup (Log Only)

```python
# settings/development.py

AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'notification_channels': ['log'],  # Log only in development
    
    'email': {
        'enabled': False,
    },
    
    'slack': {
        'enabled': False,
    },
    
    'webhook': {
        'enabled': False,
    },
}
```

### Staging Setup (Slack Only)

```python
# settings/staging.py

AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'notification_channels': ['log', 'slack'],
    
    'email': {
        'enabled': False,
    },
    
    'slack': {
        'enabled': True,
        'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
        'channel': '#staging-alerts',
    },
    
    'webhook': {
        'enabled': False,
    },
}
```

## Testing the Notification System

### 1. Run the Test Suite

```bash
cd linkup
python test_admin_notification_system.py
```

This verifies:
- Critical error detection
- Alert triggering for critical errors
- Non-critical errors don't trigger alerts
- Multi-channel delivery
- Configuration structure
- Resilience to alerting failures

### 2. Manual Testing

#### Test Email Notifications

```python
from ai_agents.alerting_service import AlertingService

violations = [{
    'metric': 'test_alert',
    'current_value': 'TEST',
    'threshold': 'N/A',
    'severity': 'critical',
    'message': 'This is a test alert'
}]

result = AlertingService.trigger_alerts(violations)
print(result)
```

#### Test via ErrorLogger

```python
from ai_agents.error_logger import ErrorLogger

# This will trigger an alert
ErrorLogger.log_message_delivery_failure(
    message_id='test-msg-123',
    sender_id='test-agent-1',
    recipient_id='test-agent-2',
    error_details='Test alert - please ignore',
    correlation_id='test-corr-001'
)
```

### 3. Verify Configuration

```bash
python manage.py shell
```

```python
from django.conf import settings

# Check configuration
config = settings.AI_AGENT_ALERT_CONFIG
print("Enabled:", config['enabled'])
print("Channels:", config['notification_channels'])
print("Email enabled:", config['email']['enabled'])
print("Slack enabled:", config['slack']['enabled'])
```

## Monitoring and Maintenance

### Check Alert Logs

```bash
# View recent alerts
tail -f logs/ai_agents.log | grep -i "THRESHOLD VIOLATION\|CRITICAL"

# Search for specific error types
grep "message_delivery_failure" logs/ai_agents.log
```

### Alert History API

```bash
# Get recent alerts
curl http://localhost:8000/api/health/alerts?limit=10

# Check current system health
curl http://localhost:8000/api/health
```

### Troubleshooting

#### Alerts Not Being Sent

1. **Check alerting is enabled:**
   ```python
   AI_AGENT_ALERT_CONFIG['enabled'] = True
   ```

2. **Verify channels are configured:**
   ```python
   AI_AGENT_ALERT_CONFIG['notification_channels'] = ['log', 'email']
   ```

3. **Check logs for errors:**
   ```bash
   grep -i "error.*alert" logs/ai_agents.log
   ```

#### Email Alerts Not Working

1. Verify Django email settings (EMAIL_HOST, EMAIL_PORT, etc.)
2. Check email configuration in AI_AGENT_ALERT_CONFIG
3. Ensure DEFAULT_FROM_EMAIL is set
4. Test email manually:
   ```bash
   python manage.py shell
   from django.core.mail import send_mail
   send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
   ```

#### Slack Alerts Not Working

1. Verify webhook URL is correct
2. Test webhook manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     YOUR_WEBHOOK_URL
   ```
3. Check Slack app permissions

## Best Practices

1. **Use Multiple Channels** - Configure at least 2 channels for redundancy
2. **Test Regularly** - Run test alerts monthly to ensure system works
3. **Monitor Alert Volume** - If too many alerts, review what's marked as critical
4. **Secure Credentials** - Use environment variables for sensitive data:
   ```python
   'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
   ```
5. **Different Configs per Environment** - Use separate settings files for dev/staging/prod
6. **Document Recipients** - Keep a list of who receives alerts and why
7. **Alert Escalation** - Have a process for unacknowledged critical alerts

## Integration with ErrorLogger

The ErrorLogger automatically integrates with the notification system. When you log critical errors, notifications are sent automatically:

```python
from ai_agents.error_logger import ErrorLogger

# These automatically trigger notifications:
ErrorLogger.log_message_delivery_failure(...)
ErrorLogger.log_websocket_connection_failure(...)
ErrorLogger.log_system_error(..., severity='critical')
ErrorLogger.log_api_key_generation(..., success=False)

# These do NOT trigger notifications:
ErrorLogger.log_authentication_failure(...)
ErrorLogger.log_rate_limit_violation(...)
ErrorLogger.log_validation_error(...)
ErrorLogger.log_system_error(..., severity='warning')
```

## Related Documentation

- [Alerting System README](ALERTING_README.md) - Complete alerting system documentation
- [Error Logger Documentation](error_logger.py) - ErrorLogger API reference
- [System Health Monitoring](../TASK_14_3_IMPLEMENTATION_SUMMARY.md) - Health monitoring overview

## Support

For issues or questions:
1. Check logs: `logs/ai_agents.log`
2. Run test suite: `python test_admin_notification_system.py`
3. Review configuration: `settings/base.py` or `settings/production.py`
4. Consult [ALERTING_README.md](ALERTING_README.md) for detailed troubleshooting

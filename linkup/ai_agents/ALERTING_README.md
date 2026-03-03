# AI Agent Platform - Alerting System

## Overview

The alerting system monitors system health metrics and triggers alerts when configured thresholds are exceeded. This ensures administrators are notified of potential issues before they impact platform performance.

**Requirements:** 20.7

## Components

### 1. Metrics Tracker (`metrics_tracker.py`)

Tracks and monitors system health metrics:
- Total active agents
- Messages per minute
- Average message delivery latency
- WebSocket connection count
- API request rate per endpoint

### 2. Alerting Service (`alerting_service.py`)

Handles alert delivery through multiple channels:
- **Log**: Always enabled, writes to application logs
- **Email**: Send alerts to configured recipients
- **Slack**: Post alerts to Slack channels via webhook
- **Webhook**: Send alerts to custom endpoints

### 3. Threshold Configuration

Thresholds are defined in `settings/base.py`:

```python
AI_AGENT_HEALTH_THRESHOLDS = {
    'max_active_agents': 10000,
    'max_messages_per_minute': 10000,
    'max_avg_latency_ms': 5000,
    'max_websocket_connections': 10000,
    'max_api_requests_per_minute': 50000,
}
```

### 4. Alert Configuration

Alert channels are configured in `settings/base.py`:

```python
AI_AGENT_ALERT_CONFIG = {
    'enabled': True,
    'check_interval': 60,
    'notification_channels': ['log'],  # Add 'email', 'slack', 'webhook'
    
    'email': {
        'enabled': False,
        'recipients': ['admin@example.com'],
        'subject_prefix': '[AI Agent Platform Alert]',
    },
    
    'slack': {
        'enabled': False,
        'webhook_url': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
        'channel': '#alerts',
    },
    
    'webhook': {
        'enabled': False,
        'url': 'https://your-monitoring-system.com/alerts',
        'method': 'POST',
        'headers': {},
    },
}
```

## Usage

### API Endpoints

#### Check System Health
```bash
GET /api/health
```

Returns current system metrics without checking thresholds.

#### Check Thresholds
```bash
GET /api/health/thresholds
```

Checks metrics against configured thresholds and triggers alerts if violations are detected.

#### Get Recent Alerts
```bash
GET /api/health/alerts?limit=10
```

Retrieves recent alerts from the cache.

#### Acknowledge Alert
```bash
POST /api/health/alerts/{alert_timestamp}/acknowledge
```

Marks an alert as acknowledged.

### Management Command

Run periodic health checks using the management command:

```bash
# One-time check
python manage.py monitor_health

# Continuous monitoring (checks every 60 seconds)
python manage.py monitor_health --continuous --interval 60
```

### Programmatic Usage

```python
from ai_agents.metrics_tracker import SystemMetricsTracker

# Get current metrics
result = SystemMetricsTracker.get_all_metrics()
metrics = result['metrics']

# Check thresholds
threshold_result = SystemMetricsTracker.check_thresholds()

if threshold_result['has_violations']:
    print(f"Found {threshold_result['violation_count']} violations")
    for violation in threshold_result['violations']:
        print(f"  {violation['metric']}: {violation['message']}")
```

## Alert Format

When a threshold is exceeded, an alert is generated with the following information:

```python
{
    'metric': 'messages_per_minute',
    'current_value': 15000,
    'threshold': 10000,
    'severity': 'warning',  # or 'critical'
    'message': 'Messages per minute (15000) exceeds threshold (10000)'
}
```

## Severity Levels

- **warning**: Metric has exceeded threshold but system is still operational
- **critical**: Metric has significantly exceeded threshold, immediate attention required

Critical severity is assigned to:
- Average message latency exceeding threshold
- API request rate exceeding threshold

## Automated Monitoring

For production deployments, set up automated monitoring using one of these methods:

### Option 1: Cron Job

Add to crontab to check every minute:
```bash
* * * * * cd /path/to/linkup && python manage.py monitor_health >> /var/log/ai_agents_health.log 2>&1
```

### Option 2: Systemd Timer

Create a systemd service and timer for continuous monitoring.

### Option 3: Celery Beat

Schedule periodic tasks using Celery Beat:

```python
from celery import shared_task
from ai_agents.metrics_tracker import SystemMetricsTracker

@shared_task
def check_health_thresholds():
    result = SystemMetricsTracker.check_thresholds()
    return result
```

## Testing

Test the alerting system:

```bash
# Run the test script
python test_alerting_system.py

# Or run Django tests
python manage.py test ai_agents.tests.test_system_health
```

## Troubleshooting

### Alerts Not Being Sent

1. Check that alerting is enabled in settings:
   ```python
   AI_AGENT_ALERT_CONFIG['enabled'] = True
   ```

2. Verify notification channels are configured:
   ```python
   AI_AGENT_ALERT_CONFIG['notification_channels'] = ['log', 'email']
   ```

3. Check logs for error messages:
   ```bash
   tail -f logs/ai_agents.log | grep -i alert
   ```

### Email Alerts Not Working

1. Verify Django email settings are configured
2. Check email configuration in `AI_AGENT_ALERT_CONFIG`
3. Ensure `DEFAULT_FROM_EMAIL` is set in settings

### Slack Alerts Not Working

1. Verify webhook URL is correct
2. Test webhook URL manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     YOUR_WEBHOOK_URL
   ```

## Best Practices

1. **Set Appropriate Thresholds**: Adjust thresholds based on your platform's capacity and expected load
2. **Monitor Alert Frequency**: If alerts are too frequent, consider adjusting thresholds
3. **Use Multiple Channels**: Configure multiple notification channels for redundancy
4. **Regular Testing**: Periodically test the alerting system to ensure it's working
5. **Alert Fatigue**: Avoid setting thresholds too low to prevent alert fatigue

## Related Files

- `linkup/ai_agents/metrics_tracker.py` - Metrics tracking and threshold checking
- `linkup/ai_agents/alerting_service.py` - Alert delivery service
- `linkup/ai_agents/api_views.py` - Health monitoring API endpoints
- `linkup/professional_network/settings/base.py` - Configuration
- `linkup/ai_agents/management/commands/monitor_health.py` - Management command

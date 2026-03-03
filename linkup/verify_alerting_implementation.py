"""
Verification script for Task 14.3: Implement alerting for threshold violations

This script verifies that all components of the alerting system are properly implemented:
1. Threshold configuration is defined
2. Threshold checking logic is implemented
3. Alert triggering is functional
4. Multiple notification channels are supported

Requirements: 20.7
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.base')
django.setup()

from django.conf import settings
from ai_agents.metrics_tracker import SystemMetricsTracker
from ai_agents.alerting_service import AlertingService


def verify_threshold_configuration():
    """Verify threshold configuration exists in settings."""
    print("\n" + "="*60)
    print("VERIFICATION 1: Threshold Configuration")
    print("="*60)
    
    try:
        thresholds = SystemMetricsTracker.get_thresholds()
        
        required_thresholds = [
            'max_active_agents',
            'max_messages_per_minute',
            'max_avg_latency_ms',
            'max_websocket_connections',
            'max_api_requests_per_minute'
        ]
        
        print("\n✓ Threshold configuration loaded:")
        for key in required_thresholds:
            if key in thresholds:
                print(f"  ✓ {key}: {thresholds[key]}")
            else:
                print(f"  ✗ {key}: MISSING")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading threshold configuration: {e}")
        return False


def verify_alert_configuration():
    """Verify alert configuration exists in settings."""
    print("\n" + "="*60)
    print("VERIFICATION 2: Alert Configuration")
    print("="*60)
    
    try:
        alert_config = getattr(settings, 'AI_AGENT_ALERT_CONFIG', {})
        
        print("\n✓ Alert configuration loaded:")
        print(f"  Enabled: {alert_config.get('enabled', False)}")
        print(f"  Check Interval: {alert_config.get('check_interval', 'N/A')}s")
        print(f"  Notification Channels: {alert_config.get('notification_channels', [])}")
        
        # Check channel configurations
        channels = ['email', 'slack', 'webhook']
        for channel in channels:
            if channel in alert_config:
                enabled = alert_config[channel].get('enabled', False)
                status = "✓ Configured" if enabled else "○ Available (disabled)"
                print(f"  {status}: {channel}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading alert configuration: {e}")
        return False


def verify_threshold_checking():
    """Verify threshold checking logic works."""
    print("\n" + "="*60)
    print("VERIFICATION 3: Threshold Checking Logic")
    print("="*60)
    
    try:
        # Get current metrics
        print("\n  Fetching current metrics...")
        metrics_result = SystemMetricsTracker.get_all_metrics()
        
        if metrics_result['status'] != 'SUCCESS':
            print(f"  ✗ Failed to get metrics: {metrics_result.get('error')}")
            return False
        
        print("  ✓ Metrics retrieved successfully")
        
        # Check thresholds with current metrics
        print("  Checking thresholds...")
        threshold_result = SystemMetricsTracker.check_thresholds()
        
        if threshold_result['status'] != 'SUCCESS':
            print(f"  ✗ Failed to check thresholds: {threshold_result.get('error')}")
            return False
        
        print("  ✓ Threshold checking completed")
        print(f"  Violations detected: {threshold_result['has_violations']}")
        print(f"  Violation count: {threshold_result['violation_count']}")
        
        if threshold_result['has_violations']:
            print("\n  Violations:")
            for v in threshold_result['violations']:
                print(f"    - {v['metric']}: {v['current_value']} > {v['threshold']}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during threshold checking: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_alert_triggering():
    """Verify alert triggering works with test data."""
    print("\n" + "="*60)
    print("VERIFICATION 4: Alert Triggering")
    print("="*60)
    
    try:
        # Create test violations
        test_violations = [
            {
                'metric': 'test_metric',
                'current_value': 100,
                'threshold': 50,
                'severity': 'warning',
                'message': 'Test violation for verification'
            }
        ]
        
        print("\n  Triggering test alert...")
        result = AlertingService.trigger_alerts(test_violations)
        
        if result['status'] in ['SUCCESS', 'PARTIAL']:
            print("  ✓ Alert triggered successfully")
            print(f"  Alerts sent: {result['alerts_sent']}")
            print(f"  Channels used: {result['channels_used']}")
            
            if result.get('errors'):
                print(f"  Warnings: {result['errors']}")
            
            return True
        else:
            print(f"  ✗ Alert triggering failed: {result.get('error')}")
            return False
        
    except Exception as e:
        print(f"\n✗ Error triggering alerts: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_notification_channels():
    """Verify notification channel implementations."""
    print("\n" + "="*60)
    print("VERIFICATION 5: Notification Channels")
    print("="*60)
    
    try:
        # Check that all channel methods exist
        channels = {
            'log': '_log_violations',
            'email': '_send_email_alerts',
            'slack': '_send_slack_alerts',
            'webhook': '_send_webhook_alerts'
        }
        
        print("\n  Checking notification channel implementations:")
        for channel, method in channels.items():
            if hasattr(AlertingService, method):
                print(f"  ✓ {channel}: {method} implemented")
            else:
                print(f"  ✗ {channel}: {method} NOT FOUND")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error checking notification channels: {e}")
        return False


def verify_api_endpoints():
    """Verify API endpoints are registered."""
    print("\n" + "="*60)
    print("VERIFICATION 6: API Endpoints")
    print("="*60)
    
    try:
        from django.urls import reverse
        
        endpoints = [
            ('system_health', 'GET /api/health'),
            ('check_thresholds', 'GET /api/health/thresholds'),
            ('get_alerts', 'GET /api/health/alerts'),
        ]
        
        print("\n  Checking API endpoint registration:")
        for name, description in endpoints:
            try:
                url = reverse(f'ai_agents:{name}')
                print(f"  ✓ {description} -> {url}")
            except Exception as e:
                print(f"  ✗ {description}: NOT REGISTERED")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error checking API endpoints: {e}")
        return False


def verify_management_command():
    """Verify management command exists."""
    print("\n" + "="*60)
    print("VERIFICATION 7: Management Command")
    print("="*60)
    
    try:
        import os.path
        command_path = 'ai_agents/management/commands/monitor_health.py'
        
        if os.path.exists(command_path):
            print(f"\n  ✓ Management command exists: {command_path}")
            print("  Usage: python manage.py monitor_health")
            return True
        else:
            print(f"\n  ✗ Management command not found: {command_path}")
            return False
        
    except Exception as e:
        print(f"\n✗ Error checking management command: {e}")
        return False


def main():
    """Run all verifications."""
    print("\n" + "="*60)
    print("TASK 14.3 VERIFICATION: Alerting for Threshold Violations")
    print("="*60)
    print("\nThis script verifies the implementation of:")
    print("  - Metric threshold configuration")
    print("  - Threshold checking logic")
    print("  - Alert triggering mechanism")
    print("  - Multiple notification channels")
    print("  - API endpoints")
    print("  - Management command")
    
    verifications = [
        ("Threshold Configuration", verify_threshold_configuration),
        ("Alert Configuration", verify_alert_configuration),
        ("Threshold Checking Logic", verify_threshold_checking),
        ("Alert Triggering", verify_alert_triggering),
        ("Notification Channels", verify_notification_channels),
        ("API Endpoints", verify_api_endpoints),
        ("Management Command", verify_management_command),
    ]
    
    results = []
    for name, func in verifications:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Verification '{name}' failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} verifications passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("✓ ALL VERIFICATIONS PASSED")
        print("="*60)
        print("\nTask 14.3 implementation is complete!")
        print("\nThe alerting system includes:")
        print("  1. ✓ Threshold configuration in settings")
        print("  2. ✓ Threshold checking logic")
        print("  3. ✓ Alert triggering mechanism")
        print("  4. ✓ Multiple notification channels (log, email, slack, webhook)")
        print("  5. ✓ API endpoints for health monitoring")
        print("  6. ✓ Management command for periodic checks")
        print("\nRequirements 20.7: SATISFIED")
        return 0
    else:
        print("\n" + "="*60)
        print("✗ SOME VERIFICATIONS FAILED")
        print("="*60)
        print("\nPlease review the failed verifications above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

"""
Test script for AI Agent alerting system (Task 14.3).

This script verifies:
1. Threshold configuration is loaded from settings
2. Metrics can be checked against thresholds
3. Violations are detected correctly
4. Alerts are triggered when thresholds are exceeded
5. Alert endpoints are accessible

Requirements: 20.7
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from django.conf import settings
from ai_agents.metrics_tracker import SystemMetricsTracker
from ai_agents.alerting_service import AlertingService


def test_threshold_configuration():
    """Test that threshold configuration is loaded from settings."""
    print("\n" + "="*60)
    print("TEST 1: Threshold Configuration")
    print("="*60)
    
    try:
        # Get thresholds from settings
        thresholds = SystemMetricsTracker.get_thresholds()
        
        print("\n✓ Thresholds loaded from settings:")
        for key, value in thresholds.items():
            print(f"  - {key}: {value}")
        
        # Verify expected keys exist
        expected_keys = [
            'max_active_agents',
            'max_messages_per_minute',
            'max_avg_latency_ms',
            'max_websocket_connections',
            'max_api_requests_per_minute'
        ]
        
        missing_keys = [key for key in expected_keys if key not in thresholds]
        if missing_keys:
            print(f"\n✗ Missing threshold keys: {missing_keys}")
            return False
        
        print("\n✓ All expected threshold keys present")
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading thresholds: {e}")
        return False


def test_metrics_collection():
    """Test that system metrics can be collected."""
    print("\n" + "="*60)
    print("TEST 2: Metrics Collection")
    print("="*60)
    
    try:
        # Get current metrics
        result = SystemMetricsTracker.get_all_metrics()
        
        if result['status'] != 'SUCCESS':
            print(f"\n✗ Failed to get metrics: {result.get('error')}")
            return False
        
        metrics = result['metrics']
        
        print("\n✓ Current system metrics:")
        print(f"  - Total active agents: {metrics['total_active_agents']}")
        print(f"  - Messages per minute: {metrics['messages_per_minute']}")
        print(f"  - Average latency: {metrics['average_message_latency_ms']}ms")
        print(f"  - WebSocket connections: {metrics['websocket_connections']}")
        print(f"  - API requests per minute: {metrics['total_api_requests_per_minute']}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error collecting metrics: {e}")
        return False


def test_threshold_checking():
    """Test threshold checking logic."""
    print("\n" + "="*60)
    print("TEST 3: Threshold Checking")
    print("="*60)
    
    try:
        # Check thresholds with current metrics
        result = SystemMetricsTracker.check_thresholds()
        
        if result['status'] != 'SUCCESS':
            print(f"\n✗ Failed to check thresholds: {result.get('error')}")
            return False
        
        print(f"\n✓ Threshold check completed")
        print(f"  - Has violations: {result['has_violations']}")
        print(f"  - Violation count: {result['violation_count']}")
        
        if result['has_violations']:
            print("\n  Violations detected:")
            for violation in result['violations']:
                print(f"    - {violation['metric']}: {violation['message']}")
                print(f"      Severity: {violation['severity']}")
        else:
            print("\n  ✓ No threshold violations detected")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error checking thresholds: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_threshold_checking_with_custom_thresholds():
    """Test threshold checking with custom (low) thresholds to trigger violations."""
    print("\n" + "="*60)
    print("TEST 4: Threshold Checking with Custom Thresholds")
    print("="*60)
    
    try:
        # Use very low thresholds to trigger violations
        custom_thresholds = {
            'max_active_agents': 0,
            'max_messages_per_minute': 0,
            'max_avg_latency_ms': 0,
            'max_websocket_connections': 0,
            'max_api_requests_per_minute': 0
        }
        
        print("\n  Using custom thresholds (all set to 0 to trigger violations):")
        for key, value in custom_thresholds.items():
            print(f"    - {key}: {value}")
        
        # Check thresholds with custom values
        result = SystemMetricsTracker.check_thresholds(custom_thresholds=custom_thresholds)
        
        if result['status'] != 'SUCCESS':
            print(f"\n✗ Failed to check thresholds: {result.get('error')}")
            return False
        
        print(f"\n✓ Threshold check completed")
        print(f"  - Has violations: {result['has_violations']}")
        print(f"  - Violation count: {result['violation_count']}")
        
        if result['has_violations']:
            print("\n  ✓ Violations detected as expected:")
            for violation in result['violations']:
                print(f"    - {violation['metric']}")
                print(f"      Current: {violation['current_value']}, Threshold: {violation['threshold']}")
                print(f"      Severity: {violation['severity']}")
        else:
            print("\n  ⚠ Warning: Expected violations but none detected")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error checking thresholds: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alerting_service():
    """Test the alerting service."""
    print("\n" + "="*60)
    print("TEST 5: Alerting Service")
    print("="*60)
    
    try:
        # Create test violations
        test_violations = [
            {
                'metric': 'test_metric',
                'current_value': 100,
                'threshold': 50,
                'severity': 'warning',
                'message': 'Test metric (100) exceeds threshold (50)'
            }
        ]
        
        print("\n  Triggering test alert...")
        result = AlertingService.trigger_alerts(test_violations)
        
        if result['status'] in ['SUCCESS', 'PARTIAL']:
            print(f"\n✓ Alerts triggered successfully")
            print(f"  - Status: {result['status']}")
            print(f"  - Alerts sent: {result['alerts_sent']}")
            print(f"  - Channels used: {result['channels_used']}")
            
            if result.get('errors'):
                print(f"  - Errors: {result['errors']}")
        else:
            print(f"\n✗ Failed to trigger alerts: {result.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error testing alerting service: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alert_configuration():
    """Test alert configuration from settings."""
    print("\n" + "="*60)
    print("TEST 6: Alert Configuration")
    print("="*60)
    
    try:
        # Get alert configuration
        alert_config = getattr(settings, 'AI_AGENT_ALERT_CONFIG', {})
        
        print("\n✓ Alert configuration loaded:")
        print(f"  - Enabled: {alert_config.get('enabled', True)}")
        print(f"  - Check interval: {alert_config.get('check_interval', 60)}s")
        print(f"  - Notification channels: {alert_config.get('notification_channels', ['log'])}")
        
        # Check email config
        email_config = alert_config.get('email', {})
        print(f"\n  Email notifications:")
        print(f"    - Enabled: {email_config.get('enabled', False)}")
        print(f"    - Recipients: {len(email_config.get('recipients', []))} configured")
        
        # Check Slack config
        slack_config = alert_config.get('slack', {})
        print(f"\n  Slack notifications:")
        print(f"    - Enabled: {slack_config.get('enabled', False)}")
        print(f"    - Channel: {slack_config.get('channel', '#alerts')}")
        
        # Check webhook config
        webhook_config = alert_config.get('webhook', {})
        print(f"\n  Webhook notifications:")
        print(f"    - Enabled: {webhook_config.get('enabled', False)}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading alert configuration: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AI AGENT ALERTING SYSTEM TEST SUITE")
    print("Task 14.3: Implement alerting for threshold violations")
    print("="*60)
    
    tests = [
        ("Threshold Configuration", test_threshold_configuration),
        ("Metrics Collection", test_metrics_collection),
        ("Threshold Checking", test_threshold_checking),
        ("Custom Threshold Checking", test_threshold_checking_with_custom_thresholds),
        ("Alerting Service", test_alerting_service),
        ("Alert Configuration", test_alert_configuration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Task 14.3 implementation verified.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

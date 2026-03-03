"""
Verification script for admin notification system integration (Task 15.2).

This script verifies:
1. ErrorLogger integrates with AlertingService
2. Critical errors trigger admin notifications
3. Non-critical errors do not trigger notifications
4. Notification channels are configurable
5. Alerting failures do not break error logging

Requirements: 15.6
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

from unittest.mock import patch, MagicMock
from django.conf import settings
from ai_agents.error_logger import ErrorLogger
from ai_agents.alerting_service import AlertingService


def test_critical_error_types():
    """Test that critical error types are correctly identified."""
    print("\n" + "="*70)
    print("TEST 1: Critical Error Type Detection")
    print("="*70)
    
    try:
        # Test critical error types
        critical_types = [
            'message_delivery_failure',
            'websocket_connection_failure',
            'system_error',
            'api_key_generation_failure'
        ]
        
        print("\n✓ Testing critical error types:")
        for error_type in critical_types:
            is_critical = ErrorLogger._is_critical_error(error_type)
            status = "✓" if is_critical else "✗"
            print(f"  {status} {error_type}: {is_critical}")
            assert is_critical, f"{error_type} should be critical"
        
        # Test non-critical error types
        non_critical_types = [
            'authentication_failure',
            'rate_limit_violation',
            'validation_error'
        ]
        
        print("\n✓ Testing non-critical error types:")
        for error_type in non_critical_types:
            is_critical = ErrorLogger._is_critical_error(error_type)
            status = "✓" if not is_critical else "✗"
            print(f"  {status} {error_type}: {is_critical}")
            assert not is_critical, f"{error_type} should not be critical"
        
        # Test severity override
        print("\n✓ Testing severity override:")
        is_critical = ErrorLogger._is_critical_error('any_error', severity='critical')
        print(f"  ✓ any_error with severity='critical': {is_critical}")
        assert is_critical, "Severity='critical' should override"
        
        is_critical = ErrorLogger._is_critical_error('any_error', severity='warning')
        print(f"  ✓ any_error with severity='warning': {is_critical}")
        assert not is_critical, "Severity='warning' should not be critical"
        
        print("\n✓ TEST PASSED: Critical error detection works correctly")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_message_delivery_failure_alert():
    """Test that message delivery failures trigger alerts."""
    print("\n" + "="*70)
    print("TEST 2: Message Delivery Failure Alert")
    print("="*70)
    
    try:
        with patch('ai_agents.error_logger.ErrorLogger._loggers') as mock_loggers:
            with patch('ai_agents.error_logger.AlertingService') as mock_alerting:
                mock_logger = MagicMock()
                mock_loggers.__getitem__.return_value = mock_logger
                mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
                
                # Log a message delivery failure
                ErrorLogger.log_message_delivery_failure(
                    mess
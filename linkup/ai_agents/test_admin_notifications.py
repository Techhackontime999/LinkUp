"""
Unit tests for admin notification system integration with error logging.

Tests that critical errors trigger admin notifications through configured channels.

Requirements: 15.6
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

import unittest
from unittest.mock import patch, MagicMock, call
from ai_agents.error_logger import ErrorLogger


class TestAdminNotifications(unittest.TestCase):
    """Test cases for admin notification system."""
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_message_delivery_failure_triggers_alert(self, mock_alerting, mock_loggers):
        """Test that message delivery failures trigger admin notifications."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        message_id = 'msg-123'
        sender_id = 'agent-1'
        recipient_id = 'agent-2'
        error_details = 'WebSocket connection failed'
        
        ErrorLogger.log_message_delivery_failure(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            error_details=error_details
        )
        
        # Verify alert was triggered
        mock_alerting.trigger_alerts.assert_called_once()
        
        # Check alert content
        call_args = mock_alerting.trigger_alerts.call_args[0][0]
        self.assertEqual(len(call_args), 1)
        violation = call_args[0]
        
        self.assertEqual(violation['metric'], 'message_delivery_failure')
        self.assertEqual(violation['severity'], 'critical')
        self.assertIn('Message delivery failed', violation['message'])
        self.assertIn(message_id, violation['context']['message_id'])
        self.assertIn(sender_id, violation['context']['sender_id'])
        self.assertIn(recipient_id, violation['context']['recipient_id'])
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_websocket_failure_triggers_alert(self, mock_alerting, mock_loggers):
        """Test that WebSocket connection failures trigger admin notifications."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        agent_id = 'agent-123'
        error_details = 'Connection timeout'
        
        ErrorLogger.log_websocket_connection_failure(
            agent_id=agent_id,
            error_details=error_details
        )
        
        # Verify alert was triggered
        mock_alerting.trigger_alerts.assert_called_once()
        
        # Check alert content
        call_args = mock_alerting.trigger_alerts.call_args[0][0]
        violation = call_args[0]
        
        self.assertEqual(violation['metric'], 'websocket_connection_failure')
        self.assertEqual(violation['severity'], 'critical')
        self.assertIn('WebSocket connection failed', violation['message'])
        self.assertIn(agent_id, violation['context']['agent_id'])
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_critical_system_error_triggers_alert(self, mock_alerting, mock_loggers):
        """Test that critical system errors trigger admin notifications."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        error_type = 'database_connection_lost'
        error_message = 'Unable to connect to database'
        component = 'AgentRegistry'
        
        ErrorLogger.log_system_error(
            error_type=error_type,
            error_message=error_message,
            component=component,
            severity='critical'
        )
        
        # Verify alert was triggered
        mock_alerting.trigger_alerts.assert_called_once()
        
        # Check alert content
        call_args = mock_alerting.trigger_alerts.call_args[0][0]
        violation = call_args[0]
        
        self.assertEqual(violation['metric'], 'system_error')
        self.assertEqual(violation['severity'], 'critical')
        self.assertIn(component, violation['message'])
        self.assertIn(error_message, violation['message'])
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_non_critical_system_error_no_alert(self, mock_alerting, mock_loggers):
        """Test that non-critical system errors do not trigger notifications."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        ErrorLogger.log_system_error(
            error_type='cache_miss',
            error_message='Cache key not found',
            component='RateLimiter',
            severity='warning'
        )
        
        # Verify alert was NOT triggered
        mock_alerting.trigger_alerts.assert_not_called()
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_api_key_generation_failure_triggers_alert(self, mock_alerting, mock_loggers):
        """Test that API key generation failures trigger admin notifications."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        agent_id = 'agent-456'
        
        ErrorLogger.log_api_key_generation(
            agent_id=agent_id,
            success=False
        )
        
        # Verify alert was triggered
        mock_alerting.trigger_alerts.assert_called_once()
        
        # Check alert content
        call_args = mock_alerting.trigger_alerts.call_args[0][0]
        violation = call_args[0]
        
        self.assertEqual(violation['metric'], 'api_key_generation_failure')
        self.assertEqual(violation['severity'], 'critical')
        self.assertIn('API key generation failed', violation['message'])
        self.assertIn(agent_id, violation['context']['agent_id'])
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_api_key_generation_success_no_alert(self, mock_alerting, mock_loggers):
        """Test that successful API key generation does not trigger notifications."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        ErrorLogger.log_api_key_generation(
            agent_id='agent-789',
            success=True
        )
        
        # Verify alert was NOT triggered
        mock_alerting.trigger_alerts.assert_not_called()
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_authentication_failure_no_alert(self, mock_alerting, mock_loggers):
        """Test that authentication failures do not trigger notifications (not critical)."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        ErrorLogger.log_authentication_failure(
            agent_id='agent-999',
            reason='Invalid API key'
        )
        
        # Verify alert was NOT triggered (auth failures are not critical)
        mock_alerting.trigger_alerts.assert_not_called()
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_rate_limit_violation_no_alert(self, mock_alerting, mock_loggers):
        """Test that rate limit violations do not trigger notifications (not critical)."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        ErrorLogger.log_rate_limit_violation(
            agent_id='agent-888',
            current_count=1050,
            limit=1000
        )
        
        # Verify alert was NOT triggered (rate limits are not critical)
        mock_alerting.trigger_alerts.assert_not_called()
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_validation_error_no_alert(self, mock_alerting, mock_loggers):
        """Test that validation errors do not trigger notifications (not critical)."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        ErrorLogger.log_validation_error(
            error_type='missing_field',
            error_message='Required field missing',
            request_details={'endpoint': '/api/test'}
        )
        
        # Verify alert was NOT triggered (validation errors are not critical)
        mock_alerting.trigger_alerts.assert_not_called()
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_alerting_failure_does_not_break_logging(self, mock_alerting, mock_loggers):
        """Test that alerting failures do not prevent error logging."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        # Make alerting service raise an exception
        mock_alerting.trigger_alerts = MagicMock(side_effect=Exception('Alerting service down'))
        
        # This should not raise an exception
        try:
            ErrorLogger.log_message_delivery_failure(
                message_id='msg-999',
                sender_id='agent-1',
                recipient_id='agent-2',
                error_details='Test error'
            )
            success = True
        except Exception:
            success = False
        
        # Verify logging still happened
        self.assertTrue(success, "Error logging should succeed even if alerting fails")
        mock_logger.error.assert_called_once()
    
    def test_is_critical_error_detection(self):
        """Test critical error detection logic."""
        # Critical error types
        self.assertTrue(ErrorLogger._is_critical_error('message_delivery_failure'))
        self.assertTrue(ErrorLogger._is_critical_error('websocket_connection_failure'))
        self.assertTrue(ErrorLogger._is_critical_error('system_error'))
        self.assertTrue(ErrorLogger._is_critical_error('api_key_generation_failure'))
        
        # Non-critical error types
        self.assertFalse(ErrorLogger._is_critical_error('authentication_failure'))
        self.assertFalse(ErrorLogger._is_critical_error('rate_limit_violation'))
        self.assertFalse(ErrorLogger._is_critical_error('validation_error'))
        
        # Severity override
        self.assertTrue(ErrorLogger._is_critical_error('any_error', severity='critical'))
        self.assertFalse(ErrorLogger._is_critical_error('any_error', severity='warning'))
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    @patch('ai_agents.error_logger.AlertingService')
    def test_alert_includes_correlation_id(self, mock_alerting, mock_loggers):
        """Test that alerts include correlation IDs for tracing."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        mock_alerting.trigger_alerts = MagicMock(return_value={'status': 'SUCCESS'})
        
        correlation_id = 'test-correlation-123'
        
        ErrorLogger.log_message_delivery_failure(
            message_id='msg-123',
            sender_id='agent-1',
            recipient_id='agent-2',
            error_details='Test error',
            correlation_id=correlation_id
        )
        
        # Check that correlation ID is in alert context
        call_args = mock_alerting.trigger_alerts.call_args[0][0]
        violation = call_args[0]
        
        self.assertEqual(violation['context']['correlation_id'], correlation_id)


def run_tests():
    """Run all tests."""
    print("Running Admin Notification Integration tests...")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAdminNotifications)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

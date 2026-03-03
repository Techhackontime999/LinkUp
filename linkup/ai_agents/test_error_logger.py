"""
Unit tests for centralized error logging service.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
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
from unittest.mock import patch, MagicMock
from ai_agents.error_logger import ErrorLogger


class TestErrorLogger(unittest.TestCase):
    """Test cases for ErrorLogger service."""
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        correlation_id = ErrorLogger.generate_correlation_id()
        
        # Should be a valid UUID string
        self.assertIsInstance(correlation_id, str)
        self.assertEqual(len(correlation_id), 36)  # UUID format: 8-4-4-4-12
        self.assertIn('-', correlation_id)
    
    def test_generate_unique_correlation_ids(self):
        """Test that correlation IDs are unique."""
        id1 = ErrorLogger.generate_correlation_id()
        id2 = ErrorLogger.generate_correlation_id()
        
        self.assertNotEqual(id1, id2)
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    def test_log_authentication_failure(self, mock_loggers):
        """Test authentication failure logging."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        agent_id = 'test-agent-123'
        reason = 'Invalid API key'
        correlation_id = 'test-correlation-id'
        
        ErrorLogger.log_authentication_failure(
            agent_id=agent_id,
            reason=reason,
            correlation_id=correlation_id
        )
        
        # Verify logger was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # Check log message contains key information
        log_message = call_args[0][0]
        self.assertIn(agent_id, log_message)
        self.assertIn(reason, log_message)
        self.assertIn(correlation_id, log_message)
        
        # Check extra data
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['event_type'], 'authentication_failure')
        self.assertEqual(extra_data['agent_id'], agent_id)
        self.assertEqual(extra_data['reason'], reason)
        self.assertEqual(extra_data['correlation_id'], correlation_id)
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    def test_log_message_delivery_failure(self, mock_loggers):
        """Test message delivery failure logging."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        message_id = 'msg-123'
        sender_id = 'agent-1'
        recipient_id = 'agent-2'
        error_details = 'WebSocket connection failed'
        correlation_id = 'test-correlation-id'
        
        ErrorLogger.log_message_delivery_failure(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            error_details=error_details,
            correlation_id=correlation_id
        )
        
        # Verify logger was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        
        # Check log message
        log_message = call_args[0][0]
        self.assertIn(message_id, log_message)
        self.assertIn(sender_id, log_message)
        self.assertIn(recipient_id, log_message)
        self.assertIn(error_details, log_message)
        
        # Check extra data
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['event_type'], 'message_delivery_failure')
        self.assertEqual(extra_data['message_id'], message_id)
        self.assertEqual(extra_data['correlation_id'], correlation_id)
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    def test_log_rate_limit_violation(self, mock_loggers):
        """Test rate limit violation logging."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        agent_id = 'agent-123'
        current_count = 1050
        limit = 1000
        correlation_id = 'test-correlation-id'
        
        ErrorLogger.log_rate_limit_violation(
            agent_id=agent_id,
            current_count=current_count,
            limit=limit,
            correlation_id=correlation_id
        )
        
        # Verify logger was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # Check log message
        log_message = call_args[0][0]
        self.assertIn(agent_id, log_message)
        self.assertIn(str(current_count), log_message)
        self.assertIn(str(limit), log_message)
        
        # Check extra data
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['event_type'], 'rate_limit_violation')
        self.assertEqual(extra_data['agent_id'], agent_id)
        self.assertEqual(extra_data['current_count'], current_count)
        self.assertEqual(extra_data['limit'], limit)
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    def test_log_validation_error(self, mock_loggers):
        """Test validation error logging."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        error_type = 'missing_field'
        error_message = 'Required field "name" is missing'
        request_details = {
            'endpoint': '/api/agents/register',
            'method': 'POST',
            'data': {'description': 'test'}
        }
        correlation_id = 'test-correlation-id'
        
        ErrorLogger.log_validation_error(
            error_type=error_type,
            error_message=error_message,
            request_details=request_details,
            correlation_id=correlation_id
        )
        
        # Verify logger was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # Check log message
        log_message = call_args[0][0]
        self.assertIn(error_type, log_message)
        self.assertIn(error_message, log_message)
        
        # Check extra data
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['event_type'], 'validation_error')
        self.assertEqual(extra_data['error_type'], error_type)
        self.assertEqual(extra_data['request_details'], request_details)
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    def test_auto_generate_correlation_id(self, mock_loggers):
        """Test that correlation ID is auto-generated when not provided."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        ErrorLogger.log_authentication_failure(
            agent_id='test-agent',
            reason='Test reason'
            # No correlation_id provided
        )
        
        # Verify logger was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # Check that correlation_id was auto-generated
        extra_data = call_args[1]['extra']
        self.assertIn('correlation_id', extra_data)
        self.assertIsInstance(extra_data['correlation_id'], str)
        self.assertEqual(len(extra_data['correlation_id']), 36)
    
    @patch('ai_agents.error_logger.ErrorLogger._loggers')
    def test_log_with_additional_context(self, mock_loggers):
        """Test logging with additional context."""
        mock_logger = MagicMock()
        mock_loggers.__getitem__.return_value = mock_logger
        
        additional_context = {
            'user_agent': 'TestAgent/1.0',
            'ip_address': '192.168.1.1'
        }
        
        ErrorLogger.log_authentication_failure(
            agent_id='test-agent',
            reason='Test reason',
            additional_context=additional_context
        )
        
        # Verify additional context is included
        call_args = mock_logger.warning.call_args
        extra_data = call_args[1]['extra']
        self.assertIn('additional_context', extra_data)
        self.assertEqual(extra_data['additional_context'], additional_context)


def run_tests():
    """Run all tests."""
    print("Running ErrorLogger tests...")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestErrorLogger)
    
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

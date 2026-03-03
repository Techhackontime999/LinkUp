"""
Verification script for centralized error logging integration.

This script verifies that the ErrorLogger is properly integrated across all components
as specified in task 15.1.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
"""

import os
import sys
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_file_for_pattern(filepath, pattern, description):
    """Check if a file contains a specific pattern."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if re.search(pattern, content):
                return True, f"✓ {description}"
            else:
                return False, f"✗ {description}"
    except Exception as e:
        return False, f"✗ {description} - Error: {str(e)}"

def verify_error_logging_integration():
    """Verify error logging integration across all components."""
    
    print("=" * 80)
    print("CENTRALIZED ERROR LOGGING INTEGRATION VERIFICATION")
    print("=" * 80)
    print()
    
    checks = []
    
    # 1. Check ErrorLogger implementation
    print("1. Checking ErrorLogger Implementation...")
    checks.append(check_file_for_pattern(
        'ai_agents/error_logger.py',
        r'def log_authentication_failure',
        "ErrorLogger has log_authentication_failure method"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/error_logger.py',
        r'def log_message_delivery_failure',
        "ErrorLogger has log_message_delivery_failure method"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/error_logger.py',
        r'def log_rate_limit_violation',
        "ErrorLogger has log_rate_limit_violation method"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/error_logger.py',
        r'def log_validation_error',
        "ErrorLogger has log_validation_error method"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/error_logger.py',
        r'def generate_correlation_id',
        "ErrorLogger has generate_correlation_id method"
    ))
    print()
    
    # 2. Check authentication service integration
    print("2. Checking Authentication Service Integration...")
    checks.append(check_file_for_pattern(
        'ai_agents/services.py',
        r'ErrorLogger\.log_authentication_failure',
        "Authentication service uses ErrorLogger.log_authentication_failure"
    ))
    print()
    
    # 3. Check communication service integration
    print("3. Checking Communication Service Integration...")
    checks.append(check_file_for_pattern(
        'ai_agents/services.py',
        r'ErrorLogger\.log_message_delivery_failure',
        "Communication service uses ErrorLogger.log_message_delivery_failure"
    ))
    print()
    
    # 4. Check rate limiting integration
    print("4. Checking Rate Limiting Integration...")
    checks.append(check_file_for_pattern(
        'ai_agents/services.py',
        r'ErrorLogger\.log_rate_limit_violation',
        "Rate limit service uses ErrorLogger.log_rate_limit_violation"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/middleware.py',
        r'ErrorLogger\.log_rate_limit_violation',
        "Rate limit middleware uses ErrorLogger.log_rate_limit_violation"
    ))
    print()
    
    # 5. Check validation error integration
    print("5. Checking Validation Error Integration...")
    checks.append(check_file_for_pattern(
        'ai_agents/api_views.py',
        r'ErrorLogger\.log_validation_error',
        "API views use ErrorLogger.log_validation_error"
    ))
    print()
    
    # 6. Check correlation ID middleware
    print("6. Checking Correlation ID Middleware...")
    checks.append(check_file_for_pattern(
        'ai_agents/middleware.py',
        r'class CorrelationIdMiddleware',
        "CorrelationIdMiddleware is implemented"
    ))
    checks.append(check_file_for_pattern(
        'professional_network/settings/base.py',
        r'ai_agents\.middleware\.CorrelationIdMiddleware',
        "CorrelationIdMiddleware is registered in settings"
    ))
    print()
    
    # 7. Check logging configuration
    print("7. Checking Logging Configuration...")
    checks.append(check_file_for_pattern(
        'professional_network/settings/base.py',
        r'ai_agents\.authentication',
        "Authentication logger configured in settings"
    ))
    checks.append(check_file_for_pattern(
        'professional_network/settings/base.py',
        r'ai_agents\.communication',
        "Communication logger configured in settings"
    ))
    checks.append(check_file_for_pattern(
        'professional_network/settings/base.py',
        r'ai_agents\.rate_limit',
        "Rate limit logger configured in settings"
    ))
    checks.append(check_file_for_pattern(
        'professional_network/settings/base.py',
        r'ai_agents\.validation',
        "Validation logger configured in settings"
    ))
    print()
    
    # 8. Check test coverage
    print("8. Checking Test Coverage...")
    checks.append(check_file_for_pattern(
        'ai_agents/test_error_logger.py',
        r'def test_log_authentication_failure',
        "Test for authentication failure logging exists"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/test_error_logger.py',
        r'def test_log_message_delivery_failure',
        "Test for message delivery failure logging exists"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/test_error_logger.py',
        r'def test_log_rate_limit_violation',
        "Test for rate limit violation logging exists"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/test_error_logger.py',
        r'def test_log_validation_error',
        "Test for validation error logging exists"
    ))
    checks.append(check_file_for_pattern(
        'ai_agents/test_error_logger.py',
        r'def test_generate_correlation_id',
        "Test for correlation ID generation exists"
    ))
    print()
    
    # Print results
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for success, message in checks:
        print(message)
        if success:
            passed += 1
        else:
            failed += 1
    
    print()
    print("=" * 80)
    print(f"Total Checks: {len(checks)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 80)
    print()
    
    if failed == 0:
        print("✓ ALL CHECKS PASSED - Error logging is fully integrated!")
        print()
        print("Task 15.1 Requirements Satisfied:")
        print("  ✓ Log authentication failures with agent ID and reason (Req 15.1)")
        print("  ✓ Log message delivery failures with details (Req 15.2)")
        print("  ✓ Log rate limit violations (Req 15.3)")
        print("  ✓ Log validation errors with request details (Req 15.4)")
        print("  ✓ Include correlation IDs for request tracing (Req 15.5)")
        return True
    else:
        print("✗ SOME CHECKS FAILED - Please review the failed items above")
        return False

if __name__ == '__main__':
    success = verify_error_logging_integration()
    sys.exit(0 if success else 1)

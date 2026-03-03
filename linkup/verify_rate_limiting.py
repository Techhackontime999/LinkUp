#!/usr/bin/env python
"""
Verification script for AI Agent rate limiting implementation.

This script verifies that:
1. AgentRateLimitService is properly implemented
2. Rate limiting methods work correctly
3. Middleware is properly configured
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')
django.setup()

from ai_agents.services import AgentRateLimitService, AgentRegistryService
from ai_agents.models import AIAgent, AgentAPIKey
from django.core.cache import cache

print("=" * 60)
print("AI AGENT RATE LIMITING VERIFICATION")
print("=" * 60)
print()

# Test 1: Verify AgentRateLimitService exists
print("Test 1: Verify AgentRateLimitService exists")
try:
    assert hasattr(AgentRateLimitService, 'check_rate_limit')
    assert hasattr(AgentRateLimitService, 'increment_rate_limit')
    assert hasattr(AgentRateLimitService, 'reset_rate_limit')
    assert hasattr(AgentRateLimitService, 'get_rate_limit_status')
    print("✓ AgentRateLimitService has all required methods")
except AssertionError as e:
    print(f"✗ AgentRateLimitService missing methods: {e}")
    sys.exit(1)

print()

# Test 2: Create a test agent
print("Test 2: Create test agent")
try:
    # Clean up any existing test agent
    AIAgent.objects.filter(name='RateLimitVerificationAgent').delete()
    
    result = AgentRegistryService.register_agent(
        name='RateLimitVerificationAgent',
        description='Test agent for rate limit verification',
        capabilities={'test': True},
        owner_email='verify@example.com',
        agent_type='CONVERSATIONAL'
    )
    
    if result['status'] != 'SUCCESS':
        print(f"✗ Failed to create test agent: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    agent_id = result['agent_id']
    print(f"✓ Test agent created with ID: {agent_id}")
    
    # Set a low rate limit for testing
    agent = AIAgent.objects.get(id=agent_id)
    api_key = AgentAPIKey.objects.get(agent=agent)
    api_key.rate_limit = 5  # 5 requests per minute
    api_key.save()
    print(f"✓ Rate limit set to {api_key.rate_limit} requests per minute")
    
except Exception as e:
    print(f"✗ Error creating test agent: {e}")
    sys.exit(1)

print()

# Test 3: Check rate limit (should allow)
print("Test 3: Check rate limit (should allow)")
try:
    result = AgentRateLimitService.check_rate_limit(agent_id)
    
    if result['status'] != 'SUCCESS':
        print(f"✗ Rate limit check failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    if not result.get('allowed', False):
        print(f"✗ Rate limit check should allow request but didn't")
        sys.exit(1)
    
    print(f"✓ Rate limit check passed")
    print(f"  - Current count: {result['current_count']}")
    print(f"  - Limit: {result['limit']}")
    print(f"  - Allowed: {result['allowed']}")
    
except Exception as e:
    print(f"✗ Error checking rate limit: {e}")
    sys.exit(1)

print()

# Test 4: Increment rate limit counter
print("Test 4: Increment rate limit counter")
try:
    for i in range(3):
        result = AgentRateLimitService.increment_rate_limit(agent_id)
        
        if result['status'] != 'SUCCESS':
            print(f"✗ Failed to increment rate limit: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        print(f"  - Increment {i+1}: count = {result['current_count']}")
    
    print("✓ Rate limit counter incremented successfully")
    
except Exception as e:
    print(f"✗ Error incrementing rate limit: {e}")
    sys.exit(1)

print()

# Test 5: Get rate limit status
print("Test 5: Get rate limit status")
try:
    result = AgentRateLimitService.get_rate_limit_status(agent_id)
    
    if result['status'] != 'SUCCESS':
        print(f"✗ Failed to get rate limit status: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    print(f"✓ Rate limit status retrieved")
    print(f"  - Current count: {result['current_count']}")
    print(f"  - Limit: {result['limit']}")
    print(f"  - Remaining: {result['remaining']}")
    print(f"  - Reset at: {result['reset_at']}")
    
except Exception as e:
    print(f"✗ Error getting rate limit status: {e}")
    sys.exit(1)

print()

# Test 6: Exceed rate limit
print("Test 6: Exceed rate limit")
try:
    # Increment to reach the limit (already at 3, need 2 more)
    for i in range(2):
        AgentRateLimitService.increment_rate_limit(agent_id)
    
    # Now check - should be at limit
    result = AgentRateLimitService.check_rate_limit(agent_id)
    
    if result['status'] != 'SUCCESS':
        print(f"✗ Rate limit check failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    if result.get('allowed', True):
        print(f"✗ Rate limit should be exceeded but request was allowed")
        print(f"  - Current count: {result['current_count']}")
        print(f"  - Limit: {result['limit']}")
        sys.exit(1)
    
    print(f"✓ Rate limit correctly blocked request")
    print(f"  - Current count: {result['current_count']}")
    print(f"  - Limit: {result['limit']}")
    print(f"  - Allowed: {result['allowed']}")
    
except Exception as e:
    print(f"✗ Error testing rate limit exceeded: {e}")
    sys.exit(1)

print()

# Test 7: Reset rate limit
print("Test 7: Reset rate limit")
try:
    result = AgentRateLimitService.reset_rate_limit(agent_id)
    
    if result['status'] != 'SUCCESS':
        print(f"✗ Failed to reset rate limit: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Verify counter is reset
    status_result = AgentRateLimitService.get_rate_limit_status(agent_id)
    
    if status_result['current_count'] != 0:
        print(f"✗ Rate limit counter not reset (count = {status_result['current_count']})")
        sys.exit(1)
    
    print(f"✓ Rate limit reset successfully")
    print(f"  - Current count: {status_result['current_count']}")
    
except Exception as e:
    print(f"✗ Error resetting rate limit: {e}")
    sys.exit(1)

print()

# Test 8: Verify middleware is configured
print("Test 8: Verify middleware is configured")
try:
    from django.conf import settings
    
    middleware = settings.MIDDLEWARE
    
    if 'ai_agents.middleware.AgentAuthenticationMiddleware' not in middleware:
        print("✗ AgentAuthenticationMiddleware not in MIDDLEWARE settings")
        sys.exit(1)
    
    if 'ai_agents.middleware.AgentRateLimitMiddleware' not in middleware:
        print("✗ AgentRateLimitMiddleware not in MIDDLEWARE settings")
        sys.exit(1)
    
    print("✓ Middleware properly configured")
    print(f"  - AgentAuthenticationMiddleware: ✓")
    print(f"  - AgentRateLimitMiddleware: ✓")
    
except Exception as e:
    print(f"✗ Error verifying middleware: {e}")
    sys.exit(1)

print()

# Cleanup
print("Cleanup: Removing test agent")
try:
    AIAgent.objects.filter(id=agent_id).delete()
    cache.clear()
    print("✓ Test agent removed")
except Exception as e:
    print(f"⚠ Warning: Could not clean up test agent: {e}")

print()
print("=" * 60)
print("✅ ALL RATE LIMITING VERIFICATION TESTS PASSED")
print("=" * 60)
print()
print("Summary:")
print("  • AgentRateLimitService implemented correctly")
print("  • Rate limiting methods work as expected")
print("  • Middleware properly configured")
print("  • Cache integration working")
print()
print("The rate limiting infrastructure is ready for use!")
print()

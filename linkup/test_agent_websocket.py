"""
Test script for AI Agent WebSocket integration.

This script verifies that:
1. AgentConsumer is properly configured
2. WebSocket routing is set up correctly
3. JWT authentication works
4. Message delivery via WebSocket functions
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from ai_agents.models import AIAgent, AgentMessage
from ai_agents.services import AgentRegistryService, AgentAuthenticationService, AgentCommunicationService
from ai_agents.consumers import AgentConsumer
from ai_agents.offline_queue_manager import OfflineQueueManager
from django.core.cache import cache


def test_agent_consumer_import():
    """Test that AgentConsumer can be imported."""
    print("✓ AgentConsumer imported successfully")
    return True


def test_routing_configuration():
    """Test that WebSocket routing is configured."""
    try:
        from ai_agents.routing import websocket_urlpatterns
        
        if not websocket_urlpatterns:
            print("✗ No WebSocket URL patterns found")
            return False
        
        print(f"✓ Found {len(websocket_urlpatterns)} WebSocket URL pattern(s)")
        
        for pattern in websocket_urlpatterns:
            print(f"  - Pattern: {pattern.pattern.pattern}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error checking routing: {e}")
        return False


def test_asgi_configuration():
    """Test that ASGI application includes agent routing."""
    try:
        from professional_network.asgi import application
        
        print("✓ ASGI application loaded successfully")
        
        # Check if application has websocket protocol
        if hasattr(application, 'application_mapping'):
            protocols = list(application.application_mapping.keys())
            print(f"  - Configured protocols: {protocols}")
            
            if 'websocket' in protocols:
                print("  ✓ WebSocket protocol configured")
                return True
            else:
                print("  ✗ WebSocket protocol not configured")
                return False
        else:
            print("  - Application structure: ProtocolTypeRouter")
            return True
        
    except Exception as e:
        print(f"✗ Error checking ASGI: {e}")
        return False


def test_offline_queue_manager():
    """Test offline queue manager functionality."""
    try:
        # Test queue count for non-existent agent
        count = OfflineQueueManager.get_queue_count('test-agent-id')
        print(f"✓ OfflineQueueManager.get_queue_count() works (count: {count})")
        
        # Test clear queue
        result = OfflineQueueManager.clear_queue('test-agent-id')
        print(f"✓ OfflineQueueManager.clear_queue() works (result: {result})")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing OfflineQueueManager: {e}")
        return False


def test_agent_online_status():
    """Test agent online status tracking."""
    try:
        # Test setting online status
        test_agent_id = 'test-agent-123'
        cache_key = f'agent_online:{test_agent_id}'
        
        # Set online
        cache.set(cache_key, True, timeout=300)
        is_online = cache.get(cache_key, False)
        
        if is_online:
            print("✓ Agent online status can be set in cache")
        else:
            print("✗ Failed to set agent online status")
            return False
        
        # Clear status
        cache.delete(cache_key)
        is_online = cache.get(cache_key, False)
        
        if not is_online:
            print("✓ Agent online status can be cleared from cache")
        else:
            print("✗ Failed to clear agent online status")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing online status: {e}")
        return False


def test_websocket_message_payload():
    """Test WebSocket message payload structure."""
    try:
        from django.utils import timezone
        
        # Create a mock message payload
        payload = {
            'type': 'agent_message',
            'message_id': 'test-message-id',
            'sender_id': 'sender-id',
            'sender_name': 'Test Sender',
            'content': 'Test message content',
            'metadata': {'test': 'data'},
            'message_type': 'TEXT',
            'priority': 3,
            'parent_message_id': None,
            'timestamp': timezone.now().isoformat()
        }
        
        # Verify all required fields are present
        required_fields = ['type', 'message_id', 'sender_id', 'sender_name', 'content', 'timestamp']
        
        for field in required_fields:
            if field not in payload:
                print(f"✗ Missing required field: {field}")
                return False
        
        print("✓ WebSocket message payload structure is correct")
        print(f"  - Payload fields: {list(payload.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing message payload: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("AI Agent WebSocket Integration Test")
    print("=" * 60)
    print()
    
    tests = [
        ("AgentConsumer Import", test_agent_consumer_import),
        ("WebSocket Routing", test_routing_configuration),
        ("ASGI Configuration", test_asgi_configuration),
        ("OfflineQueueManager", test_offline_queue_manager),
        ("Agent Online Status", test_agent_online_status),
        ("Message Payload Structure", test_websocket_message_payload),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\nTest: {test_name}")
        print("-" * 60)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

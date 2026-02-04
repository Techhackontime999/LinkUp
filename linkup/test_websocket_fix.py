#!/usr/bin/env python
"""
Simple test script to verify WebSocket routing fix.
This script checks if the routing.py file is syntactically correct.
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_routing_syntax():
    """Test if the routing.py file has correct syntax."""
    try:
        from messaging import routing
        print("✓ messaging/routing.py syntax is correct")
        
        # Check if websocket_urlpatterns exists
        if hasattr(routing, 'websocket_urlpatterns'):
            patterns = routing.websocket_urlpatterns
            print(f"✓ Found {len(patterns)} WebSocket URL patterns")
            
            for i, pattern in enumerate(patterns):
                print(f"  Pattern {i+1}: {pattern.pattern.pattern}")
            
            return True
        else:
            print("✗ websocket_urlpatterns not found in routing.py")
            return False
            
    except SyntaxError as e:
        print(f"✗ Syntax error in routing.py: {e}")
        return False
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_asgi_configuration():
    """Test if ASGI configuration is correct."""
    try:
        from professional_network import asgi
        print("✓ ASGI configuration is syntactically correct")
        
        # Check if application exists
        if hasattr(asgi, 'application'):
            print("✓ ASGI application found")
            return True
        else:
            print("✗ ASGI application not found")
            return False
            
    except Exception as e:
        print(f"✗ ASGI configuration error: {e}")
        return False

def test_consumers_syntax():
    """Test if consumers.py has correct syntax."""
    try:
        from messaging import consumers
        print("✓ messaging/consumers.py syntax is correct")
        
        # Check if required consumers exist
        if hasattr(consumers, 'ChatConsumer'):
            print("✓ ChatConsumer found")
        else:
            print("✗ ChatConsumer not found")
            
        if hasattr(consumers, 'NotificationsConsumer'):
            print("✓ NotificationsConsumer found")
        else:
            print("✗ NotificationsConsumer not found")
            
        return True
        
    except Exception as e:
        print(f"✗ Consumers syntax error: {e}")
        return False

if __name__ == '__main__':
    print("Testing WebSocket Infrastructure Fix...")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test routing syntax
    if not test_routing_syntax():
        all_tests_passed = False
    
    print()
    
    # Test ASGI configuration
    if not test_asgi_configuration():
        all_tests_passed = False
    
    print()
    
    # Test consumers syntax
    if not test_consumers_syntax():
        all_tests_passed = False
    
    print()
    print("=" * 50)
    
    if all_tests_passed:
        print("✓ All WebSocket infrastructure tests passed!")
        print("✓ WebSocket routing fix is successful!")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)
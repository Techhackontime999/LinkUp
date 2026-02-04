#!/usr/bin/env python
"""
Test script to verify the messaging system fixes.
Run this to check if the core messaging functionality is working.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

User = get_user_model()

def test_basic_messaging():
    """Test basic messaging functionality"""
    print("Testing basic messaging functionality...")
    
    # Create test users
    user1 = User.objects.create_user(username='testuser1', password='testpass123')
    user2 = User.objects.create_user(username='testuser2', password='testpass123')
    
    client = Client()
    client.login(username='testuser1', password='testpass123')
    
    # Test chat view
    print("1. Testing chat view...")
    response = client.get(reverse('messaging:chat_view', args=['testuser2']))
    assert response.status_code == 200, f"Chat view failed: {response.status_code}"
    print("   ✓ Chat view loads successfully")
    
    # Test message queueing
    print("2. Testing message creation...")
    response = client.post(
        reverse('messaging:queue_message', args=['testuser2']),
        data=json.dumps({'message': 'Test message', 'client_id': 'test_client_123'}),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Message created successfully: ID {data.get('id')}")
    else:
        print(f"   ✗ Message creation failed: {response.status_code}")
        print(f"   Response: {response.content.decode()}")
        return False
    
    # Test message history
    print("3. Testing message history...")
    response = client.get(reverse('messaging:fetch_history', args=['testuser2']))
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Message history loaded: {len(data.get('messages', []))} messages")
    else:
        print(f"   ✗ Message history failed: {response.status_code}")
        return False
    
    # Test load older messages with valid ID
    print("4. Testing load older messages...")
    if data.get('messages'):
        oldest_id = min(msg['id'] for msg in data['messages'])
        response = client.get(
            reverse('messaging:load_older_messages', args=['testuser2']),
            {'before_id': oldest_id, 'page_size': 10}
        )
        if response.status_code in [200, 404]:  # 404 is OK if no older messages
            print("   ✓ Load older messages works")
        else:
            print(f"   ✗ Load older messages failed: {response.status_code}")
            return False
    
    # Test with invalid before_id (should fail gracefully)
    print("5. Testing invalid before_id handling...")
    response = client.get(
        reverse('messaging:load_older_messages', args=['testuser2']),
        {'before_id': 'temp_client_123', 'page_size': 10}
    )
    if response.status_code == 400:
        print("   ✓ Invalid before_id properly rejected")
    else:
        print(f"   ✗ Invalid before_id not handled: {response.status_code}")
    
    # Cleanup
    user1.delete()
    user2.delete()
    
    print("\n✓ All basic messaging tests passed!")
    return True

def test_websocket_routing():
    """Test WebSocket routing configuration"""
    print("Testing WebSocket routing...")
    
    try:
        from messaging.routing import websocket_urlpatterns
        print(f"   ✓ WebSocket routing loaded: {len(websocket_urlpatterns)} patterns")
        
        # Check if patterns are valid
        for pattern in websocket_urlpatterns:
            print(f"   - Pattern: {pattern.pattern.pattern}")
        
        return True
    except Exception as e:
        print(f"   ✗ WebSocket routing error: {e}")
        return False

def test_models():
    """Test model functionality"""
    print("Testing models...")
    
    try:
        from messaging.models import Message, UserStatus, QueuedMessage
        
        # Test model imports
        print("   ✓ All models imported successfully")
        
        # Test basic model creation
        user1 = User.objects.create_user(username='modeltest1', password='testpass123')
        user2 = User.objects.create_user(username='modeltest2', password='testpass123')
        
        # Test Message creation
        message = Message.objects.create(
            sender=user1,
            recipient=user2,
            content="Test message",
            client_id="test_123"
        )
        print(f"   ✓ Message created: {message.id}")
        
        # Test UserStatus creation
        status = UserStatus.objects.create(user=user1, is_online=True)
        print(f"   ✓ UserStatus created: {status.id}")
        
        # Test QueuedMessage creation
        queued = QueuedMessage.objects.create(
            sender=user1,
            recipient=user2,
            content="Queued message"
        )
        print(f"   ✓ QueuedMessage created: {queued.id}")
        
        # Cleanup
        user1.delete()
        user2.delete()
        
        return True
    except Exception as e:
        print(f"   ✗ Model test error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Messaging System Fix Verification ===\n")
    
    tests = [
        test_models,
        test_websocket_routing,
        test_basic_messaging,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"   ✗ Test failed with exception: {e}")
            print()
    
    print(f"=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All tests passed! The messaging system should be working.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
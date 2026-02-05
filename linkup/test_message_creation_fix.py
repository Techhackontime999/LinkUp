#!/usr/bin/env python3
"""
Test script to verify the message creation async context fix
"""
import os
import sys
import asyncio
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

async def test_message_creation():
    """Test message creation in async context"""
    try:
        from messaging.message_persistence_manager import message_persistence_manager
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get test users
        try:
            user1 = await User.objects.aget(username='root')
            user2 = await User.objects.aget(username='user01')
        except User.DoesNotExist:
            print("❌ Test users not found. Please ensure 'root' and 'user01' users exist.")
            return False
        
        print(f"✅ Found test users: {user1.username} and {user2.username}")
        
        # Test message creation
        print("🧪 Testing message creation in async context...")
        
        message = await message_persistence_manager.create_message_atomic(
            sender=user1,
            recipient=user2,
            content="Test message from async context fix",
            client_id=f"test_async_fix_{asyncio.get_event_loop().time()}"
        )
        
        if message:
            print(f"✅ Message created successfully! ID: {message.id}")
            print(f"   Content: {message.content}")
            print(f"   Status: {message.status}")
            print(f"   Client ID: {message.client_id}")
            return True
        else:
            print("❌ Message creation returned None")
            return False
            
    except Exception as e:
        print(f"❌ Message creation failed with error: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check if it's the specific async context error
        if "You cannot call this from an async context" in str(e):
            print("🚨 CRITICAL: Still getting SynchronousOnlyOperation error!")
            print("   The fix needs more work.")
        
        return False

async def test_message_status_update():
    """Test message status update in async context"""
    try:
        from messaging.message_persistence_manager import message_persistence_manager
        from messaging.models import Message
        
        # Get a recent message to test status update
        message = await Message.objects.filter(status='pending').afirst()
        
        if not message:
            print("ℹ️  No pending messages found to test status update")
            return True
        
        print(f"🧪 Testing status update for message {message.id}...")
        
        success = await message_persistence_manager.update_message_status_atomic(
            message.id,
            'sent',
            user_id=message.sender.id
        )
        
        if success:
            print(f"✅ Message status updated successfully!")
            return True
        else:
            print("❌ Message status update failed")
            return False
            
    except Exception as e:
        print(f"❌ Message status update failed with error: {e}")
        
        # Check if it's the specific async context error
        if "You cannot call this from an async context" in str(e):
            print("🚨 CRITICAL: Still getting SynchronousOnlyOperation error in status update!")
        
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Message Creation Async Context Fix")
    print("=" * 50)
    
    tests = [
        ("Message Creation", test_message_creation),
        ("Message Status Update", test_message_status_update),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The async context fix is working.")
        print("\n💡 You should now be able to:")
        print("1. Send messages through WebSocket without errors")
        print("2. See messages appear in the chat interface")
        print("3. No more 'SynchronousOnlyOperation' errors in logs")
    else:
        print("⚠️  Some tests failed. The fix may need additional work.")
        print("\n🔧 If tests are still failing:")
        print("1. Check Django logs for specific error messages")
        print("2. Ensure all database operations use async methods")
        print("3. Verify no sync database calls in async contexts")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
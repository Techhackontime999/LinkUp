#!/usr/bin/env python3
"""
Simple test to check if basic async context issues are resolved
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

async def test_basic_message_operations():
    """Test basic message operations in async context"""
    try:
        from messaging.models import Message
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Test async user retrieval
        try:
            user1 = await User.objects.aget(username='root')
            user2 = await User.objects.aget(username='user01')
            print(f"✅ Found test users: {user1.username} and {user2.username}")
        except User.DoesNotExist:
            print("❌ Test users not found. Creating test users...")
            user1 = await User.objects.acreate(username='root', email='root@test.com')
            user2 = await User.objects.acreate(username='user01', email='user01@test.com')
            print(f"✅ Created test users: {user1.username} and {user2.username}")
        
        # Test basic message creation using async ORM
        print("🧪 Testing basic message creation with async ORM...")
        
        message = await Message.objects.acreate(
            sender=user1,
            recipient=user2,
            content="Test message - async context fix verification",
            status='pending'
        )
        
        print(f"✅ Message created successfully! ID: {message.id}")
        print(f"   Content: {message.content}")
        print(f"   Status: {message.status}")
        
        # Test message retrieval
        retrieved_message = await Message.objects.aget(id=message.id)
        print(f"✅ Message retrieved successfully: {retrieved_message.content}")
        
        # Test message update
        retrieved_message.status = 'sent'
        await retrieved_message.asave()
        print(f"✅ Message status updated to: {retrieved_message.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic message operations failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check for specific async context errors
        if "You cannot call this from an async context" in str(e):
            print("🚨 CRITICAL: Still getting SynchronousOnlyOperation error!")
            print("   The basic async ORM operations are not working properly.")
        
        return False

async def test_message_persistence_manager():
    """Test the message persistence manager in async context"""
    try:
        from messaging.message_persistence_manager import message_persistence_manager
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get test users
        user1 = await User.objects.aget(username='root')
        user2 = await User.objects.aget(username='user01')
        
        print("🧪 Testing message persistence manager...")
        
        # Test message creation through persistence manager
        message = await message_persistence_manager.create_message_atomic(
            sender=user1,
            recipient=user2,
            content="Test message via persistence manager",
            client_id=f"test_pm_{asyncio.get_event_loop().time()}"
        )
        
        if message:
            print(f"✅ Persistence manager created message successfully! ID: {message.id}")
            
            # Test status update
            success = await message_persistence_manager.update_message_status_atomic(
                message.id,
                'sent',
                user_id=user1.id
            )
            
            if success:
                print("✅ Persistence manager updated message status successfully!")
                return True
            else:
                print("❌ Persistence manager failed to update message status")
                return False
        else:
            print("❌ Persistence manager failed to create message")
            return False
            
    except Exception as e:
        print(f"❌ Message persistence manager test failed: {e}")
        
        if "You cannot call this from an async context" in str(e):
            print("🚨 CRITICAL: Persistence manager still has async context issues!")
        
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Basic Async Context Fix")
    print("=" * 50)
    
    tests = [
        ("Basic Message Operations", test_basic_message_operations),
        ("Message Persistence Manager", test_message_persistence_manager),
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
        print("🎉 All basic tests passed! The async context fix is working.")
        print("\n💡 Next steps:")
        print("1. Test WebSocket message sending in the browser")
        print("2. Monitor Django logs for any remaining errors")
        print("3. Run the full messaging test suite")
    else:
        print("⚠️  Some basic tests failed. Need to investigate further.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Fix remaining async context issues after migration
"""
import os
import sys
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

def refresh_django_models():
    """Refresh Django models to pick up new fields"""
    try:
        from django.apps import apps
        from django.core.management import call_command
        
        # Clear Django's model cache
        apps.clear_cache()
        
        # Reload the messaging app
        from messaging import models
        import importlib
        importlib.reload(models)
        
        print("✅ Django models refreshed")
        return True
        
    except Exception as e:
        print(f"❌ Error refreshing Django models: {e}")
        return False

def test_message_creation():
    """Test basic message creation"""
    try:
        from messaging.models import Message
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get test users
        try:
            user1 = User.objects.get(username='root')
            user2 = User.objects.get(username='user01')
        except User.DoesNotExist:
            print("❌ Test users not found. Please ensure 'root' and 'user01' users exist.")
            return False
        
        # Create a test message
        message = Message.objects.create(
            sender=user1,
            recipient=user2,
            content="Test message after migration fix"
        )
        
        print(f"✅ Message created successfully! ID: {message.id}")
        
        # Check if updated_at field exists and works
        if hasattr(message, 'updated_at') and message.updated_at:
            print(f"✅ updated_at field working: {message.updated_at}")
        else:
            print("⚠️  updated_at field missing or None")
        
        return True
        
    except Exception as e:
        print(f"❌ Message creation failed: {e}")
        return False

def test_async_message_creation():
    """Test async message creation"""
    import asyncio
    
    async def async_test():
        try:
            from messaging.message_persistence_manager import message_persistence_manager
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Get test users
            user1 = await User.objects.aget(username='root')
            user2 = await User.objects.aget(username='user01')
            
            # Test message creation
            message = await message_persistence_manager.create_message_atomic(
                sender=user1,
                recipient=user2,
                content="Async test message after fixes",
                client_id=f"test_fix_{asyncio.get_event_loop().time()}"
            )
            
            if message:
                print(f"✅ Async message created successfully! ID: {message.id}")
                return True
            else:
                print("❌ Async message creation returned None")
                return False
                
        except Exception as e:
            print(f"❌ Async message creation failed: {e}")
            return False
    
    try:
        return asyncio.run(async_test())
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False

def main():
    """Run all fixes and tests"""
    print("🔧 Fixing Remaining Async Context Issues")
    print("=" * 50)
    
    steps = [
        ("Refresh Django Models", refresh_django_models),
        ("Test Basic Message Creation", test_message_creation),
        ("Test Async Message Creation", test_async_message_creation),
    ]
    
    passed = 0
    total = len(steps)
    
    for step_name, step_func in steps:
        print(f"\n🧪 {step_name}...")
        try:
            if step_func():
                passed += 1
                print(f"✅ {step_name} PASSED")
            else:
                print(f"❌ {step_name} FAILED")
        except Exception as e:
            print(f"❌ {step_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} steps passed")
    
    if passed == total:
        print("🎉 All fixes applied successfully!")
        print("\n💡 Next steps:")
        print("1. Restart your Django server")
        print("2. Test WebSocket messaging in the browser")
        print("3. Run: python test_message_creation_fix.py")
    else:
        print("⚠️  Some issues remain.")
        print("\n🔧 Try:")
        print("1. Restart Django server completely")
        print("2. Clear any cached Python bytecode: find . -name '*.pyc' -delete")
        print("3. Check Django logs for specific errors")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
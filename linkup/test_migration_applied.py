#!/usr/bin/env python3
"""
Test script to verify the updated_at field migration was applied correctly
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

def test_updated_at_field():
    """Test if the updated_at field exists on Message model"""
    try:
        from messaging.models import Message
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Check if updated_at field exists in the model
        if hasattr(Message, 'updated_at'):
            print("✅ Message model has updated_at field")
        else:
            print("❌ Message model is missing updated_at field")
            return False
        
        # Check if we can create a message
        try:
            user1 = User.objects.get(username='root')
            user2 = User.objects.get(username='user01')
        except User.DoesNotExist:
            print("❌ Test users not found. Please ensure 'root' and 'user01' users exist.")
            return False
        
        # Try to create a message and check updated_at
        message = Message.objects.create(
            sender=user1,
            recipient=user2,
            content="Test message for updated_at field verification"
        )
        
        if hasattr(message, 'updated_at') and message.updated_at:
            print(f"✅ Message created with updated_at: {message.updated_at}")
            print(f"   Message ID: {message.id}")
            print(f"   Created at: {message.created_at}")
            print(f"   Updated at: {message.updated_at}")
            return True
        else:
            print("❌ Message created but updated_at field is missing or None")
            return False
            
    except Exception as e:
        print(f"❌ Error testing updated_at field: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

def test_message_fields():
    """Test all Message model fields"""
    try:
        from messaging.models import Message
        
        # Get all field names
        field_names = [field.name for field in Message._meta.get_fields()]
        print(f"📋 Message model fields: {', '.join(sorted(field_names))}")
        
        # Check for required fields
        required_fields = ['sender', 'recipient', 'content', 'created_at', 'updated_at', 'status']
        missing_fields = []
        
        for field in required_fields:
            if field not in field_names:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {', '.join(missing_fields)}")
            return False
        else:
            print("✅ All required fields present")
            return True
            
    except Exception as e:
        print(f"❌ Error checking message fields: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Testing Migration Application")
    print("=" * 50)
    
    tests = [
        ("Message Fields Check", test_message_fields),
        ("Updated At Field Test", test_updated_at_field),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Migration applied successfully!")
        print("\n💡 The updated_at field is working correctly.")
        print("You can now run the async context tests.")
    else:
        print("⚠️  Migration issues detected.")
        print("\n🔧 Try running:")
        print("1. python manage.py makemigrations")
        print("2. python manage.py migrate")
        print("3. Restart Django server")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
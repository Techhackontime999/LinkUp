#!/usr/bin/env python3
"""
Quick script to check for async context errors in the messaging system
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

def check_recent_errors():
    """Check for recent async context errors"""
    try:
        from messaging.models import MessagingError
        from datetime import timedelta
        from django.utils import timezone
        
        # Check for errors in the last 10 minutes
        cutoff_time = timezone.now() - timedelta(minutes=10)
        
        # Look for async context errors
        async_errors = MessagingError.objects.filter(
            error_type='async_context',
            occurred_at__gte=cutoff_time
        ).order_by('-occurred_at')
        
        print(f"🔍 Checking for async context errors in the last 10 minutes...")
        
        if async_errors.exists():
            print(f"⚠️  Found {async_errors.count()} async context errors:")
            for error in async_errors[:5]:  # Show last 5
                print(f"   - {error.occurred_at}: {error.error_message[:100]}...")
                if 'SynchronousOnlyOperation' in error.error_message:
                    print("     🚨 CRITICAL: SynchronousOnlyOperation detected!")
            return False
        else:
            print("✅ No async context errors found in the last 10 minutes")
            return True
            
    except Exception as e:
        print(f"❌ Error checking for async errors: {e}")
        return False

def check_websocket_errors():
    """Check for recent WebSocket errors"""
    try:
        from messaging.models import MessagingError
        from datetime import timedelta
        from django.utils import timezone
        
        # Check for errors in the last 10 minutes
        cutoff_time = timezone.now() - timedelta(minutes=10)
        
        # Look for WebSocket errors
        websocket_errors = MessagingError.objects.filter(
            error_type__in=['websocket_transmission', 'connection_handling'],
            occurred_at__gte=cutoff_time
        ).order_by('-occurred_at')
        
        print(f"🔍 Checking for WebSocket errors in the last 10 minutes...")
        
        if websocket_errors.exists():
            print(f"⚠️  Found {websocket_errors.count()} WebSocket errors:")
            for error in websocket_errors[:3]:  # Show last 3
                print(f"   - {error.occurred_at}: {error.error_message[:80]}...")
            return websocket_errors.count() < 5  # Allow some errors but not too many
        else:
            print("✅ No WebSocket errors found in the last 10 minutes")
            return True
            
    except Exception as e:
        print(f"❌ Error checking for WebSocket errors: {e}")
        return False

def check_message_creation_errors():
    """Check for message creation specific errors"""
    try:
        from messaging.models import MessagingError
        from datetime import timedelta
        from django.utils import timezone
        
        # Check for errors in the last 10 minutes
        cutoff_time = timezone.now() - timedelta(minutes=10)
        
        # Look for message processing errors
        message_errors = MessagingError.objects.filter(
            error_type='message_processing',
            error_message__icontains='Failed to create message',
            occurred_at__gte=cutoff_time
        ).order_by('-occurred_at')
        
        print(f"🔍 Checking for message creation errors in the last 10 minutes...")
        
        if message_errors.exists():
            print(f"⚠️  Found {message_errors.count()} message creation errors:")
            for error in message_errors[:3]:  # Show last 3
                print(f"   - {error.occurred_at}: {error.error_message[:80]}...")
            return False
        else:
            print("✅ No message creation errors found in the last 10 minutes")
            return True
            
    except Exception as e:
        print(f"❌ Error checking for message creation errors: {e}")
        return False

def main():
    """Run all error checks"""
    print("🔍 Checking for Async Context and WebSocket Errors")
    print("=" * 50)
    
    checks = [
        ("Async Context Errors", check_recent_errors),
        ("WebSocket Errors", check_websocket_errors),
        ("Message Creation Errors", check_message_creation_errors),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n🧪 {check_name}:")
        if check_func():
            passed += 1
        else:
            print(f"❌ Issues found in {check_name}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! The messaging system appears healthy.")
        print("\n💡 This means:")
        print("✅ No async context errors detected")
        print("✅ WebSocket connections are stable")
        print("✅ Message creation is working properly")
    else:
        print("⚠️  Some issues detected. Check the details above.")
        print("\n🔧 Next steps:")
        print("1. Review the specific errors shown above")
        print("2. Test message sending in the browser")
        print("3. Monitor Django logs for new errors")
        print("4. Run: python manage.py monitor_messaging_health")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
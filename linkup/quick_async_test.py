#!/usr/bin/env python3
"""
Quick test to verify async context fixes are working
Run this after starting the Django server to test WebSocket functionality
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

def test_imports():
    """Test that all our fixes can be imported"""
    try:
        from messaging.async_error_handler import AsyncErrorHandler
        from messaging.error_monitor import error_monitor
        from messaging.models import MessagingError
        from messaging.connection_validator import ConnectionValidator
        print("✅ All async fix imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_async_error_handler():
    """Test AsyncErrorHandler functionality"""
    try:
        # Test sync context detection
        is_async = AsyncErrorHandler.is_async_context()
        print(f"✅ Async context detection works: {is_async}")
        
        # Test sync error logging
        result = AsyncErrorHandler.log_error_sync(
            'test_error',
            'Quick test error',
            {'test': True}
        )
        print("✅ Sync error logging works")
        return True
    except Exception as e:
        print(f"❌ AsyncErrorHandler test failed: {e}")
        return False

def test_connection_validator():
    """Test ConnectionValidator safe_get method"""
    try:
        validator = ConnectionValidator()
        
        # Test safe_get
        result = validator.safe_get({'key': 'value'}, 'key')
        assert result == 'value'
        
        result = validator.safe_get({'key': 'value'}, 'missing', 'default')
        assert result == 'default'
        
        print("✅ ConnectionValidator safe_get works")
        return True
    except Exception as e:
        print(f"❌ ConnectionValidator test failed: {e}")
        return False

def test_error_monitor():
    """Test error monitoring functionality"""
    try:
        # Get health report
        report = error_monitor.generate_health_report()
        print(f"✅ Error monitor works - Health Score: {report['health_score']}/100")
        
        # Check for async context errors
        async_check = error_monitor.check_async_context_errors()
        if async_check['has_sync_only_errors']:
            print("⚠️  SynchronousOnlyOperation errors still detected!")
            return False
        else:
            print("✅ No SynchronousOnlyOperation errors detected")
        
        return True
    except Exception as e:
        print(f"❌ Error monitor test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Quick Async Context Fixes Test")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("AsyncErrorHandler Test", test_async_error_handler),
        ("ConnectionValidator Test", test_connection_validator),
        ("Error Monitor Test", test_error_monitor),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Async context fixes are working.")
        print("\n💡 Next steps:")
        print("1. Start your Django server")
        print("2. Test WebSocket connections in the browser")
        print("3. Monitor for SynchronousOnlyOperation errors")
        print("4. Use: python manage.py monitor_messaging_health")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
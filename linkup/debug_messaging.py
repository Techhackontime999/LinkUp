#!/usr/bin/env python
"""
Debug script for messaging system issues.
This script helps identify common problems with the messaging setup.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

def check_django_setup():
    """Check basic Django configuration"""
    print("=== Django Configuration ===")
    
    print(f"Django version: {django.get_version()}")
    print(f"Settings module: {settings.SETTINGS_MODULE}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"Database: {settings.DATABASES['default']['ENGINE']}")
    
    # Check installed apps
    messaging_installed = 'messaging' in settings.INSTALLED_APPS
    channels_installed = 'channels' in settings.INSTALLED_APPS
    
    print(f"Messaging app installed: {messaging_installed}")
    print(f"Channels installed: {channels_installed}")
    
    if not messaging_installed:
        print("❌ ERROR: 'messaging' app not in INSTALLED_APPS")
        return False
    
    if not channels_installed:
        print("❌ ERROR: 'channels' app not in INSTALLED_APPS")
        return False
    
    print("✓ Django configuration looks good")
    return True

def check_database():
    """Check database connectivity and tables"""
    print("\n=== Database Check ===")
    
    try:
        from django.db import connection
        from messaging.models import Message, UserStatus, QueuedMessage
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        print("✓ Database connection successful")
        
        # Check if tables exist
        try:
            Message.objects.count()
            print("✓ Message table exists")
        except Exception as e:
            print(f"❌ Message table issue: {e}")
            return False
        
        try:
            UserStatus.objects.count()
            print("✓ UserStatus table exists")
        except Exception as e:
            print(f"❌ UserStatus table issue: {e}")
            return False
        
        try:
            QueuedMessage.objects.count()
            print("✓ QueuedMessage table exists")
        except Exception as e:
            print(f"❌ QueuedMessage table issue: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_websocket_config():
    """Check WebSocket configuration"""
    print("\n=== WebSocket Configuration ===")
    
    try:
        # Check ASGI configuration
        from professional_network.asgi import application
        print("✓ ASGI application loads successfully")
        
        # Check routing
        from messaging.routing import websocket_urlpatterns
        print(f"✓ WebSocket routing loaded: {len(websocket_urlpatterns)} patterns")
        
        for i, pattern in enumerate(websocket_urlpatterns):
            print(f"  {i+1}. {pattern.pattern.pattern}")
        
        # Check consumers
        from messaging.consumers import ChatConsumer, NotificationsConsumer
        print("✓ Consumers import successfully")
        
        # Check channels configuration
        if hasattr(settings, 'CHANNEL_LAYERS'):
            print("✓ CHANNEL_LAYERS configured")
            print(f"  Backend: {settings.CHANNEL_LAYERS['default']['BACKEND']}")
        else:
            print("⚠️  CHANNEL_LAYERS not configured (will use in-memory)")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket configuration error: {e}")
        return False

def check_urls():
    """Check URL configuration"""
    print("\n=== URL Configuration ===")
    
    try:
        from django.urls import reverse
        
        # Test key URLs
        urls_to_test = [
            ('messaging:inbox', []),
            ('messaging:chat_view', ['testuser']),
            ('messaging:fetch_history', ['testuser']),
            ('messaging:queue_message', ['testuser']),
            ('messaging:load_older_messages', ['testuser']),
        ]
        
        for url_name, args in urls_to_test:
            try:
                url = reverse(url_name, args=args)
                print(f"✓ {url_name}: {url}")
            except Exception as e:
                print(f"❌ {url_name}: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ URL configuration error: {e}")
        return False

def check_static_files():
    """Check static files configuration"""
    print("\n=== Static Files ===")
    
    try:
        import os
        
        # Check if chat.js exists
        chat_js_path = os.path.join(settings.BASE_DIR, 'messaging', 'static', 'messaging', 'chat.js')
        if os.path.exists(chat_js_path):
            print("✓ chat.js file exists")
            
            # Check file size
            size = os.path.getsize(chat_js_path)
            print(f"  File size: {size} bytes")
            
            if size < 1000:
                print("⚠️  chat.js file seems very small")
        else:
            print("❌ chat.js file not found")
            return False
        
        # Check templates
        template_path = os.path.join(settings.BASE_DIR, 'messaging', 'templates', 'messaging', 'chat.html')
        if os.path.exists(template_path):
            print("✓ chat.html template exists")
        else:
            print("❌ chat.html template not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Static files error: {e}")
        return False

def check_dependencies():
    """Check required dependencies"""
    print("\n=== Dependencies ===")
    
    required_packages = [
        'channels',
        'channels_redis',
        'daphne',
    ]
    
    all_good = True
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            all_good = False
    
    return all_good

def main():
    """Run all checks"""
    print("=== Messaging System Debug ===\n")
    
    checks = [
        check_django_setup,
        check_dependencies,
        check_database,
        check_urls,
        check_websocket_config,
        check_static_files,
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        try:
            if check():
                passed += 1
        except Exception as e:
            print(f"❌ Check failed with exception: {e}")
    
    print(f"\n=== Results: {passed}/{total} checks passed ===")
    
    if passed == total:
        print("🎉 All checks passed! The messaging system should be properly configured.")
        print("\nNext steps:")
        print("1. Run: python manage.py migrate")
        print("2. Start server with: daphne -p 8000 professional_network.asgi:application")
        print("3. Or use: python manage.py runserver (for development)")
    else:
        print("❌ Some checks failed. Fix the issues above before proceeding.")
        print("\nCommon fixes:")
        print("1. Install missing dependencies: pip install channels channels-redis daphne")
        print("2. Run migrations: python manage.py migrate")
        print("3. Check INSTALLED_APPS in settings.py")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python
"""
Verification script for messaging admin enhancements (Task 9)
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from messaging.admin import MessageAdmin, NotificationAdmin, NotificationPreferenceAdmin, UserStatusAdmin
from messaging.models import Message, Notification, NotificationPreference, UserStatus
from linkup.admin import admin_site


def verify_messaging_admin():
    """Verify messaging admin enhancements"""
    print("=" * 80)
    print("MESSAGING ADMIN VERIFICATION - Task 9")
    print("=" * 80)
    
    all_passed = True
    
    # Test 9.1: MessageAdmin
    print("\n9.1 MessageAdmin Configuration:")
    print("-" * 40)
    
    message_admin = MessageAdmin(Message, admin_site)
    
    # Check list_display
    expected_list_display = ('sender', 'recipient', 'content_preview', 'timestamp', 'is_read')
    if message_admin.list_display == expected_list_display:
        print("✓ list_display configured correctly")
    else:
        print(f"✗ list_display mismatch: {message_admin.list_display}")
        all_passed = False
    
    # Check list_filter
    expected_list_filter = ('is_read', 'created_at')
    if message_admin.list_filter == expected_list_filter:
        print("✓ list_filter configured correctly")
    else:
        print(f"✗ list_filter mismatch: {message_admin.list_filter}")
        all_passed = False
    
    # Check search_fields
    expected_search_fields = ('sender__username', 'recipient__username', 'content')
    if message_admin.search_fields == expected_search_fields:
        print("✓ search_fields configured correctly")
    else:
        print(f"✗ search_fields mismatch: {message_admin.search_fields}")
        all_passed = False
    
    # Check date_hierarchy
    if message_admin.date_hierarchy == 'created_at':
        print("✓ date_hierarchy configured correctly")
    else:
        print(f"✗ date_hierarchy mismatch: {message_admin.date_hierarchy}")
        all_passed = False
    
    # Check autocomplete_fields
    expected_autocomplete = ('sender', 'recipient')
    if message_admin.autocomplete_fields == expected_autocomplete:
        print("✓ autocomplete_fields configured correctly")
    else:
        print(f"✗ autocomplete_fields mismatch: {message_admin.autocomplete_fields}")
        all_passed = False
    
    # Check readonly_fields
    if 'timestamp' in message_admin.readonly_fields:
        print("✓ readonly_fields configured correctly")
    else:
        print(f"✗ readonly_fields missing timestamp: {message_admin.readonly_fields}")
        all_passed = False
    
    # Test 9.2 & 9.3: NotificationAdmin
    print("\n9.2 & 9.3 NotificationAdmin Configuration:")
    print("-" * 40)
    
    notification_admin = NotificationAdmin(Notification, admin_site)
    
    # Check list_display
    expected_list_display = ('user', 'notification_type', 'message_preview', 'is_read', 'created_at')
    if notification_admin.list_display == expected_list_display:
        print("✓ list_display configured correctly")
    else:
        print(f"✗ list_display mismatch: {notification_admin.list_display}")
        all_passed = False
    
    # Check message_preview method exists
    if hasattr(notification_admin, 'message_preview'):
        print("✓ message_preview method exists")
    else:
        print("✗ message_preview method missing")
        all_passed = False
    
    # Check date_hierarchy
    if notification_admin.date_hierarchy == 'created_at':
        print("✓ date_hierarchy configured correctly")
    else:
        print(f"✗ date_hierarchy mismatch: {notification_admin.date_hierarchy}")
        all_passed = False
    
    # Check autocomplete_fields
    if 'recipient' in notification_admin.autocomplete_fields:
        print("✓ autocomplete_fields configured correctly")
    else:
        print(f"✗ autocomplete_fields missing recipient: {notification_admin.autocomplete_fields}")
        all_passed = False
    
    # Test 9.4: NotificationPreferenceAdmin
    print("\n9.4 NotificationPreferenceAdmin Configuration:")
    print("-" * 40)
    
    pref_admin = NotificationPreferenceAdmin(NotificationPreference, admin_site)
    
    # Check list_display includes required fields
    required_fields = ['user', 'notification_type', 'delivery_method', 'is_enabled']
    missing_fields = [f for f in required_fields if f not in pref_admin.list_display]
    if not missing_fields:
        print("✓ list_display configured correctly")
    else:
        print(f"✗ list_display missing fields: {missing_fields}")
        all_passed = False
    
    # Check autocomplete_fields
    if 'user' in pref_admin.autocomplete_fields:
        print("✓ autocomplete_fields configured correctly")
    else:
        print(f"✗ autocomplete_fields missing user: {pref_admin.autocomplete_fields}")
        all_passed = False
    
    # Test 9.5: UserStatusAdmin
    print("\n9.5 UserStatusAdmin Configuration:")
    print("-" * 40)
    
    status_admin = UserStatusAdmin(UserStatus, admin_site)
    
    # Check list_display
    expected_list_display = ('user', 'status', 'last_updated')
    if status_admin.list_display == expected_list_display:
        print("✓ list_display configured correctly")
    else:
        print(f"✗ list_display mismatch: {status_admin.list_display}")
        all_passed = False
    
    # Check list_filter
    if 'is_online' in status_admin.list_filter and 'last_seen' in status_admin.list_filter:
        print("✓ list_filter configured correctly")
    else:
        print(f"✗ list_filter mismatch: {status_admin.list_filter}")
        all_passed = False
    
    # Check autocomplete_fields
    if 'user' in status_admin.autocomplete_fields:
        print("✓ autocomplete_fields configured correctly")
    else:
        print(f"✗ autocomplete_fields missing user: {status_admin.autocomplete_fields}")
        all_passed = False
    
    # Check readonly_fields
    if 'last_seen' in status_admin.readonly_fields:
        print("✓ readonly_fields configured correctly")
    else:
        print(f"✗ readonly_fields missing last_seen: {status_admin.readonly_fields}")
        all_passed = False
    
    # Check model registration
    print("\nModel Registration:")
    print("-" * 40)
    
    registered_models = [Message, UserStatus, Notification, NotificationPreference]
    for model in registered_models:
        if admin_site.is_registered(model):
            print(f"✓ {model.__name__} is registered")
        else:
            print(f"✗ {model.__name__} is NOT registered")
            all_passed = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Task 9 implementation is correct!")
    else:
        print("✗ SOME CHECKS FAILED - Please review the implementation")
    print("=" * 80)
    
    return all_passed


if __name__ == '__main__':
    try:
        success = verify_messaging_admin()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""
Unit tests for users admin functionality

These tests verify specific examples and edge cases for admin functionality.
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from users.admin import CustomUserAdmin

User = get_user_model()


class UserAdminUnitTests(TestCase):
    """Unit tests for UserAdmin functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.user_admin = CustomUserAdmin(User, self.admin_site)
    
    def _create_request_with_messages(self):
        """Create a request with proper message framework support"""
        request = self.factory.get('/')
        
        # Add session middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add message storage
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        return request
    
    def test_activate_users_basic_functionality(self):
        """Test basic bulk user activation functionality"""
        # Create test users with mixed active states
        user1 = User.objects.create(username='user1', is_active=False)
        user2 = User.objects.create(username='user2', is_active=True)
        user3 = User.objects.create(username='user3', is_active=False)
        
        # Create queryset
        queryset = User.objects.filter(id__in=[user1.id, user2.id, user3.id])
        
        # Execute bulk activation
        request = self._create_request_with_messages()
        self.user_admin.activate_users(request, queryset)
        
        # Verify all users are now active
        user1.refresh_from_db()
        user2.refresh_from_db()
        user3.refresh_from_db()
        
        self.assertTrue(user1.is_active)
        self.assertTrue(user2.is_active)
        self.assertTrue(user3.is_active)
    
    def test_activate_users_with_empty_queryset(self):
        """Test bulk activation with empty queryset"""
        queryset = User.objects.none()
        request = self._create_request_with_messages()
        
        # Should not raise any exceptions
        try:
            self.user_admin.activate_users(request, queryset)
        except Exception as e:
            self.fail(f"Bulk activation with empty queryset should not fail: {e}")
    
    def test_deactivate_users_basic_functionality(self):
        """Test basic bulk user deactivation functionality"""
        # Create test users with mixed active states
        user1 = User.objects.create(username='user1', is_active=True)
        user2 = User.objects.create(username='user2', is_active=False)
        user3 = User.objects.create(username='user3', is_active=True)
        
        # Create queryset
        queryset = User.objects.filter(id__in=[user1.id, user2.id, user3.id])
        
        # Execute bulk deactivation
        request = self._create_request_with_messages()
        self.user_admin.deactivate_users(request, queryset)
        
        # Verify all users are now inactive
        user1.refresh_from_db()
        user2.refresh_from_db()
        user3.refresh_from_db()
        
        self.assertFalse(user1.is_active)
        self.assertFalse(user2.is_active)
        self.assertFalse(user3.is_active)
    
    def test_get_full_name_method(self):
        """Test the get_full_name display method"""
        # Test with both first and last name
        user1 = User.objects.create(
            username='user1', 
            first_name='John', 
            last_name='Doe'
        )
        result1 = self.user_admin.get_full_name(user1)
        self.assertEqual(result1, 'John Doe')
        
        # Test with only username (no first/last name)
        user2 = User.objects.create(username='user2')
        result2 = self.user_admin.get_full_name(user2)
        self.assertEqual(result2, 'user2')
        
        # Test with only first name
        user3 = User.objects.create(
            username='user3', 
            first_name='Jane'
        )
        result3 = self.user_admin.get_full_name(user3)
        self.assertEqual(result3, 'user3')  # Falls back to username
    
    def test_account_status_badge_method(self):
        """Test the account_status_badge display method"""
        # Test active user
        active_user = User.objects.create(username='active', is_active=True)
        active_badge = self.user_admin.account_status_badge(active_user)
        self.assertIn('Active', active_badge)
        self.assertIn('#28a745', active_badge)  # Green color
        
        # Test inactive user
        inactive_user = User.objects.create(username='inactive', is_active=False)
        inactive_badge = self.user_admin.account_status_badge(inactive_user)
        self.assertIn('Inactive', inactive_badge)
        self.assertIn('#dc3545', inactive_badge)  # Red color
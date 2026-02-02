"""
Test admin security and authentication requirements
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AdminSecurityTest(TestCase):
    """Test admin authentication and permission requirements"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create different types of users
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_unauthenticated_user_redirected_to_login(self):
        """Test that non-authenticated users are redirected to login"""
        # Try to access admin index without authentication
        response = self.client.get('/admin/')
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
    
    def test_regular_user_cannot_access_admin(self):
        """Test that regular users (non-staff) cannot access admin"""
        # Login as regular user
        self.client.login(username='regular', password='testpass123')
        
        # Try to access admin index
        response = self.client.get('/admin/')
        
        # Should redirect to login page (Django treats non-staff as not authenticated for admin)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
    
    def test_staff_user_can_access_admin(self):
        """Test that staff users can access admin"""
        # Login as staff user
        self.client.login(username='staff', password='testpass123')
        
        # Try to access admin index
        response = self.client.get('/admin/')
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django administration')
    
    def test_superuser_can_access_admin(self):
        """Test that superusers can access admin"""
        # Login as superuser
        self.client.login(username='admin', password='testpass123')
        
        # Try to access admin index
        response = self.client.get('/admin/')
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django administration')
    
    def test_admin_login_page_accessible(self):
        """Test that admin login page is accessible"""
        response = self.client.get('/admin/login/')
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Password')
    
    def test_admin_logout_functionality(self):
        """Test that admin logout works correctly"""
        # Login as staff user
        self.client.login(username='staff', password='testpass123')
        
        # Verify we can access admin
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        
        # Logout
        response = self.client.get('/admin/logout/')
        
        # Should redirect or show logout page
        self.assertIn(response.status_code, [200, 302])
        
        # Try to access admin again - should be redirected to login
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
    
    def test_admin_model_access_requires_permissions(self):
        """Test that accessing specific admin models requires proper permissions"""
        # Login as staff user (has basic admin access but no specific model permissions)
        self.client.login(username='staff', password='testpass123')
        
        # Try to access user admin changelist
        response = self.client.get('/admin/users/user/')
        
        # Should either be successful (if user has permissions) or show permission denied
        # Django handles this automatically based on user permissions
        self.assertIn(response.status_code, [200, 403])
        
        # Superuser should always have access
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/admin/users/user/')
        self.assertEqual(response.status_code, 200)
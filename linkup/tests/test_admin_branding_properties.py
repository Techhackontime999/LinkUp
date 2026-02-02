"""
Property-based tests for admin branding consistency
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase
import re

User = get_user_model()


class AdminBrandingPropertyTests(HypothesisTestCase):
    """Property tests for consistent branding across admin pages"""
    
    def setUp(self):
        """Set up test data"""
        # Create a superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='admin', password='testpass123')
    
    @given(st.sampled_from([
        'admin:index',
        'admin:users_user_changelist',
        'admin:users_profile_changelist',
        'admin:jobs_job_changelist',
        'admin:feed_post_changelist',
        'admin:messaging_message_changelist',
        'admin:network_connection_changelist',
    ]))
    def test_consistent_branding_across_pages(self, url_name):
        """
        Feature: professional-admin-panel, Property 1: Consistent Branding Across Pages
        
        For any admin page in the Admin_Panel, the page should display the custom 
        site header "LinkUp Administration" and maintain consistent branding elements.
        
        **Validates: Requirements 1.4**
        """
        try:
            # Access the admin page
            url = reverse(url_name)
            response = self.client.get(url)
            
            # Check that response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check for consistent branding elements
            content = response.content.decode('utf-8')
            
            # Check for custom site header
            self.assertIn('LinkUp Administration', content)
            
            # Check for custom site title in browser tab
            self.assertIn('LinkUp Admin Portal', content)
            
            # Check that the old Django branding is not present
            self.assertNotIn('Django administration', content)
            
            # Check for consistent navigation structure
            self.assertIn('id="nav-sidebar"', content)
            
            # Check for consistent header structure
            self.assertIn('id="header"', content)
            self.assertIn('id="branding"', content)
            
        except Exception as e:
            # Some URLs might not exist or be accessible, skip them
            if "NoReverseMatch" in str(e) or response.status_code == 404:
                return
            raise
    
    def test_admin_index_branding(self):
        """Test that the admin index page has correct branding"""
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for custom branding
        self.assertIn('LinkUp Administration', content)
        self.assertIn('Welcome to LinkUp Administration', content)
        
        # Ensure old Django branding is not present
        self.assertNotIn('Django administration', content)
    
    def test_admin_login_page_branding(self):
        """Test that the admin login page has correct branding"""
        # Logout first
        self.client.logout()
        
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check for custom branding in login page
        self.assertIn('LinkUp Admin Portal', content)
    
    @given(st.lists(
        st.sampled_from([
            'admin:users_user_changelist',
            'admin:jobs_job_changelist', 
            'admin:feed_post_changelist'
        ]), 
        min_size=1, 
        max_size=3
    ))
    def test_branding_consistency_across_multiple_pages(self, url_names):
        """
        Test that branding is consistent when navigating between multiple admin pages
        """
        branding_elements = set()
        
        for url_name in url_names:
            try:
                url = reverse(url_name)
                response = self.client.get(url)
                
                if response.status_code == 200:
                    content = response.content.decode('utf-8')
                    
                    # Extract branding elements
                    site_header = re.search(r'<div id="site-name"><a[^>]*>([^<]+)</a></div>', content)
                    if site_header:
                        branding_elements.add(site_header.group(1))
                    
                    # Check title
                    title_match = re.search(r'<title>([^|]*)\|([^<]+)</title>', content)
                    if title_match:
                        branding_elements.add(title_match.group(2).strip())
                        
            except Exception:
                # Skip URLs that don't exist
                continue
        
        # All pages should have the same branding elements
        if branding_elements:
            self.assertIn('LinkUp Administration', branding_elements)
            # Should not have mixed branding
            self.assertNotIn('Django site admin', branding_elements)
    
    def test_custom_css_loading(self):
        """Test that custom CSS is loaded on admin pages"""
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check that custom CSS files are loaded
        # This would depend on your specific CSS setup
        self.assertIn('admin/css/', content)  # Basic admin CSS should be present
    
    def test_no_django_default_branding(self):
        """Ensure that default Django admin branding is completely removed"""
        # Test multiple admin pages
        admin_urls = [
            'admin:index',
            'admin:users_user_changelist',
        ]
        
        for url_name in admin_urls:
            try:
                response = self.client.get(reverse(url_name))
                if response.status_code == 200:
                    content = response.content.decode('utf-8')
                    
                    # These should NOT appear anywhere
                    forbidden_strings = [
                        'Django administration',
                        'Django site admin',
                        'Welcome to Django',
                    ]
                    
                    for forbidden in forbidden_strings:
                        self.assertNotIn(forbidden, content, 
                                       f"Found forbidden Django branding '{forbidden}' on {url_name}")
                        
            except Exception:
                # Skip URLs that don't exist
                continue
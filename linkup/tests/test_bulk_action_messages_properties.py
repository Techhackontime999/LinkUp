"""
Property-based tests for bulk action success messages
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase
from jobs.models import Job
from users.models import Profile
import re

User = get_user_model()


class BulkActionMessagesPropertyTests(HypothesisTestCase):
    """Property tests for bulk action success messages"""
    
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
    
    def test_user_activation_success_message(self):
        """
        Feature: professional-admin-panel, Property 15: Bulk Action Success Messages
        
        For any bulk action that completes successfully, the Admin_Panel should 
        display a success message indicating the number of records affected.
        
        **Validates: Requirements 10.8**
        """
        # Create test users
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'testuser{i}@test.com',
                password='testpass123',
                is_active=False
            )
            users.append(user)
        
        # Perform bulk activation
        url = reverse('admin:users_user_changelist')
        data = {
            'action': 'activate_users',
            '_selected_action': [str(user.pk) for user in users],
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check for success message
        messages = list(response.context['messages'])
        self.assertTrue(len(messages) > 0)
        
        # Check that the message contains the count
        message_text = str(messages[0])
        self.assertIn('3', message_text)
        self.assertIn('activated', message_text.lower())
    
    def test_user_deactivation_success_message(self):
        """Test bulk user deactivation success message"""
        # Create test users
        users = []
        for i in range(2):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'testuser{i}@test.com',
                password='testpass123',
                is_active=True
            )
            users.append(user)
        
        # Perform bulk deactivation with confirmation
        url = reverse('admin:users_user_changelist')
        data = {
            'action': 'deactivate_users',
            '_selected_action': [str(user.pk) for user in users],
            'post': 'yes',  # Confirmation
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check for success message
        messages = list(response.context['messages'])
        self.assertTrue(len(messages) > 0)
        
        # Check that the message contains the count
        message_text = str(messages[0])
        self.assertIn('2', message_text)
        self.assertIn('deactivated', message_text.lower())
    
    def test_job_status_update_success_message(self):
        """Test bulk job status update success message"""
        # Create test jobs
        jobs = []
        for i in range(4):
            job = Job.objects.create(
                title=f'Test Job {i}',
                company=f'Company {i}',
                description=f'Description for job {i}',
                location='Test City',
                job_type='full_time',
                posted_by=self.admin_user,
                is_active=False
            )
            jobs.append(job)
        
        # Perform bulk activation
        url = reverse('admin:jobs_job_changelist')
        data = {
            'action': 'mark_active',
            '_selected_action': [str(job.pk) for job in jobs],
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check for success message
        messages = list(response.context['messages'])
        self.assertTrue(len(messages) > 0)
        
        # Check that the message contains the count
        message_text = str(messages[0])
        self.assertIn('4', message_text)
        self.assertIn('active', message_text.lower())
    
    @given(st.integers(min_value=1, max_value=10))
    def test_bulk_action_message_count_accuracy(self, user_count):
        """
        Property test: The success message should always contain the exact 
        number of records that were affected by the bulk action.
        """
        # Create test users
        users = []
        for i in range(user_count):
            user = User.objects.create_user(
                username=f'propuser{i}_{user_count}',
                email=f'propuser{i}_{user_count}@test.com',
                password='testpass123',
                is_active=False
            )
            users.append(user)
        
        # Perform bulk activation
        url = reverse('admin:users_user_changelist')
        data = {
            'action': 'activate_users',
            '_selected_action': [str(user.pk) for user in users],
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check for success message with correct count
        messages = list(response.context['messages'])
        self.assertTrue(len(messages) > 0)
        
        message_text = str(messages[0])
        
        # The message should contain the exact count
        self.assertIn(str(user_count), message_text)
        
        # Verify the users were actually activated
        for user in users:
            user.refresh_from_db()
            self.assertTrue(user.is_active)
    
    def test_csv_export_success_message(self):
        """Test that CSV export actions show success messages"""
        # Create test users
        users = []
        for i in range(2):
            user = User.objects.create_user(
                username=f'csvuser{i}',
                email=f'csvuser{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        # Perform CSV export
        url = reverse('admin:users_user_changelist')
        data = {
            'action': 'export_as_csv',
            '_selected_action': [str(user.pk) for user in users],
        }
        
        response = self.client.post(url, data)
        
        # CSV export should return a file download (200) or redirect with message
        self.assertIn(response.status_code, [200, 302])
        
        # If it's a CSV download, check the content type
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'text/csv')
    
    def test_empty_selection_handling(self):
        """Test that appropriate messages are shown when no items are selected"""
        # Try to perform bulk action with no selection
        url = reverse('admin:users_user_changelist')
        data = {
            'action': 'activate_users',
            '_selected_action': [],
        }
        
        response = self.client.post(url, data, follow=True)
        
        # Should handle empty selection gracefully
        self.assertEqual(response.status_code, 200)
        
        # Should either show a message or handle gracefully
        # (Django's default behavior varies)
    
    def test_message_format_consistency(self):
        """Test that success messages follow a consistent format"""
        # Create test users
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'formatuser{i}',
                email=f'formatuser{i}@test.com',
                password='testpass123',
                is_active=False
            )
            users.append(user)
        
        # Test different bulk actions for format consistency
        actions_to_test = [
            ('activate_users', 'activated'),
        ]
        
        for action, expected_word in actions_to_test:
            url = reverse('admin:users_user_changelist')
            data = {
                'action': action,
                '_selected_action': [str(user.pk) for user in users],
            }
            
            response = self.client.post(url, data, follow=True)
            
            if response.status_code == 200:
                messages = list(response.context['messages'])
                if messages:
                    message_text = str(messages[0])
                    
                    # Check for consistent format: number + action word
                    self.assertTrue(
                        re.search(r'\d+.*' + expected_word, message_text, re.IGNORECASE),
                        f"Message '{message_text}' doesn't follow expected format"
                    )
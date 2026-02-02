"""
Integration tests for complete admin workflows
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from jobs.models import Job, Application
from users.models import Profile, Experience, Education
from feed.models import Post, Comment
from messaging.models import Message, Notification
from network.models import Connection, Follow

User = get_user_model()


class AdminWorkflowIntegrationTests(TestCase):
    """Integration tests for complete admin workflows"""
    
    def setUp(self):
        """Set up test data"""
        # Create a superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Create a staff user
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create regular users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        
        self.client = Client()
    
    def test_login_search_edit_save_workflow(self):
        """
        Test complete workflow: login → search → edit → save
        
        **Validates: Requirements Multiple**
        """
        # Step 1: Login
        login_success = self.client.login(username='admin', password='testpass123')
        self.assertTrue(login_success)
        
        # Step 2: Access admin index
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LinkUp Administration')
        
        # Step 3: Navigate to user list
        response = self.client.get(reverse('admin:users_user_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Search for a user
        response = self.client.get(reverse('admin:users_user_changelist'), {'q': 'user1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user1')
        
        # Step 5: Edit the user
        user_edit_url = reverse('admin:users_user_change', args=[self.user1.pk])
        response = self.client.get(user_edit_url)
        self.assertEqual(response.status_code, 200)
        
        # Step 6: Save changes
        response = self.client.post(user_edit_url, {
            'username': 'user1',
            'email': 'user1_updated@test.com',
            'first_name': 'Updated',
            'last_name': 'User',
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'date_joined_0': '2024-01-01',
            'date_joined_1': '12:00:00',
        })
        
        # Should redirect after successful save
        self.assertEqual(response.status_code, 302)
        
        # Verify the changes were saved
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.email, 'user1_updated@test.com')
        self.assertEqual(self.user1.first_name, 'Updated')
    
    def test_inline_editing_workflow(self):
        """
        Test inline editing workflow with Profile, Experience, and Education
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create a profile for user1
        profile = Profile.objects.create(
            user=self.user1,
            headline='Software Developer',
            bio='Experienced developer',
            location='New York'
        )
        
        # Edit user with inline profile
        user_edit_url = reverse('admin:users_user_change', args=[self.user1.pk])
        response = self.client.get(user_edit_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that inline forms are present
        self.assertContains(response, 'profile-0-headline')
        self.assertContains(response, 'experiences-TOTAL_FORMS')
        self.assertContains(response, 'educations-TOTAL_FORMS')
        
        # Update user with inline data
        response = self.client.post(user_edit_url, {
            'username': 'user1',
            'email': 'user1@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
            'date_joined_0': '2024-01-01',
            'date_joined_1': '12:00:00',
            
            # Profile inline
            'profile-TOTAL_FORMS': '1',
            'profile-INITIAL_FORMS': '1',
            'profile-MIN_NUM_FORMS': '0',
            'profile-MAX_NUM_FORMS': '1',
            'profile-0-id': profile.pk,
            'profile-0-user': self.user1.pk,
            'profile-0-headline': 'Senior Software Developer',
            'profile-0-bio': 'Very experienced developer',
            'profile-0-location': 'San Francisco',
            
            # Experience inline (empty)
            'experiences-TOTAL_FORMS': '0',
            'experiences-INITIAL_FORMS': '0',
            'experiences-MIN_NUM_FORMS': '0',
            'experiences-MAX_NUM_FORMS': '1000',
            
            # Education inline (empty)
            'educations-TOTAL_FORMS': '0',
            'educations-INITIAL_FORMS': '0',
            'educations-MIN_NUM_FORMS': '0',
            'educations-MAX_NUM_FORMS': '1000',
        })
        
        # Should redirect after successful save
        self.assertEqual(response.status_code, 302)
        
        # Verify inline changes were saved
        profile.refresh_from_db()
        self.assertEqual(profile.headline, 'Senior Software Developer')
        self.assertEqual(profile.location, 'San Francisco')
    
    def test_bulk_action_workflow_with_confirmation(self):
        """
        Test bulk action workflow with confirmation pages
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create test users
        test_users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'bulkuser{i}',
                email=f'bulkuser{i}@test.com',
                password='testpass123',
                is_active=True
            )
            test_users.append(user)
        
        # Step 1: Navigate to user list
        response = self.client.get(reverse('admin:users_user_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Select users and choose deactivate action (requires confirmation)
        response = self.client.post(reverse('admin:users_user_changelist'), {
            'action': 'deactivate_users',
            '_selected_action': [str(user.pk) for user in test_users],
        })
        
        # Should show confirmation page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Are you sure')
        self.assertContains(response, 'deactivate')
        
        # Step 3: Confirm the action
        response = self.client.post(reverse('admin:users_user_changelist'), {
            'action': 'deactivate_users',
            '_selected_action': [str(user.pk) for user in test_users],
            'post': 'yes',  # Confirmation
        }, follow=True)
        
        # Should redirect back to changelist with success message
        self.assertEqual(response.status_code, 200)
        
        # Check for success message
        messages = list(response.context['messages'])
        self.assertTrue(len(messages) > 0)
        message_text = str(messages[0])
        self.assertIn('3', message_text)
        self.assertIn('deactivated', message_text.lower())
        
        # Verify users were deactivated
        for user in test_users:
            user.refresh_from_db()
            self.assertFalse(user.is_active)
    
    def test_job_management_workflow(self):
        """
        Test complete job management workflow
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Step 1: Create a new job
        job_add_url = reverse('admin:jobs_job_add')
        response = self.client.get(job_add_url)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Submit job creation form
        response = self.client.post(job_add_url, {
            'title': 'Software Engineer',
            'company': 'Tech Corp',
            'description': 'Great opportunity for a software engineer',
            'location': 'Remote',
            'job_type': 'full_time',
            'posted_by': self.admin_user.pk,
            'is_active': True,
        })
        
        # Should redirect after creation
        self.assertEqual(response.status_code, 302)
        
        # Verify job was created
        job = Job.objects.get(title='Software Engineer')
        self.assertEqual(job.company, 'Tech Corp')
        
        # Step 3: Edit the job
        job_edit_url = reverse('admin:jobs_job_change', args=[job.pk])
        response = self.client.get(job_edit_url)
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Update job
        response = self.client.post(job_edit_url, {
            'title': 'Senior Software Engineer',
            'company': 'Tech Corp',
            'description': 'Great opportunity for a senior software engineer',
            'location': 'Remote',
            'job_type': 'full_time',
            'posted_by': self.admin_user.pk,
            'is_active': True,
        })
        
        # Should redirect after update
        self.assertEqual(response.status_code, 302)
        
        # Verify job was updated
        job.refresh_from_db()
        self.assertEqual(job.title, 'Senior Software Engineer')
    
    def test_content_moderation_workflow(self):
        """
        Test content moderation workflow for posts and comments
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create test post
        post = Post.objects.create(
            user=self.user1,
            content='This is a test post with some content'
        )
        
        # Create test comment
        comment = Comment.objects.create(
            post=post,
            user=self.user2,
            content='This is a test comment'
        )
        
        # Step 1: Navigate to post list
        response = self.client.get(reverse('admin:feed_post_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: View post details
        post_edit_url = reverse('admin:feed_post_change', args=[post.pk])
        response = self.client.get(post_edit_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that inline comments are shown
        self.assertContains(response, comment.content[:20])  # Truncated content
        
        # Step 3: Navigate to comment list
        response = self.client.get(reverse('admin:feed_comment_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Edit comment
        comment_edit_url = reverse('admin:feed_comment_change', args=[comment.pk])
        response = self.client.get(comment_edit_url)
        self.assertEqual(response.status_code, 200)
    
    def test_messaging_admin_workflow(self):
        """
        Test messaging administration workflow
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create test message
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content='Test message content'
        )
        
        # Step 1: Navigate to message list
        response = self.client.get(reverse('admin:messaging_message_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Search for messages
        response = self.client.get(reverse('admin:messaging_message_changelist'), 
                                 {'q': 'test'})
        self.assertEqual(response.status_code, 200)
        
        # Step 3: View message details
        message_edit_url = reverse('admin:messaging_message_change', args=[message.pk])
        response = self.client.get(message_edit_url)
        self.assertEqual(response.status_code, 200)
    
    def test_network_management_workflow(self):
        """
        Test network connections and follows management workflow
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create test connection
        connection = Connection.objects.create(
            user=self.user1,
            friend=self.user2,
            status='accepted'
        )
        
        # Create test follow
        follow = Follow.objects.create(
            follower=self.user1,
            followed=self.user2
        )
        
        # Step 1: Navigate to connections list
        response = self.client.get(reverse('admin:network_connection_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Navigate to follows list
        response = self.client.get(reverse('admin:network_follow_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Edit connection
        connection_edit_url = reverse('admin:network_connection_change', args=[connection.pk])
        response = self.client.get(connection_edit_url)
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_navigation_workflow(self):
        """
        Test navigation from dashboard to various admin sections
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Step 1: Access dashboard
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to LinkUp Administration')
        
        # Step 2: Navigate to different sections from dashboard
        sections_to_test = [
            ('admin:users_user_changelist', 'Users'),
            ('admin:jobs_job_changelist', 'Jobs'),
            ('admin:feed_post_changelist', 'Posts'),
            ('admin:messaging_message_changelist', 'Messages'),
        ]
        
        for url_name, section_name in sections_to_test:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200, 
                           f"Failed to access {section_name} section")
    
    def test_filter_and_pagination_workflow(self):
        """
        Test filtering and pagination workflow
        """
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create many test users to trigger pagination
        for i in range(150):  # More than list_per_page = 100
            User.objects.create_user(
                username=f'paginationuser{i}',
                email=f'paginationuser{i}@test.com',
                password='testpass123',
                is_active=(i % 2 == 0)  # Alternate active/inactive
            )
        
        # Step 1: Navigate to user list
        response = self.client.get(reverse('admin:users_user_changelist'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Apply filter
        response = self.client.get(reverse('admin:users_user_changelist'), 
                                 {'is_active__exact': '1'})
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Navigate to second page
        response = self.client.get(reverse('admin:users_user_changelist'), 
                                 {'p': '2'})
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Combine filter and pagination
        response = self.client.get(reverse('admin:users_user_changelist'), 
                                 {'is_active__exact': '1', 'p': '2'})
        self.assertEqual(response.status_code, 200)
"""
Test pagination controls in admin interface
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.admin.sites import site
from users.models import Profile
from jobs.models import Job
from feed.models import Post

User = get_user_model()


class AdminPaginationTest(TestCase):
    """Test that pagination controls are displayed for large datasets"""
    
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
    
    def test_user_admin_pagination_controls(self):
        """Test that user admin shows pagination controls with large dataset"""
        # Create 150 users (more than list_per_page = 100)
        users = []
        for i in range(150):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        # Access the user admin changelist
        url = reverse('admin:users_user_changelist')
        response = self.client.get(url)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that pagination controls are present
        self.assertContains(response, 'class="paginator"')
        self.assertContains(response, 'Next')
        
        # Check that only 100 users are shown per page (list_per_page = 100)
        # The response should contain pagination info
        self.assertContains(response, '1-100')
    
    def test_job_admin_pagination_controls(self):
        """Test that job admin shows pagination controls with large dataset"""
        # Create 120 jobs (more than list_per_page = 100)
        jobs = []
        for i in range(120):
            job = Job.objects.create(
                title=f'Job {i}',
                company=f'Company {i}',
                description=f'Description for job {i}',
                location='Test City',
                job_type='full_time',
                posted_by=self.admin_user
            )
            jobs.append(job)
        
        # Access the job admin changelist
        url = reverse('admin:jobs_job_changelist')
        response = self.client.get(url)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that pagination controls are present
        self.assertContains(response, 'class="paginator"')
        self.assertContains(response, 'Next')
    
    def test_post_admin_pagination_controls(self):
        """Test that post admin shows pagination controls with large dataset"""
        # Create 110 posts (more than list_per_page = 100)
        posts = []
        for i in range(110):
            post = Post.objects.create(
                user=self.admin_user,
                content=f'Test post content {i}'
            )
            posts.append(post)
        
        # Access the post admin changelist
        url = reverse('admin:feed_post_changelist')
        response = self.client.get(url)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that pagination controls are present
        self.assertContains(response, 'class="paginator"')
        self.assertContains(response, 'Next')
    
    def test_small_dataset_no_pagination(self):
        """Test that pagination controls are not shown for small datasets"""
        # Create only 10 users (less than list_per_page = 100)
        for i in range(10):
            User.objects.create_user(
                username=f'smalluser{i}',
                email=f'smalluser{i}@test.com',
                password='testpass123'
            )
        
        # Access the user admin changelist
        url = reverse('admin:users_user_changelist')
        response = self.client.get(url)
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that pagination controls are NOT present for small datasets
        # Django doesn't show pagination when all records fit on one page
        self.assertNotContains(response, 'Next')
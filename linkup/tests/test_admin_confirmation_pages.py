"""
Test confirmation pages for destructive bulk actions
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from feed.models import Post, Comment
from jobs.models import Job

User = get_user_model()


class AdminConfirmationPagesTest(TestCase):
    """Test that destructive bulk actions show confirmation pages"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        
        # Create test users
        self.test_user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.test_user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
    
    def test_deactivate_users_shows_confirmation(self):
        """Test that deactivating users shows confirmation page"""
        # Prepare POST data for bulk action
        data = {
            'action': 'deactivate_users',
            '_selected_action': [self.test_user1.pk, self.test_user2.pk],
        }
        
        # Submit bulk action
        response = self.client.post('/admin/users/user/', data, follow=True)
        
        # Should show confirmation page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Are you sure')
        self.assertContains(response, 'deactivate')
    
    def test_deactivate_users_confirmation_executes_action(self):
        """Test that confirming deactivation actually deactivates users"""
        # Verify users are active initially
        self.assertTrue(self.test_user1.is_active)
        self.assertTrue(self.test_user2.is_active)
        
        # Prepare POST data with confirmation
        data = {
            'action': 'deactivate_users',
            '_selected_action': [self.test_user1.pk, self.test_user2.pk],
            'post': 'yes',  # Confirmation flag
        }
        
        # Submit confirmed action
        response = self.client.post('/admin/users/user/', data, follow=True)
        
        # Should redirect back to changelist
        self.assertEqual(response.status_code, 200)
        
        # Verify users are now inactive
        self.test_user1.refresh_from_db()
        self.test_user2.refresh_from_db()
        self.assertFalse(self.test_user1.is_active)
        self.assertFalse(self.test_user2.is_active)
    
    def test_delete_posts_shows_confirmation(self):
        """Test that deleting posts shows confirmation page"""
        # Create test posts
        post1 = Post.objects.create(user=self.test_user1, content='Test post 1')
        post2 = Post.objects.create(user=self.test_user2, content='Test post 2')
        
        # Prepare POST data for bulk delete
        data = {
            'action': 'delete_selected_posts',
            '_selected_action': [post1.pk, post2.pk],
        }
        
        # Submit bulk action
        response = self.client.post('/admin/feed/post/', data, follow=True)
        
        # Should show confirmation page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm deletion')
        self.assertContains(response, 'cannot be undone')
    
    def test_delete_posts_confirmation_executes_action(self):
        """Test that confirming deletion actually deletes posts"""
        # Create test posts
        post1 = Post.objects.create(user=self.test_user1, content='Test post 1')
        post2 = Post.objects.create(user=self.test_user2, content='Test post 2')
        
        # Verify posts exist
        self.assertEqual(Post.objects.count(), 2)
        
        # Prepare POST data with confirmation
        data = {
            'action': 'delete_selected_posts',
            '_selected_action': [post1.pk, post2.pk],
            'apply': 'yes',  # Confirmation flag
        }
        
        # Submit confirmed action
        response = self.client.post('/admin/feed/post/', data, follow=True)
        
        # Should redirect back to changelist
        self.assertEqual(response.status_code, 200)
        
        # Verify posts are deleted
        self.assertEqual(Post.objects.count(), 0)
    
    def test_delete_comments_shows_confirmation(self):
        """Test that deleting comments shows confirmation page"""
        # Create test post and comments
        post = Post.objects.create(user=self.test_user1, content='Test post')
        comment1 = Comment.objects.create(post=post, user=self.test_user1, content='Comment 1')
        comment2 = Comment.objects.create(post=post, user=self.test_user2, content='Comment 2')
        
        # Prepare POST data for bulk delete
        data = {
            'action': 'delete_selected_comments',
            '_selected_action': [comment1.pk, comment2.pk],
        }
        
        # Submit bulk action
        response = self.client.post('/admin/feed/comment/', data, follow=True)
        
        # Should show confirmation page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm deletion')
        self.assertContains(response, 'cannot be undone')
    
    def test_delete_comments_confirmation_executes_action(self):
        """Test that confirming deletion actually deletes comments"""
        # Create test post and comments
        post = Post.objects.create(user=self.test_user1, content='Test post')
        comment1 = Comment.objects.create(post=post, user=self.test_user1, content='Comment 1')
        comment2 = Comment.objects.create(post=post, user=self.test_user2, content='Comment 2')
        
        # Verify comments exist
        self.assertEqual(Comment.objects.count(), 2)
        
        # Prepare POST data with confirmation
        data = {
            'action': 'delete_selected_comments',
            '_selected_action': [comment1.pk, comment2.pk],
            'apply': 'yes',  # Confirmation flag
        }
        
        # Submit confirmed action
        response = self.client.post('/admin/feed/comment/', data, follow=True)
        
        # Should redirect back to changelist
        self.assertEqual(response.status_code, 200)
        
        # Verify comments are deleted
        self.assertEqual(Comment.objects.count(), 0)
    
    def test_non_destructive_actions_no_confirmation(self):
        """Test that non-destructive actions don't require confirmation"""
        # Test activate_users (non-destructive)
        self.test_user1.is_active = False
        self.test_user1.save()
        
        data = {
            'action': 'activate_users',
            '_selected_action': [self.test_user1.pk],
        }
        
        # Submit action
        response = self.client.post('/admin/users/user/', data, follow=True)
        
        # Should execute immediately without confirmation
        self.assertEqual(response.status_code, 200)
        self.test_user1.refresh_from_db()
        self.assertTrue(self.test_user1.is_active)

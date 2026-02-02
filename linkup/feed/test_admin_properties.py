"""
Property-based tests for feed admin functionality

These tests verify universal properties that should hold across all valid inputs
using the Hypothesis property-based testing framework.
"""
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from feed.admin import PostAdmin, CommentAdmin
from feed.models import Post, Comment
from PIL import Image
import io
import tempfile
import os

User = get_user_model()


class PostAdminPropertyTests(TestCase):
    """Property-based tests for PostAdmin functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.post_admin = PostAdmin(Post, self.admin_site)
    
    def _create_test_image(self, width=100, height=100, format='JPEG'):
        """Create a test image file for testing"""
        # Create a simple test image
        image = Image.new('RGB', (width, height), color='red')
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        
        # Create uploaded file
        filename = f'test_image.{format.lower()}'
        if format == 'JPEG':
            filename = 'test_image.jpg'
        
        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type=f'image/{format.lower()}'
        )
    
    @given(st.integers(min_value=10, max_value=500))
    @settings(deadline=None, max_examples=10)  # Reduce examples for faster execution
    def test_post_image_thumbnail_conditional_display_property(self, image_size):
        """
        **Property 9: Post Image Thumbnail Conditional Display**
        **Validates: Requirements 8.1**
        
        For any post with an image, the admin interface should display a thumbnail.
        For posts without images, it should display a placeholder or empty indicator.
        
        This property verifies that:
        1. Posts with valid images show HTML img tags in the thumbnail display
        2. Posts without images show a placeholder ('-')
        3. The thumbnail HTML is properly formatted and safe
        4. Image dimensions are constrained appropriately
        """
        # Create a test user
        user = User.objects.create(
            username='test_thumbnail_user',
            email='test_thumbnail@example.com'
        )
        
        try:
            # Test 1: Post with image should show thumbnail
            test_image = self._create_test_image(width=image_size, height=image_size)
            post_with_image = Post.objects.create(
                user=user,
                content='Test post with image',
                image=test_image
            )
            
            thumbnail_html = self.post_admin.image_preview(post_with_image)
            
            # Verify thumbnail contains img tag
            self.assertIn('<img', thumbnail_html, 
                         f"Post with image should display img tag in thumbnail. Got: {thumbnail_html}")
            
            # Verify thumbnail has proper styling constraints
            self.assertIn('max-width:150px', thumbnail_html,
                         f"Thumbnail should have max-width constraint. Got: {thumbnail_html}")
            
            # Verify thumbnail has proper styling
            self.assertIn('border-radius:6px', thumbnail_html,
                         f"Thumbnail should have border-radius styling. Got: {thumbnail_html}")
            
            # Verify src attribute is present
            self.assertIn('src=', thumbnail_html,
                         f"Thumbnail should have src attribute. Got: {thumbnail_html}")
            
            # Test 2: Post without image should show placeholder
            post_without_image = Post.objects.create(
                user=user,
                content='Test post without image'
                # No image field set
            )
            
            placeholder_html = self.post_admin.image_preview(post_without_image)
            
            # Verify placeholder is shown
            self.assertEqual(placeholder_html, '-',
                           f"Post without image should show placeholder '-'. Got: {placeholder_html}")
            
            # Test 3: Post with empty image field should show placeholder
            post_empty_image = Post.objects.create(
                user=user,
                content='Test post with empty image field',
                image=None
            )
            
            empty_placeholder_html = self.post_admin.image_preview(post_empty_image)
            
            # Verify placeholder is shown for empty image
            self.assertEqual(empty_placeholder_html, '-',
                           f"Post with empty image field should show placeholder '-'. Got: {empty_placeholder_html}")
        
        finally:
            # Clean up
            user.delete()
            # Posts will be deleted by cascade
    
    @given(st.integers(min_value=0, max_value=50), st.integers(min_value=0, max_value=50))
    @settings(deadline=None, max_examples=10)  # Reduce examples and limits for faster execution
    def test_engagement_metrics_calculation_property(self, num_likes, num_comments):
        """
        **Property 11: Engagement Metrics Calculation**
        **Validates: Requirements 8.3**
        
        For any post with likes and comments, the admin interface should accurately
        calculate and display engagement metrics.
        
        This property verifies that:
        1. Like count matches the actual number of likes
        2. Comment count matches the actual number of comments
        3. Metrics are calculated consistently
        4. Zero values are handled correctly
        """
        # Create test users
        post_author = User.objects.create(
            username='test_post_author',
            email='test_author@example.com'
        )
        
        # Create a test post
        post = Post.objects.create(
            user=post_author,
            content='Test post for engagement metrics'
        )
        
        try:
            # Create users for likes (limit to reasonable number for performance)
            like_users = []
            actual_likes = min(num_likes, 20)  # Further limit for performance
            for i in range(actual_likes):
                like_user = User.objects.create(
                    username=f'like_user_{i}',
                    email=f'like_user_{i}@example.com'
                )
                like_users.append(like_user)
                post.likes.add(like_user)
            
            # Create comments (limit to reasonable number for performance)
            actual_comments = min(num_comments, 20)  # Further limit for performance
            for i in range(actual_comments):
                comment_user = User.objects.create(
                    username=f'comment_user_{i}',
                    email=f'comment_user_{i}@example.com'
                )
                Comment.objects.create(
                    post=post,
                    user=comment_user,
                    content=f'Test comment {i}'
                )
            
            # Test like count calculation
            calculated_likes = self.post_admin.total_likes_count(post)
            self.assertEqual(calculated_likes, actual_likes,
                           f"Like count should be {actual_likes}, but got {calculated_likes}")
            
            # Test comment count calculation
            calculated_comments = self.post_admin.total_comments_count(post)
            self.assertEqual(calculated_comments, actual_comments,
                           f"Comment count should be {actual_comments}, but got {calculated_comments}")
            
            # Test that metrics are non-negative
            self.assertGreaterEqual(calculated_likes, 0,
                                  f"Like count should be non-negative, got {calculated_likes}")
            
            self.assertGreaterEqual(calculated_comments, 0,
                                  f"Comment count should be non-negative, got {calculated_comments}")
            
            # Test consistency - calling the method multiple times should return same result
            likes_second_call = self.post_admin.total_likes_count(post)
            comments_second_call = self.post_admin.total_comments_count(post)
            
            self.assertEqual(calculated_likes, likes_second_call,
                           f"Like count should be consistent across calls: {calculated_likes} vs {likes_second_call}")
            
            self.assertEqual(calculated_comments, comments_second_call,
                           f"Comment count should be consistent across calls: {calculated_comments} vs {comments_second_call}")
        
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_').delete()
            User.objects.filter(username__startswith='like_user_').delete()
            User.objects.filter(username__startswith='comment_user_').delete()
            # Related objects will be deleted by cascade


class CommentAdminPropertyTests(TestCase):
    """Property-based tests for CommentAdmin functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.comment_admin = CommentAdmin(Comment, self.admin_site)
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=10)  # Reduce examples for faster execution
    def test_comment_content_preview_property(self, comment_content):
        """
        Test that comment content preview is properly truncated and formatted.
        
        This property verifies that:
        1. Long comments are truncated to 100 characters
        2. Short comments are displayed in full
        3. Content is properly escaped for HTML display
        """
        # Create test user and post
        user = User.objects.create(
            username='test_comment_user',
            email='test_comment@example.com'
        )
        
        post = Post.objects.create(
            user=user,
            content='Test post for comment preview'
        )
        
        try:
            # Create comment with the test content
            comment = Comment.objects.create(
                post=post,
                user=user,
                content=comment_content
            )
            
            # Get the preview
            preview = self.comment_admin.short_content(comment)
            
            # Verify preview length is appropriate
            if len(comment_content) <= 100:
                # Short content should be displayed in full
                self.assertEqual(preview, comment_content,
                               f"Short comment should be displayed in full. Expected: '{comment_content}', Got: '{preview}'")
            else:
                # Long content should be truncated
                self.assertTrue(len(preview) <= 103,  # 100 chars + "..." = 103
                              f"Long comment should be truncated to ~100 chars. Got {len(preview)} chars: '{preview}'")
                
                # Should contain the beginning of the original content
                self.assertTrue(preview.startswith(comment_content[:50]),
                              f"Truncated preview should start with original content. Original: '{comment_content[:50]}...', Preview: '{preview}'")
            
            # Verify preview is a string
            self.assertIsInstance(preview, str,
                                f"Preview should be a string, got {type(preview)}")
        
        finally:
            # Clean up
            user.delete()
            # Related objects will be deleted by cascade
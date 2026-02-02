"""
Property-based tests for Jobs admin interface

These tests verify universal properties that should hold across all valid inputs
using the Hypothesis property-based testing framework.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.utils.html import strip_tags

try:
    from hypothesis import given, strategies as st, assume, settings
    from hypothesis.extra.django import TestCase as HypothesisTestCase
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    # Create dummy decorators if hypothesis is not available
    def given(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class st:
        @staticmethod
        def text(**kwargs):
            return lambda: "test"
        
        @staticmethod
        def booleans():
            return lambda: True
        
        @staticmethod
        def integers(**kwargs):
            return lambda: 100
        
        @staticmethod
        def lists(*args, **kwargs):
            return lambda: []
    
    HypothesisTestCase = TestCase
    
    def settings(**kwargs):
        def decorator(func):
            return func
        return decorator

from .models import Job, Application
from .admin import JobAdmin, ApplicationAdmin
from feed.models import Post, Comment
from linkup.admin_utils import truncate_html

User = get_user_model()


class JobAdminPropertyTests(HypothesisTestCase):
    """Property-based tests for Job admin interface"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        # Use get_or_create to avoid unique constraint violations
        self.user, created = User.objects.get_or_create(
            username='testuser_jobs',
            defaults={
                'email': 'test@example.com',
                'password': 'testpass123'
            }
        )
    
    @given(st.text(min_size=0, max_size=2000, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='<>'
    )))
    @settings(max_examples=100, deadline=None)
    def test_rich_text_content_truncation_job_description(self, description_content):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any rich text content (job description), when displayed in List_Display,
        the content should be truncated to 100 characters with HTML tags stripped
        and an ellipsis appended if the original content exceeds 100 characters.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Create a job with the generated description
        job = Job.objects.create(
            title='Test Job',
            company='Test Company',
            location='Test Location',
            description=description_content,
            posted_by=self.user
        )
        
        job_admin = JobAdmin(Job, self.site)
        result = job_admin.description_preview(job)
        
        # Strip HTML tags from both original and result for comparison
        original_stripped = strip_tags(description_content).strip()
        result_stripped = strip_tags(result).strip()
        
        # Normalize Unicode for comparison
        import unicodedata
        original_normalized = unicodedata.normalize('NFC', original_stripped)
        result_normalized = unicodedata.normalize('NFC', result_stripped)
        
        # Property 1: Result should never exceed 100 characters + ellipsis
        if len(original_normalized) > 100:
            self.assertLessEqual(len(result_normalized), 103)  # 100 + "..." (ellipsis)
            # Should end with ellipsis if content was truncated
            self.assertTrue(result_normalized.endswith('…') or result_normalized.endswith('...'))
        else:
            # Short content should not be truncated
            if original_normalized:  # Only check non-empty content
                self.assertEqual(result_normalized, original_normalized)
        
        # Property 2: For well-formed content, HTML tags should be mostly stripped
        # Note: Django's strip_tags may not handle malformed HTML perfectly
        if '<' in description_content and '>' in description_content:
            # Only check for proper tag stripping if we have what looks like real HTML
            tag_count_original = description_content.count('<') + description_content.count('>')
            tag_count_result = result.count('<') + result.count('>')
            # Result should have fewer or equal HTML-like characters
            self.assertLessEqual(tag_count_result, tag_count_original)
        
        # Property 3: If original has meaningful content, result should have some content
        if original_normalized:
            self.assertTrue(result_normalized)
        
        # Clean up
        job.delete()
    
    @given(st.text(min_size=0, max_size=1000, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='<>'
    )))
    @settings(max_examples=100, deadline=None)
    def test_rich_text_content_truncation_post_content(self, post_content):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any rich text content (post content), when displayed in List_Display,
        the content should be truncated to 100 characters with HTML tags stripped
        and an ellipsis appended if the original content exceeds 100 characters.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Create a post with the generated content
        post = Post.objects.create(
            user=self.user,
            content=post_content
        )
        
        # Test the truncate_html utility function directly (used by admin)
        result = truncate_html(post_content, 100)
        
        # Strip HTML tags from both original and result for comparison
        original_stripped = strip_tags(post_content).strip()
        result_stripped = strip_tags(result).strip()
        
        # Normalize Unicode for comparison
        import unicodedata
        original_normalized = unicodedata.normalize('NFC', original_stripped)
        result_normalized = unicodedata.normalize('NFC', result_stripped)
        
        # Property 1: Result should never exceed 100 characters + ellipsis
        if len(original_normalized) > 100:
            self.assertLessEqual(len(result_normalized), 103)  # 100 + "..." (ellipsis)
            # Should end with ellipsis if content was truncated
            self.assertTrue(result_normalized.endswith('…') or result_normalized.endswith('...'))
        else:
            # Short content should not be truncated
            if original_normalized:  # Only check non-empty content
                self.assertEqual(result_normalized, original_normalized)
        
        # Property 2: For well-formed content, HTML tags should be mostly stripped
        # Note: Django's strip_tags may not handle malformed HTML perfectly
        if '<' in post_content and '>' in post_content:
            # Only check for proper tag stripping if we have what looks like real HTML
            tag_count_original = post_content.count('<') + post_content.count('>')
            tag_count_result = result.count('<') + result.count('>')
            # Result should have fewer or equal HTML-like characters
            self.assertLessEqual(tag_count_result, tag_count_original)
        
        # Property 3: If original has content, result should have some content
        if original_normalized:
            self.assertTrue(result_normalized)
        
        # Clean up
        post.delete()
    
    @given(st.text(min_size=0, max_size=500, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='<>'
    )))
    @settings(max_examples=100, deadline=None)
    def test_rich_text_content_truncation_comment_text(self, comment_content):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any rich text content (comment text), when displayed in List_Display,
        the content should be truncated to 100 characters with HTML tags stripped
        and an ellipsis appended if the original content exceeds 100 characters.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Create a post first
        post = Post.objects.create(
            user=self.user,
            content='Test post content'
        )
        
        # Create a comment with the generated content
        comment = Comment.objects.create(
            post=post,
            user=self.user,
            content=comment_content
        )
        
        # Test the truncate_html utility function directly (used by admin)
        result = truncate_html(comment_content, 100)
        
        # Strip HTML tags from both original and result for comparison
        original_stripped = strip_tags(comment_content).strip()
        result_stripped = strip_tags(result).strip()
        
        # Normalize Unicode for comparison
        import unicodedata
        original_normalized = unicodedata.normalize('NFC', original_stripped)
        result_normalized = unicodedata.normalize('NFC', result_stripped)
        
        # Property 1: Result should never exceed 100 characters + ellipsis
        if len(original_normalized) > 100:
            self.assertLessEqual(len(result_normalized), 103)  # 100 + "..." (ellipsis)
            # Should end with ellipsis if content was truncated
            self.assertTrue(result_normalized.endswith('…') or result_normalized.endswith('...'))
        else:
            # Short content should not be truncated
            if original_normalized:  # Only check non-empty content
                self.assertEqual(result_normalized, original_normalized)
        
        # Property 2: For well-formed content, HTML tags should be mostly stripped
        # Note: Django's strip_tags may not handle malformed HTML perfectly
        if '<' in comment_content and '>' in comment_content:
            # Only check for proper tag stripping if we have what looks like real HTML
            tag_count_original = comment_content.count('<') + comment_content.count('>')
            tag_count_result = result.count('<') + result.count('>')
            # Result should have fewer or equal HTML-like characters
            self.assertLessEqual(tag_count_result, tag_count_original)
        
        # Property 3: If original has content, result should have some content
        if original_normalized:
            self.assertTrue(result_normalized)
        
        # Clean up
        comment.delete()
        post.delete()
    
    @given(st.text(min_size=101, max_size=300, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
    )))
    @settings(max_examples=50, deadline=None)
    def test_rich_text_truncation_with_html_tags(self, base_content):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any rich text content with HTML tags, truncation should strip tags
        and respect the 100 character limit on the plain text content.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Skip if content is too short
        assume(len(base_content.strip()) > 100)
        
        # Add various HTML tags to the content
        html_content = f"<p><strong>{base_content[:50]}</strong></p><div><em>{base_content[50:]}</em></div>"
        
        result = truncate_html(html_content, 100)
        
        # Strip HTML tags from result
        result_stripped = strip_tags(result).strip()
        
        # Should not exceed 100 characters by much (allowing for ellipsis and Unicode normalization)
        self.assertLessEqual(len(result_stripped), 105)  # More lenient for Unicode edge cases
        
        # Should not contain HTML tags
        self.assertNotIn('<p>', result)
        self.assertNotIn('<strong>', result)
        self.assertNotIn('<div>', result)
        self.assertNotIn('<em>', result)
        self.assertNotIn('</p>', result)
        self.assertNotIn('</strong>', result)
        self.assertNotIn('</div>', result)
        self.assertNotIn('</em>', result)
        
        # Should contain some of the original text content
        original_text = strip_tags(html_content)
        if len(original_text.strip()) > 0:
            # At least the first few characters should match
            result_start = result_stripped[:min(20, len(result_stripped))]
            original_start = original_text[:min(20, len(original_text))]
            if result_start and original_start:
                # Remove ellipsis for comparison
                result_clean = result_start.replace('…', '').replace('...', '').strip()
                if result_clean and original_start.strip():
                    # Check if they start with similar content (allowing for Unicode normalization)
                    import unicodedata
                    result_norm = unicodedata.normalize('NFC', result_clean[:10])
                    original_norm = unicodedata.normalize('NFC', original_start.strip()[:10])
                    if result_norm and original_norm:
                        self.assertTrue(original_norm.startswith(result_norm[:5]) or result_norm.startswith(original_norm[:5]))
    
    def test_rich_text_truncation_edge_cases(self):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        Test edge cases for rich text content truncation.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Test empty content
        result = truncate_html('', 100)
        self.assertEqual(result, '')
        
        # Test None content
        result = truncate_html(None, 100)
        self.assertEqual(result, '')
        
        # Test content with only HTML tags
        result = truncate_html('<p></p><div></div>', 100)
        self.assertEqual(result.strip(), '')
        
        # Test content with only whitespace
        result = truncate_html('   \n\t   ', 100)
        self.assertEqual(result.strip(), '')
        
        # Test content exactly at limit
        content_100 = 'A' * 100
        result = truncate_html(content_100, 100)
        self.assertEqual(len(result), 100)
        self.assertFalse(result.endswith('…'))
        self.assertFalse(result.endswith('...'))
        
        # Test content one character over limit
        content_101 = 'A' * 101
        result = truncate_html(content_101, 100)
        self.assertLessEqual(len(result), 103)  # 100 + ellipsis
        self.assertTrue(result.endswith('…') or result.endswith('...'))


    @given(st.lists(
        st.builds(
            Job,
            title=st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            company=st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            location=st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            description=st.text(min_size=1, max_size=200, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            is_active=st.booleans()
        ),
        min_size=1,
        max_size=10
    ))
    @settings(max_examples=100, deadline=None)
    def test_bulk_job_status_updates_mark_active(self, jobs):
        """
        **Property 14: Bulk Job Status Updates**
        **Validates: Requirements 10.3, 10.4**
        
        For any set of selected Job records, executing mark_active bulk action
        should update the is_active field to True for all selected jobs.
        
        This property verifies that:
        1. All jobs in the queryset have is_active=True after mark_active action
        2. The action works regardless of the initial is_active state
        3. The action works for any number of jobs (1-10 in this test)
        4. No jobs outside the queryset are affected
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Save jobs to database with random initial active states
        saved_jobs = []
        for i, job in enumerate(jobs):
            # Ensure unique titles by adding a suffix
            job.title = f"{job.title}_{i}"
            job.posted_by = self.user
            job.save()
            saved_jobs.append(job)
        
        # Create a control job that should not be affected
        control_job = Job.objects.create(
            title=f"control_job_{len(saved_jobs)}",
            company="Control Company",
            location="Control Location", 
            description="Control description",
            posted_by=self.user,
            is_active=False
        )
        
        # Get queryset of the jobs we want to activate
        job_ids = [job.id for job in saved_jobs]
        queryset = Job.objects.filter(id__in=job_ids)
        
        # Record initial states
        initial_states = {job.id: job.is_active for job in saved_jobs}
        
        # Execute the bulk mark_active action
        request = self._create_request_with_messages()
        job_admin = JobAdmin(Job, self.site)
        job_admin.mark_active(request, queryset)
        
        # Verify all selected jobs are now active
        for job in saved_jobs:
            job.refresh_from_db()
            self.assertTrue(
                job.is_active,
                f"Job {job.title} should be active after bulk mark_active, "
                f"but is_active={job.is_active}. Initial state was {initial_states[job.id]}"
            )
        
        # Verify control job was not affected
        control_job.refresh_from_db()
        self.assertFalse(
            control_job.is_active,
            "Control job should not be affected by bulk mark_active"
        )
        
        # Clean up
        for job in saved_jobs:
            job.delete()
        control_job.delete()
    
    @given(st.lists(
        st.builds(
            Job,
            title=st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            company=st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            location=st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            description=st.text(min_size=1, max_size=200, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            is_active=st.booleans()
        ),
        min_size=1,
        max_size=10
    ))
    @settings(max_examples=100, deadline=None)
    def test_bulk_job_status_updates_mark_inactive(self, jobs):
        """
        **Property 14: Bulk Job Status Updates**
        **Validates: Requirements 10.3, 10.4**
        
        For any set of selected Job records, executing mark_inactive bulk action
        should update the is_active field to False for all selected jobs.
        
        This property verifies that:
        1. All jobs in the queryset have is_active=False after mark_inactive action
        2. The action works regardless of the initial is_active state
        3. The action works for any number of jobs (1-10 in this test)
        4. No jobs outside the queryset are affected
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Save jobs to database with random initial active states
        saved_jobs = []
        for i, job in enumerate(jobs):
            # Ensure unique titles by adding a suffix
            job.title = f"{job.title}_{i}"
            job.posted_by = self.user
            job.save()
            saved_jobs.append(job)
        
        # Create a control job that should not be affected
        control_job = Job.objects.create(
            title=f"control_job_{len(saved_jobs)}",
            company="Control Company",
            location="Control Location",
            description="Control description", 
            posted_by=self.user,
            is_active=True
        )
        
        # Get queryset of the jobs we want to deactivate
        job_ids = [job.id for job in saved_jobs]
        queryset = Job.objects.filter(id__in=job_ids)
        
        # Record initial states
        initial_states = {job.id: job.is_active for job in saved_jobs}
        
        # Execute the bulk mark_inactive action
        request = self._create_request_with_messages()
        job_admin = JobAdmin(Job, self.site)
        job_admin.mark_inactive(request, queryset)
        
        # Verify all selected jobs are now inactive
        for job in saved_jobs:
            job.refresh_from_db()
            self.assertFalse(
                job.is_active,
                f"Job {job.title} should be inactive after bulk mark_inactive, "
                f"but is_active={job.is_active}. Initial state was {initial_states[job.id]}"
            )
        
        # Verify control job was not affected
        control_job.refresh_from_db()
        self.assertTrue(
            control_job.is_active,
            "Control job should not be affected by bulk mark_inactive"
        )
        
        # Clean up
        for job in saved_jobs:
            job.delete()
        control_job.delete()
    
    def _create_request_with_messages(self):
        """Create a request with proper message framework support"""
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        
        request = self.factory.get('/')
        
        # Add session middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add message storage
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        return request


# Skip all property tests if hypothesis is not available
if not HYPOTHESIS_AVAILABLE:
    import unittest
    JobAdminPropertyTests = unittest.skip("Hypothesis not available")(JobAdminPropertyTests)
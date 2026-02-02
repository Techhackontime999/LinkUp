"""
Property-based tests for admin utility functions
"""
import csv
import io
from django.test import TestCase, RequestFactory
from django.contrib.admin import ModelAdmin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.html import strip_tags

try:
    from hypothesis import given, strategies as st, assume
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

from .admin_utils import ExportCSVMixin, truncate_html, status_badge

User = get_user_model()


class MockModelAdmin(ModelAdmin, ExportCSVMixin):
    """Mock ModelAdmin class for testing ExportCSVMixin"""
    list_display = ('username', 'email', 'is_active')
    model = User


class AdminUtilsPropertyTests(HypothesisTestCase):
    """Property-based tests for admin utility functions"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = MockModelAdmin(User, None)
    
    @given(st.text(min_size=0, max_size=1000))
    def test_truncate_html_preserves_length_limit_property(self, content):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any content, truncation should limit output to specified length.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        length_limit = 100
        result = truncate_html(content, length_limit)
        
        # Strip any HTML tags that might be in the result
        plain_result = strip_tags(result)
        
        # The result should never exceed the length limit + ellipsis
        if len(strip_tags(content).strip()) > length_limit:
            self.assertLessEqual(len(plain_result), length_limit + 1)  # +1 for ellipsis character
        else:
            # Short content should not be truncated, but may have whitespace differences
            original_stripped = strip_tags(content).strip()
            result_stripped = plain_result.strip()
            if original_stripped:  # Only check if original has content
                self.assertEqual(result_stripped, original_stripped)
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ', min_size=1, max_size=50))
    def test_truncate_html_strips_all_html_tags_property(self, html_content):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any HTML content, truncation should strip all HTML tags.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Skip empty or whitespace-only content
        assume(html_content.strip())
        
        # Add some HTML tags to the content
        html_with_tags = f"<p>{html_content}</p><div><strong>test</strong></div>"
        result = truncate_html(html_with_tags, 200)
        
        # Result should not contain any HTML tags
        self.assertNotIn('<p>', result)
        self.assertNotIn('</p>', result)
        self.assertNotIn('<div>', result)
        self.assertNotIn('<strong>', result)
        
        # Should contain some of the original text content
        stripped_original = strip_tags(html_with_tags)
        if len(stripped_original) <= 200:
            # At least some words from the content should be present
            content_words = [word.strip() for word in html_content.split() if word.strip()]
            if content_words:
                self.assertTrue(any(word in result for word in content_words[:3]))  # Check first few words
    
    @given(st.booleans())
    def test_status_badge_generates_valid_html_property(self, status_value):
        """
        **Property 6: Status Badge Generation**
        **Validates: Requirements 3.8, 6.8**
        
        For any boolean status, status badge should generate valid HTML with appropriate styling.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        result = status_badge(status_value)
        
        # Should generate HTML span element
        self.assertIn('<span', result)
        self.assertIn('</span>', result)
        
        # Should contain style attributes
        self.assertIn('style=', result)
        self.assertIn('background-color:', result)
        self.assertIn('color: white', result)
        
        # Should contain appropriate color based on status
        if status_value:
            self.assertIn('#28a745', result)  # Green for true
            self.assertIn('Active', result)
        else:
            self.assertIn('#dc3545', result)  # Red for false
            self.assertIn('Inactive', result)
    
    @given(st.booleans(), 
           st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=20),
           st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=20))
    def test_status_badge_custom_labels_property(self, status_value, true_label, false_label):
        """
        **Property 6: Status Badge Generation**
        **Validates: Requirements 3.8, 6.8**
        
        For any boolean status and custom labels, badge should use the correct label.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Skip if labels are the same to avoid ambiguous test
        assume(true_label != false_label)
        
        result = status_badge(status_value, true_label, false_label)
        
        # Should contain the appropriate label in the visible content
        if status_value:
            self.assertIn(true_label, result)
        else:
            self.assertIn(false_label, result)
    
    def test_csv_export_structure_property(self):
        """
        **Property 16: CSV Export Structure**
        **Validates: Requirements 11.5, 11.6, 11.7**
        
        For any queryset, CSV export should have proper structure with headers and data.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Create some test users
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                is_active=i % 2 == 0
            )
            users.append(user)
        
        request = self.factory.get('/')
        queryset = User.objects.filter(username__startswith='testuser')
        
        response = self.admin.export_as_csv(request, queryset)
        
        # Should return proper HTTP response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Parse CSV content
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Should have header row plus data rows
        self.assertGreaterEqual(len(rows), 1)  # At least header
        self.assertEqual(len(rows), queryset.count() + 1)  # Header + data rows
        
        # Header should contain expected fields
        header = rows[0]
        self.assertIn('username', header)
        self.assertIn('email', header)
        self.assertIn('is_active', header)
        
        # Each data row should have same number of columns as header
        for row in rows[1:]:
            self.assertEqual(len(row), len(header))
    
    @given(st.integers(min_value=1, max_value=200))
    def test_truncate_html_length_parameter_property(self, length):
        """
        **Property 10: Rich Text Content Truncation**
        **Validates: Requirements 6.7, 8.2, 14.5**
        
        For any length parameter, truncation should respect the specified length.
        """
        if not HYPOTHESIS_AVAILABLE:
            self.skipTest("Hypothesis not available")
        
        # Create content longer than the specified length
        long_content = "A" * (length + 50)
        result = truncate_html(long_content, length)
        
        # Result should not exceed the specified length + ellipsis
        self.assertLessEqual(len(result), length + 1)
        
        # Should end with ellipsis if content was truncated
        if len(long_content) > length:
            self.assertTrue(result.endswith('…'))
    
    def test_export_csv_handles_empty_queryset_property(self):
        """
        **Property 16: CSV Export Structure**
        **Validates: Requirements 11.5, 11.6, 11.7**
        
        CSV export should handle empty querysets gracefully.
        """
        request = self.factory.get('/')
        queryset = User.objects.none()
        
        response = self.admin.export_as_csv(request, queryset)
        
        # Should still return valid CSV with headers
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Should have exactly one row (header only)
        self.assertEqual(len(rows), 1)
        
        # Header should still contain expected fields
        header = rows[0]
        self.assertIn('username', header)
        self.assertIn('email', header)
        self.assertIn('is_active', header)


# Skip all property tests if hypothesis is not available
if not HYPOTHESIS_AVAILABLE:
    import unittest
    AdminUtilsPropertyTests = unittest.skip("Hypothesis not available")(AdminUtilsPropertyTests)
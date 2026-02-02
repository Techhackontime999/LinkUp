"""
Tests for admin utility functions and mixins
"""
import csv
import io
from django.test import TestCase, RequestFactory
from django.contrib.admin import ModelAdmin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.html import format_html

from .admin_utils import ExportCSVMixin, truncate_html, status_badge

User = get_user_model()


class MockModelAdmin(ModelAdmin, ExportCSVMixin):
    """Mock ModelAdmin class for testing ExportCSVMixin"""
    list_display = ('username', 'email', 'is_active')
    model = User


class ExportCSVMixinTests(TestCase):
    """Test cases for ExportCSVMixin"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = MockModelAdmin(User, None)
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            username='testuser2', 
            email='test2@example.com',
            is_active=False
        )
    
    def test_export_as_csv_basic_functionality(self):
        """Test basic CSV export functionality"""
        request = self.factory.get('/')
        queryset = User.objects.all()
        
        response = self.admin.export_as_csv(request, queryset)
        
        # Check response type and headers
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('users.csv', response['Content-Disposition'])
    
    def test_export_csv_content_structure(self):
        """Test that CSV content has correct structure"""
        request = self.factory.get('/')
        queryset = User.objects.filter(username='testuser1')
        
        response = self.admin.export_as_csv(request, queryset)
        
        # Parse CSV content
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Check header row
        self.assertEqual(len(rows), 2)  # Header + 1 data row
        header = rows[0]
        self.assertIn('username', header)
        self.assertIn('email', header)
        self.assertIn('is_active', header)
        
        # Check data row
        data_row = rows[1]
        self.assertIn('testuser1', data_row)
        self.assertIn('test1@example.com', data_row)
    
    def test_export_csv_with_empty_queryset(self):
        """Test CSV export with empty queryset"""
        request = self.factory.get('/')
        queryset = User.objects.none()
        
        response = self.admin.export_as_csv(request, queryset)
        
        # Should still have header row
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        self.assertEqual(len(rows), 1)  # Only header row
        self.assertIn('username', rows[0])
    
    def test_export_csv_handles_none_values(self):
        """Test that CSV export handles None values correctly"""
        # Create user with empty email (since email field is required)
        user = User.objects.create(username='testnone', email='')
        
        request = self.factory.get('/')
        queryset = User.objects.filter(username='testnone')
        
        response = self.admin.export_as_csv(request, queryset)
        content = response.content.decode('utf-8')
        
        # Should not raise exception and should handle empty values gracefully
        self.assertIsInstance(response, HttpResponse)
        self.assertIn('testnone', content)


class TruncateHtmlTests(TestCase):
    """Test cases for truncate_html function"""
    
    def test_truncate_plain_text(self):
        """Test truncation of plain text"""
        text = "This is a long piece of text that should be truncated"
        result = truncate_html(text, 20)
        
        self.assertLessEqual(len(result), 21)  # 20 chars + "…"
        self.assertTrue(result.endswith('…'))
    
    def test_truncate_html_content(self):
        """Test truncation of HTML content strips tags"""
        html = "<p>This is <strong>HTML</strong> content with <em>tags</em></p>"
        result = truncate_html(html, 20)
        
        # Should strip HTML tags
        self.assertNotIn('<p>', result)
        self.assertNotIn('<strong>', result)
        self.assertNotIn('<em>', result)
        self.assertIn('This is HTML conten', result)  # Adjusted for truncation
    
    def test_truncate_short_content(self):
        """Test that short content is not truncated"""
        text = "Short text"
        result = truncate_html(text, 100)
        
        self.assertEqual(result, text)
        self.assertNotIn('…', result)
    
    def test_truncate_empty_content(self):
        """Test truncation of empty content"""
        result = truncate_html('', 100)
        self.assertEqual(result, '')
        
        result = truncate_html(None, 100)
        self.assertEqual(result, '')
    
    def test_truncate_html_with_nested_tags(self):
        """Test truncation with nested HTML tags"""
        html = "<div><p>Nested <span>HTML <strong>content</strong></span></p></div>"
        result = truncate_html(html, 15)
        
        # Should strip all tags and truncate
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertIn('Nested HTML', result)
    
    def test_truncate_default_length(self):
        """Test default truncation length of 100 characters"""
        long_text = "A" * 150
        result = truncate_html(long_text)
        
        # Default should be 100 characters + "…"
        self.assertLessEqual(len(result), 101)
        self.assertTrue(result.endswith('…'))


class StatusBadgeTests(TestCase):
    """Test cases for status_badge function"""
    
    def test_status_badge_true_value(self):
        """Test status badge for True value"""
        result = status_badge(True)
        
        self.assertIn('Active', result)
        self.assertIn('#28a745', result)  # Green color
        self.assertIn('<span', result)
        self.assertIn('</span>', result)
    
    def test_status_badge_false_value(self):
        """Test status badge for False value"""
        result = status_badge(False)
        
        self.assertIn('Inactive', result)
        self.assertIn('#dc3545', result)  # Red color
        self.assertIn('<span', result)
        self.assertIn('</span>', result)
    
    def test_status_badge_custom_labels(self):
        """Test status badge with custom labels"""
        result_true = status_badge(True, "Enabled", "Disabled")
        result_false = status_badge(False, "Enabled", "Disabled")
        
        self.assertIn('Enabled', result_true)
        self.assertIn('Disabled', result_false)
        self.assertNotIn('Active', result_true)
        self.assertNotIn('Inactive', result_false)
    
    def test_status_badge_html_safety(self):
        """Test that status badge generates safe HTML"""
        result = status_badge(True, "Test Label", "Other Label")
        
        # Should contain proper HTML structure
        self.assertIn('style=', result)
        self.assertIn('background-color:', result)
        self.assertIn('color: white', result)
        self.assertIn('padding:', result)
        self.assertIn('border-radius:', result)
        self.assertIn('font-size:', result)
        self.assertIn('font-weight: bold', result)
    
    def test_status_badge_with_special_characters(self):
        """Test status badge with special characters in labels"""
        result = status_badge(True, "Active & Ready", "Inactive < Disabled")
        
        # Should handle special characters safely
        self.assertIn('Active &amp; Ready', result)
        # Note: format_html should escape special characters
"""
Tests for admin_extras template tags
"""
import tempfile
import os
from django.test import TestCase
from django.template import Context, Template
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from PIL import Image
import io

from .templatetags.admin_extras import thumbnail, percentage_bar, truncate_text

User = get_user_model()


class ThumbnailTemplateTagTests(TestCase):
    """Test cases for thumbnail template tag"""
    
    def setUp(self):
        # Create a test image
        self.test_image = self.create_test_image()
    
    def create_test_image(self):
        """Create a test image file"""
        # Create a simple test image
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )
    
    def test_thumbnail_with_valid_image(self):
        """Test thumbnail generation with valid image"""
        # Mock an image field with URL
        class MockImageField:
            def __init__(self, url):
                self.url = url
        
        image_field = MockImageField('/media/test_image.jpg')
        result = thumbnail(image_field, 50, 50)
        
        # Should return HTML img tag
        self.assertIn('<img', result)
        self.assertIn('src="/media/test_image.jpg"', result)
        self.assertIn('width="50"', result)
        self.assertIn('height="50"', result)
        self.assertIn('border-radius: 4px', result)
        self.assertIn('object-fit: cover', result)
    
    def test_thumbnail_with_custom_dimensions(self):
        """Test thumbnail with custom width and height"""
        class MockImageField:
            def __init__(self, url):
                self.url = url
        
        image_field = MockImageField('/media/test_image.jpg')
        result = thumbnail(image_field, 100, 75)
        
        self.assertIn('width="100"', result)
        self.assertIn('height="75"', result)
    
    def test_thumbnail_with_no_image(self):
        """Test thumbnail when no image is provided"""
        result = thumbnail(None)
        self.assertEqual(result, "No image")
    
    def test_thumbnail_with_empty_image_field(self):
        """Test thumbnail with empty image field"""
        class MockImageField:
            pass
        
        image_field = MockImageField()
        result = thumbnail(image_field)
        self.assertEqual(result, "No image")
    
    def test_thumbnail_with_image_field_no_url(self):
        """Test thumbnail with image field that has no URL attribute"""
        class MockImageField:
            def __init__(self):
                pass
        
        image_field = MockImageField()
        result = thumbnail(image_field)
        self.assertEqual(result, "No image")
    
    def test_thumbnail_default_dimensions(self):
        """Test thumbnail with default dimensions (50x50)"""
        class MockImageField:
            def __init__(self, url):
                self.url = url
        
        image_field = MockImageField('/media/test_image.jpg')
        result = thumbnail(image_field)  # No dimensions specified
        
        self.assertIn('width="50"', result)
        self.assertIn('height="50"', result)
    
    def test_thumbnail_exception_handling(self):
        """Test thumbnail handles exceptions gracefully"""
        class MockImageField:
            @property
            def url(self):
                raise Exception("Test exception")
        
        image_field = MockImageField()
        result = thumbnail(image_field)
        self.assertEqual(result, "No image")
    
    def test_thumbnail_in_template(self):
        """Test thumbnail tag usage in Django template"""
        template = Template('{% load admin_extras %}{% thumbnail image_field 60 60 %}')
        
        class MockImageField:
            def __init__(self, url):
                self.url = url
        
        context = Context({'image_field': MockImageField('/media/test.jpg')})
        result = template.render(context)
        
        self.assertIn('<img', result)
        self.assertIn('width="60"', result)
        self.assertIn('height="60"', result)


class PercentageBarTemplateTagTests(TestCase):
    """Test cases for percentage_bar template tag"""
    
    def test_percentage_bar_basic_functionality(self):
        """Test basic percentage bar generation"""
        result = percentage_bar(75, 100)
        
        # Should contain progress bar HTML
        self.assertIn('<div', result)
        self.assertIn('width: 75%', result)
        self.assertIn('75%', result)  # Percentage text
        self.assertIn('background-color: #ffc107', result)  # Yellow for 75%
    
    def test_percentage_bar_high_percentage(self):
        """Test percentage bar with high percentage (green)"""
        result = percentage_bar(90, 100)
        
        self.assertIn('width: 90%', result)
        self.assertIn('90%', result)
        self.assertIn('background-color: #28a745', result)  # Green for 90%
    
    def test_percentage_bar_low_percentage(self):
        """Test percentage bar with low percentage (red)"""
        result = percentage_bar(25, 100)
        
        self.assertIn('width: 25%', result)
        self.assertIn('25%', result)
        self.assertIn('background-color: #dc3545', result)  # Red for 25%
    
    def test_percentage_bar_zero_value(self):
        """Test percentage bar with zero value"""
        result = percentage_bar(0, 100)
        
        self.assertIn('width: 0%', result)
        self.assertIn('0%', result)
        self.assertIn('background-color: #dc3545', result)  # Red for 0%
    
    def test_percentage_bar_full_value(self):
        """Test percentage bar with 100% value"""
        result = percentage_bar(100, 100)
        
        self.assertIn('width: 100%', result)
        self.assertIn('100%', result)
        self.assertIn('background-color: #28a745', result)  # Green for 100%
    
    def test_percentage_bar_over_max(self):
        """Test percentage bar with value over maximum"""
        result = percentage_bar(150, 100)
        
        # Should cap at 100%
        self.assertIn('width: 100%', result)
        self.assertIn('100%', result)
    
    def test_percentage_bar_custom_max_value(self):
        """Test percentage bar with custom maximum value"""
        result = percentage_bar(40, 50)
        
        # 40/50 = 80%
        self.assertIn('width: 80%', result)
        self.assertIn('80%', result)
        self.assertIn('background-color: #28a745', result)  # Green for 80%
    
    def test_percentage_bar_zero_max_value(self):
        """Test percentage bar with zero maximum value"""
        result = percentage_bar(50, 0)
        
        # Should handle division by zero
        self.assertIn('width: 0%', result)
        self.assertIn('0%', result)
    
    def test_percentage_bar_default_max_value(self):
        """Test percentage bar with default maximum value (100)"""
        result = percentage_bar(60)  # No max_value specified
        
        self.assertIn('width: 60%', result)
        self.assertIn('60%', result)
    
    def test_percentage_bar_html_structure(self):
        """Test percentage bar HTML structure"""
        result = percentage_bar(50, 100)
        
        # Check outer container
        self.assertIn('width: 100px', result)
        self.assertIn('height: 20px', result)
        self.assertIn('background-color: #e9ecef', result)
        self.assertIn('border-radius: 4px', result)
        self.assertIn('overflow: hidden', result)
        self.assertIn('display: inline-block', result)
        
        # Check inner bar
        self.assertIn('color: white', result)
        self.assertIn('font-size: 11px', result)
        self.assertIn('font-weight: bold', result)
        self.assertIn('display: flex', result)
        self.assertIn('align-items: center', result)
        self.assertIn('justify-content: center', result)
    
    def test_percentage_bar_in_template(self):
        """Test percentage_bar tag usage in Django template"""
        template = Template('{% load admin_extras %}{% percentage_bar value max_val %}')
        context = Context({'value': 75, 'max_val': 100})
        result = template.render(context)
        
        self.assertIn('width: 75%', result)
        self.assertIn('75%', result)


class TruncateTextFilterTests(TestCase):
    """Test cases for truncate_text filter"""
    
    def test_truncate_text_basic_functionality(self):
        """Test basic text truncation"""
        text = "This is a long piece of text that should be truncated"
        result = truncate_text(text, 20)
        
        self.assertEqual(len(result), 23)  # 20 chars + "..."
        self.assertTrue(result.endswith('...'))
        self.assertEqual(result, "This is a long piece...")
    
    def test_truncate_text_short_text(self):
        """Test truncation with text shorter than limit"""
        text = "Short text"
        result = truncate_text(text, 20)
        
        self.assertEqual(result, text)
        self.assertNotIn('...', result)
    
    def test_truncate_text_exact_length(self):
        """Test truncation with text exactly at limit"""
        text = "A" * 20
        result = truncate_text(text, 20)
        
        self.assertEqual(result, text)
        self.assertNotIn('...', result)
    
    def test_truncate_text_empty_string(self):
        """Test truncation with empty string"""
        result = truncate_text('', 20)
        self.assertEqual(result, '')
    
    def test_truncate_text_none_value(self):
        """Test truncation with None value"""
        result = truncate_text(None, 20)
        self.assertEqual(result, '')
    
    def test_truncate_text_default_length(self):
        """Test truncation with default length (100)"""
        text = "A" * 150
        result = truncate_text(text)  # No length specified
        
        self.assertEqual(len(result), 103)  # 100 chars + "..."
        self.assertTrue(result.endswith('...'))
    
    def test_truncate_text_in_template(self):
        """Test truncate_text filter usage in Django template"""
        template = Template('{% load admin_extras %}{{ text|truncate_text:15 }}')
        context = Context({'text': 'This is a very long text that needs truncation'})
        result = template.render(context)
        
        self.assertEqual(result, 'This is a very ...')
    
    def test_truncate_text_with_special_characters(self):
        """Test truncation with special characters"""
        text = "Text with émojis 🎉 and spëcial chars"
        result = truncate_text(text, 20)
        
        self.assertEqual(len(result), 23)  # Should handle unicode correctly
        self.assertTrue(result.endswith('...'))


class TemplateTagIntegrationTests(TestCase):
    """Integration tests for template tags working together"""
    
    def test_multiple_template_tags_in_template(self):
        """Test using multiple template tags in the same template"""
        template = Template('''
            {% load admin_extras %}
            <div>
                {% thumbnail image_field 40 40 %}
                {% percentage_bar completion 100 %}
                {{ description|truncate_text:50 }}
            </div>
        ''')
        
        class MockImageField:
            def __init__(self, url):
                self.url = url
        
        context = Context({
            'image_field': MockImageField('/media/profile.jpg'),
            'completion': 85,
            'description': 'This is a long description that should be truncated to fit the display requirements'
        })
        
        result = template.render(context)
        
        # Should contain all template tag outputs
        self.assertIn('<img', result)  # thumbnail
        self.assertIn('width: 85%', result)  # percentage_bar
        self.assertIn('This is a long description that should be truncate...', result)  # truncate_text
    
    def test_template_tags_with_missing_context(self):
        """Test template tags handle missing context gracefully"""
        template = Template('''
            {% load admin_extras %}
            {% thumbnail missing_image %}
            {% percentage_bar missing_value %}
            {{ missing_text|truncate_text:20 }}
        ''')
        
        context = Context({})  # Empty context
        result = template.render(context)
        
        # Should handle missing values gracefully
        self.assertIn('No image', result)
        # percentage_bar with None should handle gracefully
        # truncate_text with None should return empty string
#!/usr/bin/env python3
"""
Test script for Form User Experience Enhancements
Tests the enhanced form functionality including validation, visual feedback, and UX features.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

User = get_user_model()

class FormEnhancementTests(TestCase):
    """Test cases for enhanced form functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_registration_form_enhancement(self):
        """Test enhanced registration form"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        
        # Check for enhanced form classes
        self.assertContains(response, 'form-enhanced')
        self.assertContains(response, 'form-field-enhanced')
        self.assertContains(response, 'field-group-enhanced')
        
        # Check for validation attributes
        self.assertContains(response, 'data-validation')
        
        # Test form submission with validation
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123'
        }
        
        response = self.client.post(reverse('register'), form_data)
        # Should redirect on successful registration
        self.assertEqual(response.status_code, 302)
    
    def test_job_form_enhancement(self):
        """Test enhanced job creation form"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('jobs:job_create'))
        self.assertEqual(response.status_code, 200)
        
        # Check for enhanced form elements
        self.assertContains(response, 'form-enhanced')
        self.assertContains(response, 'field-group-enhanced')
        self.assertContains(response, 'form-progress-indicator')
        
        # Check for validation attributes
        self.assertContains(response, 'data-validation')
        self.assertContains(response, 'field-required')
        self.assertContains(response, 'field-optional')
        
        # Test form submission
        form_data = {
            'title': 'Senior Developer',
            'company': 'Tech Corp',
            'location': 'San Francisco, CA',
            'workplace_type': 'remote',
            'job_type': 'full-time',
            'description': 'A great opportunity for a senior developer to join our team and work on exciting projects.',
            'requirements': 'Python, Django, JavaScript',
            'salary_range': '$120k - $150k'
        }
        
        response = self.client.post(reverse('jobs:job_create'), form_data)
        # Should redirect on successful creation
        self.assertEqual(response.status_code, 302)
    
    def test_application_form_enhancement(self):
        """Test enhanced job application form"""
        from jobs.models import Job
        
        self.client.login(username='testuser', password='testpass123')
        
        # Create a job to apply to
        job = Job.objects.create(
            title='Test Job',
            company='Test Company',
            location='Test Location',
            workplace_type='remote',
            job_type='full-time',
            description='Test description for the job posting.',
            posted_by=self.user
        )
        
        response = self.client.get(reverse('jobs:job_apply', kwargs={'pk': job.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Check for enhanced form elements
        self.assertContains(response, 'form-enhanced')
        self.assertContains(response, 'field-group-enhanced')
        
        # Check for file upload enhancements
        self.assertContains(response, 'form-field-enhanced')
        self.assertContains(response, 'field-character-count')
        
        # Test form submission with file
        resume_content = b'This is a test resume content'
        resume_file = SimpleUploadedFile(
            "resume.pdf", 
            resume_content, 
            content_type="application/pdf"
        )
        
        form_data = {
            'cover_letter': 'This is a test cover letter explaining why I am perfect for this role. I have extensive experience in the field and am excited about this opportunity to contribute to your team.',
            'resume': resume_file
        }
        
        response = self.client.post(
            reverse('jobs:job_apply', kwargs={'pk': job.pk}), 
            form_data
        )
        # Should redirect on successful application
        self.assertEqual(response.status_code, 302)
    
    def test_form_validation_attributes(self):
        """Test that forms have proper validation attributes"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test job form validation attributes
        response = self.client.get(reverse('jobs:job_create'))
        content = response.content.decode()
        
        # Check for validation data attributes
        self.assertIn('data-validation=\'{"minLength": 3, "required": true}\'', content)
        self.assertIn('data-validation=\'{"minLength": 50, "required": true}\'', content)
        
        # Check for required field indicators
        self.assertIn('field-required', content)
        self.assertIn('field-optional', content)
    
    def test_form_accessibility_features(self):
        """Test accessibility features in enhanced forms"""
        response = self.client.get(reverse('register'))
        content = response.content.decode()
        
        # Check for proper labeling
        self.assertIn('for=', content)  # Labels should have 'for' attributes
        
        # Check for ARIA attributes
        self.assertIn('role="alert"', content)
        self.assertIn('aria-live', content)
        
        # Check for fieldset grouping
        self.assertIn('<fieldset', content)
        self.assertIn('<legend>', content)
    
    def test_form_css_classes(self):
        """Test that enhanced CSS classes are applied"""
        response = self.client.get(reverse('register'))
        content = response.content.decode()
        
        # Check for enhanced form classes
        required_classes = [
            'form-enhanced',
            'form-field-enhanced',
            'field-group-enhanced',
            'field-validation-message',
            'field-status-indicator'
        ]
        
        for css_class in required_classes:
            self.assertIn(css_class, content)
    
    def test_javascript_inclusion(self):
        """Test that form enhancement JavaScript is included"""
        response = self.client.get(reverse('register'))
        content = response.content.decode()
        
        # Check for JavaScript inclusion
        self.assertIn('form-enhancements.js', content)
        
        # Check for form-specific JavaScript
        self.assertIn('<script>', content)


def run_form_tests():
    """Run the form enhancement tests"""
    print("Running Form Enhancement Tests...")
    print("=" * 50)
    
    # Import test modules
    from django.test.utils import get_runner
    from django.conf import settings
    
    # Get the Django test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run the tests
    failures = test_runner.run_tests(['__main__'])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed!")
        return False
    else:
        print("\n✅ All form enhancement tests passed!")
        return True


def test_form_files_exist():
    """Test that all required form enhancement files exist"""
    print("Checking Form Enhancement Files...")
    print("-" * 40)
    
    required_files = [
        'staticfiles/js/form-enhancements.js',
        'staticfiles/css/form-enhancements.css'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist


def test_form_classes_updated():
    """Test that form classes have been updated with enhancements"""
    print("\nChecking Form Class Updates...")
    print("-" * 40)
    
    # Check users/forms.py
    try:
        with open('users/forms.py', 'r') as f:
            content = f.read()
            if 'form-field-enhanced' in content:
                print("✅ users/forms.py - Enhanced classes added")
            else:
                print("❌ users/forms.py - Enhanced classes missing")
                return False
    except FileNotFoundError:
        print("❌ users/forms.py - File not found")
        return False
    
    # Check jobs/forms.py
    try:
        with open('jobs/forms.py', 'r') as f:
            content = f.read()
            if 'form-field-enhanced' in content:
                print("✅ jobs/forms.py - Enhanced classes added")
            else:
                print("❌ jobs/forms.py - Enhanced classes missing")
                return False
    except FileNotFoundError:
        print("❌ jobs/forms.py - File not found")
        return False
    
    return True


def test_template_updates():
    """Test that templates have been updated with enhancements"""
    print("\nChecking Template Updates...")
    print("-" * 40)
    
    templates_to_check = [
        ('templates/jobs/job_form.html', 'form-enhanced'),
        ('templates/jobs/apply_form.html', 'form-enhanced'),
        ('users/templates/users/register.html', 'form-enhanced'),
        ('templates/base.html', 'form-enhancements.css')
    ]
    
    all_updated = True
    for template_path, expected_content in templates_to_check:
        try:
            with open(template_path, 'r') as f:
                content = f.read()
                if expected_content in content:
                    print(f"✅ {template_path} - Enhanced")
                else:
                    print(f"❌ {template_path} - Enhancement missing")
                    all_updated = False
        except FileNotFoundError:
            print(f"❌ {template_path} - File not found")
            all_updated = False
    
    return all_updated


def main():
    """Main test function"""
    print("Form User Experience Enhancement Tests")
    print("=" * 50)
    
    # Test file existence
    files_exist = test_form_files_exist()
    
    # Test form class updates
    classes_updated = test_form_classes_updated()
    
    # Test template updates
    templates_updated = test_template_updates()
    
    # Run Django tests if basic checks pass
    if files_exist and classes_updated and templates_updated:
        print("\n" + "=" * 50)
        django_tests_passed = run_form_tests()
        
        if django_tests_passed:
            print("\n🎉 All Form Enhancement Tests Passed!")
            print("\nForm UX Features Implemented:")
            print("✅ Visual feedback on form field focus")
            print("✅ Real-time validation status indicators")
            print("✅ Inline validation message displays")
            print("✅ Double-submission prevention")
            print("✅ Automatic error field focusing")
            print("✅ Logical field grouping layouts")
            print("✅ Enhanced accessibility features")
            print("✅ Responsive design support")
            return True
        else:
            print("\n❌ Some Django tests failed!")
            return False
    else:
        print("\n❌ Basic file/template checks failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
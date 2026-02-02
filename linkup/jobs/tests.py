from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from .models import Job, Application
from .admin import ApplicationInline, JobAdmin

User = get_user_model()


class ApplicationInlineTests(TestCase):
    """Test cases for ApplicationInline admin configuration"""
    
    def setUp(self):
        self.site = AdminSite()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.job = Job.objects.create(
            title='Test Job',
            company='Test Company',
            location='Test Location',
            description='Test description',
            posted_by=self.user
        )
    
    def test_application_inline_configuration(self):
        """Test that ApplicationInline has correct configuration"""
        # Test fields configuration
        expected_fields = ('applicant', 'status', 'applied_at')
        self.assertEqual(ApplicationInline.fields, expected_fields)
        
        # Test readonly_fields configuration
        expected_readonly = ('applied_at',)
        self.assertEqual(ApplicationInline.readonly_fields, expected_readonly)
        
        # Test autocomplete_fields configuration
        expected_autocomplete = ('applicant',)
        self.assertEqual(ApplicationInline.autocomplete_fields, expected_autocomplete)
        
        # Test model configuration
        self.assertEqual(ApplicationInline.model, Application)
        
        # Test extra configuration
        self.assertEqual(ApplicationInline.extra, 0)
    
    def test_application_inline_in_job_admin(self):
        """Test that ApplicationInline is properly included in JobAdmin"""
        job_admin = JobAdmin(Job, self.site)
        
        # Check that ApplicationInline is in the inlines
        self.assertIn(ApplicationInline, job_admin.inlines)
    
    def test_application_status_field_exists(self):
        """Test that Application model has status field with correct choices"""
        application = Application.objects.create(
            job=self.job,
            applicant=self.user,
            status='pending'
        )
        
        # Test that status field exists and has correct value
        self.assertEqual(application.status, 'pending')
        
        # Test that status choices are available
        expected_choices = [
            ('pending', 'Pending'),
            ('reviewed', 'Reviewed'),
            ('interview', 'Interview'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ]
        self.assertEqual(Application.STATUS_CHOICES, expected_choices)


class ApplicationAdminTests(TestCase):
    """Test cases for ApplicationAdmin configuration"""
    
    def setUp(self):
        self.site = AdminSite()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.job = Job.objects.create(
            title='Test Job',
            company='Test Company',
            location='Test Location',
            description='Test description',
            posted_by=self.user
        )
    
    def test_application_admin_includes_status_in_list_display(self):
        """Test that ApplicationAdmin includes status in list_display"""
        from .admin import ApplicationAdmin
        
        # Check that status is in list_display
        self.assertIn('status', ApplicationAdmin.list_display)
        
        # Check that status is in list_filter
        self.assertIn('status', ApplicationAdmin.list_filter)
    
    def test_job_title_method(self):
        """Test that job_title method returns correct job title"""
        from .admin import ApplicationAdmin
        
        application = Application.objects.create(
            job=self.job,
            applicant=self.user,
            cover_letter='Test cover letter'
        )
        
        app_admin = ApplicationAdmin(Application, self.site)
        result = app_admin.job_title(application)
        
        self.assertEqual(result, 'Test Job')
    
    def test_cover_letter_preview_method(self):
        """Test that cover_letter_preview method truncates long text"""
        from .admin import ApplicationAdmin
        
        long_cover_letter = 'This is a very long cover letter that should be truncated when displayed in the admin interface to ensure it fits properly in the list view without taking up too much space and overwhelming the display.'
        
        application = Application.objects.create(
            job=self.job,
            applicant=self.user,
            cover_letter=long_cover_letter
        )
        
        app_admin = ApplicationAdmin(Application, self.site)
        result = app_admin.cover_letter_preview(application)
        
        # Should be truncated to 100 characters
        self.assertEqual(len(result), 100)
        self.assertTrue(result.endswith('…'))
    
    def test_cover_letter_preview_empty(self):
        """Test that cover_letter_preview method handles empty cover letter"""
        from .admin import ApplicationAdmin
        
        application = Application.objects.create(
            job=self.job,
            applicant=self.user,
            cover_letter=''
        )
        
        app_admin = ApplicationAdmin(Application, self.site)
        result = app_admin.cover_letter_preview(application)
        
        self.assertEqual(result, '-')

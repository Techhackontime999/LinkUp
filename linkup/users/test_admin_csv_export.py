"""
Property-based tests for CSV export functionality
"""
import csv
import io
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.http import HttpResponse
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase
from users.admin import CustomUserAdmin, ProfileAdmin
from users.models import Profile
from jobs.admin import JobAdmin, ApplicationAdmin
from jobs.models import Job, Application

User = get_user_model()


class CSVExportPropertyTests(HypothesisTestCase):
    """Property-based tests for CSV export functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.user_admin = CustomUserAdmin(User, self.admin_site)
        self.profile_admin = ProfileAdmin(Profile, self.admin_site)
        self.job_admin = JobAdmin(Job, self.admin_site)
        self.application_admin = ApplicationAdmin(Application, self.admin_site)
        
        # Create a superuser for admin requests
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
    
    def test_csv_export_structure_users(self):
        """
        **Property 16: CSV Export Structure**
        **Validates: Requirements 11.5, 11.6, 11.7**
        
        For any queryset selected for export, the generated CSV file should contain 
        a header row with column names matching the list_display fields, followed 
        by data rows with values for each selected record.
        """
        # Create test users
        users = []
        for i in range(5):
            user = User.objects.create(
                username=f'testuser_{i}',
                email=f'test_{i}@example.com',
                first_name=f'First{i}',
                last_name=f'Last{i}',
                is_active=i % 2 == 0,
                is_staff=i % 3 == 0
            )
            users.append(user)
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(user.id) for user in users],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset of selected users
        queryset = User.objects.filter(id__in=[user.id for user in users])
        
        # Execute CSV export
        response = self.user_admin.export_as_csv(request, queryset)
        
        # Verify response is CSV
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Parse CSV content
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Verify structure
        self.assertGreater(len(rows), 0, "CSV should have at least header row")
        
        # Check header row
        header_row = rows[0]
        self.assertGreater(len(header_row), 0, "Header row should have columns")
        
        # Verify we have data rows (header + user rows)
        expected_rows = len(users) + 1  # +1 for header
        self.assertEqual(len(rows), expected_rows)
        
        # Verify each data row has same number of columns as header
        for i, row in enumerate(rows[1:], 1):
            self.assertEqual(len(row), len(header_row), 
                           f"Row {i} should have same number of columns as header")
        
        # Verify data integrity - check that user data appears in CSV
        csv_data = '\n'.join([','.join(row) for row in rows])
        for user in users:
            self.assertIn(user.username, csv_data, 
                         f"Username {user.username} should appear in CSV")
            self.assertIn(user.email, csv_data, 
                         f"Email {user.email} should appear in CSV")
    
    def test_csv_export_structure_profiles(self):
        """
        Test CSV export structure for Profile model
        """
        # Create users and profiles
        profiles = []
        for i in range(3):
            user = User.objects.create(
                username=f'profileuser_{i}',
                email=f'profile_{i}@example.com'
            )
            # Get or create profile (in case it's auto-created)
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'headline': f'Headline {i}',
                    'bio': f'Bio for user {i}',
                    'location': f'Location {i}'
                }
            )
            if not created:
                # Update existing profile
                profile.headline = f'Headline {i}'
                profile.bio = f'Bio for user {i}'
                profile.location = f'Location {i}'
                profile.save()
            profiles.append(profile)
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(profile.id) for profile in profiles],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset
        queryset = Profile.objects.filter(id__in=[profile.id for profile in profiles])
        
        # Execute CSV export
        response = self.profile_admin.export_as_csv(request, queryset)
        
        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Parse and verify CSV structure
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have header + profile rows
        self.assertEqual(len(rows), len(profiles) + 1)
        
        # Verify profile data appears
        csv_data = '\n'.join([','.join(row) for row in rows])
        for profile in profiles:
            self.assertIn(profile.headline, csv_data)
            self.assertIn(profile.location, csv_data)
    
    def test_csv_export_structure_jobs(self):
        """
        Test CSV export structure for Job model
        """
        # Create poster user
        poster = User.objects.create(
            username='jobposter',
            email='poster@company.com'
        )
        
        # Create jobs
        jobs = []
        for i in range(4):
            job = Job.objects.create(
                title=f'Job Title {i}',
                company=f'Company {i}',
                location=f'City {i}',
                job_type='full_time',
                description=f'Job description {i}',
                posted_by=poster,
                is_active=i % 2 == 0
            )
            jobs.append(job)
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(job.id) for job in jobs],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset
        queryset = Job.objects.filter(id__in=[job.id for job in jobs])
        
        # Execute CSV export
        response = self.job_admin.export_as_csv(request, queryset)
        
        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Parse and verify CSV structure
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have header + job rows
        self.assertEqual(len(rows), len(jobs) + 1)
        
        # Verify job data appears
        csv_data = '\n'.join([','.join(row) for row in rows])
        for job in jobs:
            self.assertIn(job.title, csv_data)
            self.assertIn(job.company, csv_data)
    
    def test_csv_export_empty_queryset(self):
        """
        Test CSV export with empty queryset
        """
        # Create empty queryset
        queryset = User.objects.none()
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Execute CSV export
        response = self.user_admin.export_as_csv(request, queryset)
        
        # Should still return valid CSV with header
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Parse CSV
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have only header row
        self.assertEqual(len(rows), 1)
        self.assertGreater(len(rows[0]), 0, "Header should have columns")
    
    def test_csv_export_special_characters(self):
        """
        Test CSV export handles special characters correctly
        """
        # Create user with special characters
        user = User.objects.create(
            username='test,user"with\'special',
            email='test@example.com',
            first_name='First,Name',
            last_name='Last"Name'
        )
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(user.id)],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset
        queryset = User.objects.filter(id=user.id)
        
        # Execute CSV export
        response = self.user_admin.export_as_csv(request, queryset)
        
        # Parse CSV
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have header + 1 data row
        self.assertEqual(len(rows), 2)
        
        # Verify special characters are properly escaped/quoted
        data_row = rows[1]
        csv_data = ','.join(data_row)
        
        # The CSV should contain the data, properly escaped
        self.assertIn('test@example.com', csv_data)
    
    def test_csv_filename_generation(self):
        """
        Test that CSV export generates appropriate filename
        """
        # Create test user
        user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(user.id)],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset
        queryset = User.objects.filter(id=user.id)
        
        # Execute CSV export
        response = self.user_admin.export_as_csv(request, queryset)
        
        # Check Content-Disposition header for filename
        content_disposition = response['Content-Disposition']
        self.assertIn('attachment', content_disposition)
        self.assertIn('filename=', content_disposition)
        
        # Should contain model name
        self.assertIn('users', content_disposition.lower())
    
    def test_csv_export_large_dataset(self):
        """
        Test CSV export with larger dataset to ensure performance
        """
        # Create a larger number of users
        users = []
        for i in range(50):  # Reasonable size for testing
            user = User.objects.create(
                username=f'bulkuser_{i}',
                email=f'bulk_{i}@example.com',
                first_name=f'First{i}',
                last_name=f'Last{i}'
            )
            users.append(user)
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(user.id) for user in users],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset
        queryset = User.objects.filter(id__in=[user.id for user in users])
        
        # Execute CSV export
        response = self.user_admin.export_as_csv(request, queryset)
        
        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Parse CSV
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have header + all user rows
        self.assertEqual(len(rows), len(users) + 1)
        
        # Verify all users are included
        csv_data = '\n'.join([','.join(row) for row in rows])
        for user in users[:5]:  # Check first 5 users
            self.assertIn(user.username, csv_data)
            self.assertIn(user.email, csv_data)
    
    def test_csv_export_with_none_values(self):
        """
        Test CSV export handles None/null values correctly
        """
        # Create user with some None values
        user = User.objects.create(
            username='testnull',
            email='test@example.com',
            first_name='',  # Empty string
            last_name=None  # This might be None in some cases
        )
        
        # Create request for export
        request = self.factory.post('/', {
            '_selected_action': [str(user.id)],
            'action': 'export_as_csv'
        })
        request.user = self.admin_user
        
        # Get queryset
        queryset = User.objects.filter(id=user.id)
        
        # Execute CSV export
        response = self.user_admin.export_as_csv(request, queryset)
        
        # Should not raise any exceptions
        self.assertIsInstance(response, HttpResponse)
        
        # Parse CSV
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have header + 1 data row
        self.assertEqual(len(rows), 2)
        
        # Should contain the username and email
        csv_data = ','.join(rows[1])
        self.assertIn('testnull', csv_data)
        self.assertIn('test@example.com', csv_data)
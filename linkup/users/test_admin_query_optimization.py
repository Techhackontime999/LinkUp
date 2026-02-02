"""
Property-based tests for admin query optimization

These tests verify that admin classes properly use select_related and prefetch_related
for query optimization as specified in the design document.
"""
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import override_settings
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from users.admin import CustomUserAdmin, ProfileAdmin, ExperienceAdmin, EducationAdmin
from users.models import User, Profile, Experience, Education

User = get_user_model()


class QueryOptimizationPropertyTests(TestCase):
    """Property-based tests for admin query optimization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.user_admin = CustomUserAdmin(User, self.admin_site)
        self.profile_admin = ProfileAdmin(Profile, self.admin_site)
        self.experience_admin = ExperienceAdmin(Experience, self.admin_site)
        self.education_admin = EducationAdmin(Education, self.admin_site)
    
    def test_user_admin_select_related_optimization(self):
        """
        **Property 19: Query Optimization with select_related**
        **Validates: Requirements 14.1**
        
        For any ModelAdmin with foreign key fields in list_display, the queryset 
        should use select_related() for those foreign key relationships to minimize 
        database queries.
        
        This property verifies that:
        1. UserAdmin uses select_related('profile') for the profile relationship
        2. The optimization is applied to the queryset returned by get_queryset()
        3. The optimization reduces the number of database queries when accessing related fields
        """
        # Create test users with profiles
        users = []
        for i in range(3):
            user = User.objects.create(
                username=f'test_user_{i}',
                email=f'test{i}@example.com',
                first_name=f'First{i}',
                last_name=f'Last{i}'
            )
            # Profile is automatically created by signal
            profile = user.profile
            profile.headline = f'Test headline {i}'
            profile.save()
            users.append(user)
        
        try:
            # Create a mock request
            request = self.factory.get('/')
            
            # Get the optimized queryset from UserAdmin
            queryset = self.user_admin.get_queryset(request)
            
            # Verify that select_related is applied
            # Check the query's select_related fields
            self.assertIn('profile', queryset.query.select_related)
            
            # Test that accessing profile doesn't cause additional queries
            # Note: UserAdmin also uses prefetch_related for experiences and educations
            # So we expect: 1 query for users+profiles + 1 for experiences + 1 for educations = 3 total
            with self.assertNumQueries(3):  
                list_items = list(queryset[:3])  # Get first 3 items
                for user in list_items:
                    # Accessing profile should not cause additional queries due to select_related
                    _ = user.profile.headline
            
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_user_').delete()
    
    def test_user_admin_prefetch_related_optimization(self):
        """
        **Property 20: Query Optimization with prefetch_related**
        **Validates: Requirements 14.2**
        
        For any ModelAdmin that displays counts or data from reverse foreign key 
        relationships, the queryset should use prefetch_related() for those relationships.
        
        This property verifies that:
        1. UserAdmin uses prefetch_related for experiences and educations relationships
        2. The optimization is applied to the queryset returned by get_queryset()
        3. The optimization reduces queries when accessing reverse foreign key relationships
        """
        # Create test users with experiences and educations
        users = []
        for i in range(2):
            user = User.objects.create(
                username=f'test_user_prefetch_{i}',
                email=f'testprefetch{i}@example.com'
            )
            
            # Create experiences for each user
            for j in range(2):
                Experience.objects.create(
                    user=user,
                    title=f'Job {j}',
                    company=f'Company {j}',
                    start_date='2020-01-01',
                    is_current=(j == 0)
                )
            
            # Create educations for each user
            for j in range(2):
                Education.objects.create(
                    user=user,
                    school=f'School {j}',
                    degree=f'Degree {j}',
                    field_of_study=f'Field {j}',
                    start_date='2015-01-01',
                    end_date='2019-01-01'
                )
            
            users.append(user)
        
        try:
            # Create a mock request
            request = self.factory.get('/')
            
            # Get the optimized queryset from UserAdmin
            queryset = self.user_admin.get_queryset(request)
            
            # Verify that prefetch_related is applied
            # Check the query's prefetch_related lookups
            prefetch_lookups = queryset._prefetch_related_lookups
            self.assertIn('experiences', prefetch_lookups)
            self.assertIn('educations', prefetch_lookups)
            
            # Test that accessing related objects doesn't cause N+1 queries
            # Should be: 1 query for users + 1 for experiences + 1 for educations = 3 total
            with self.assertNumQueries(3):
                list_items = list(queryset)
                for user in list_items:
                    # Accessing experiences and educations should not cause additional queries
                    _ = list(user.experiences.all())
                    _ = list(user.educations.all())
            
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_user_prefetch_').delete()
    
    def test_profile_admin_select_related_optimization(self):
        """
        **Property 19: Query Optimization with select_related (ProfileAdmin)**
        **Validates: Requirements 14.1**
        
        ProfileAdmin should use select_related('user') for the user foreign key.
        """
        # Create test users with profiles
        users = []
        for i in range(3):
            user = User.objects.create(
                username=f'test_profile_user_{i}',
                email=f'testprofile{i}@example.com'
            )
            users.append(user)
        
        try:
            # Create a mock request
            request = self.factory.get('/')
            
            # Get the optimized queryset from ProfileAdmin
            queryset = self.profile_admin.get_queryset(request)
            
            # Verify that select_related is applied
            self.assertIn('user', queryset.query.select_related)
            
            # Test that accessing user doesn't cause additional queries
            with self.assertNumQueries(1):  # Should be just one query due to select_related
                profiles = list(queryset[:3])
                for profile in profiles:
                    # Accessing user should not cause additional queries
                    _ = profile.user.username
                    _ = profile.user.email
            
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_profile_user_').delete()
    
    def test_experience_admin_select_related_optimization(self):
        """
        **Property 19: Query Optimization with select_related (ExperienceAdmin)**
        **Validates: Requirements 14.1**
        
        ExperienceAdmin should use select_related('user') for the user foreign key.
        """
        # Create test users with experiences
        users = []
        experiences = []
        for i in range(3):
            user = User.objects.create(
                username=f'test_exp_user_{i}',
                email=f'testexp{i}@example.com'
            )
            users.append(user)
            
            experience = Experience.objects.create(
                user=user,
                title=f'Job {i}',
                company=f'Company {i}',
                start_date='2020-01-01',
                is_current=True
            )
            experiences.append(experience)
        
        try:
            # Create a mock request
            request = self.factory.get('/')
            
            # Get the optimized queryset from ExperienceAdmin
            queryset = self.experience_admin.get_queryset(request)
            
            # Verify that select_related is applied
            self.assertIn('user', queryset.query.select_related)
            
            # Test that accessing user doesn't cause additional queries
            with self.assertNumQueries(1):  # Should be just one query due to select_related
                exp_list = list(queryset[:3])
                for experience in exp_list:
                    # Accessing user should not cause additional queries
                    _ = experience.user.username
                    _ = experience.user.email
            
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_exp_user_').delete()
    
    def test_education_admin_select_related_optimization(self):
        """
        **Property 19: Query Optimization with select_related (EducationAdmin)**
        **Validates: Requirements 14.1**
        
        EducationAdmin should use select_related('user') for the user foreign key.
        """
        # Create test users with educations
        users = []
        educations = []
        for i in range(3):
            user = User.objects.create(
                username=f'test_edu_user_{i}',
                email=f'testedu{i}@example.com'
            )
            users.append(user)
            
            education = Education.objects.create(
                user=user,
                school=f'School {i}',
                degree=f'Degree {i}',
                field_of_study=f'Field {i}',
                start_date='2015-01-01',
                end_date='2019-01-01'
            )
            educations.append(education)
        
        try:
            # Create a mock request
            request = self.factory.get('/')
            
            # Get the optimized queryset from EducationAdmin
            queryset = self.education_admin.get_queryset(request)
            
            # Verify that select_related is applied
            self.assertIn('user', queryset.query.select_related)
            
            # Test that accessing user doesn't cause additional queries
            with self.assertNumQueries(1):  # Should be just one query due to select_related
                edu_list = list(queryset[:3])
                for education in edu_list:
                    # Accessing user should not cause additional queries
                    _ = education.user.username
                    _ = education.user.email
            
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_edu_user_').delete()
    
    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=3)
    def test_query_optimization_scales_with_data_size(self, num_users):
        """
        **Property 19 & 20: Query Optimization Scaling**
        **Validates: Requirements 14.1, 14.2**
        
        For any number of users, the query optimization should maintain consistent 
        query counts regardless of the dataset size.
        """
        # Create test users with related data
        users = []
        for i in range(num_users):
            user = User.objects.create(
                username=f'test_scale_user_{i}',
                email=f'testscale{i}@example.com'
            )
            
            # Add profile data
            profile = user.profile
            profile.headline = f'Headline {i}'
            profile.save()
            
            # Add experience
            Experience.objects.create(
                user=user,
                title=f'Job {i}',
                company=f'Company {i}',
                start_date='2020-01-01',
                is_current=True
            )
            
            # Add education
            Education.objects.create(
                user=user,
                school=f'School {i}',
                degree=f'Degree {i}',
                field_of_study=f'Field {i}',
                start_date='2015-01-01',
                end_date='2019-01-01'
            )
            
            users.append(user)
        
        try:
            # Create a mock request
            request = self.factory.get('/')
            
            # Test UserAdmin query optimization
            user_queryset = self.user_admin.get_queryset(request)
            
            # Query count should be constant regardless of num_users
            # 1 query for users + 1 for experiences + 1 for educations = 3 total
            with self.assertNumQueries(3):
                user_list = list(user_queryset)
                for user in user_list:
                    _ = user.profile.headline  # select_related optimization
                    _ = list(user.experiences.all())  # prefetch_related optimization
                    _ = list(user.educations.all())  # prefetch_related optimization
            
            # Test ProfileAdmin query optimization
            profile_queryset = self.profile_admin.get_queryset(request)
            
            # Should be 1 query due to select_related('user')
            with self.assertNumQueries(1):
                profile_list = list(profile_queryset)
                for profile in profile_list:
                    _ = profile.user.username  # select_related optimization
            
        finally:
            # Clean up
            User.objects.filter(username__startswith='test_scale_user_').delete()
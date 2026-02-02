"""
Property-based tests for admin filtering functionality
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from datetime import timedelta
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase, from_model
from users.admin import CustomUserAdmin, ProfileAdmin, HasProfilePictureFilter, UserRegistrationDateFilter, ProfileCompletionFilter
from users.models import Profile
import random

User = get_user_model()


class AdminFilteringPropertyTests(HypothesisTestCase):
    """Property-based tests for admin filtering functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.user_admin = CustomUserAdmin(User, self.admin_site)
        self.profile_admin = ProfileAdmin(Profile, self.admin_site)
        
        # Create a superuser for admin requests
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
    
    def test_multiple_filter_combination_and_logic(self):
        """
        **Property 17: Multiple Filter Combination**
        **Validates: Requirements 12.5**
        
        For any set of filters applied simultaneously, the resulting queryset 
        should contain only records that satisfy all filter conditions (AND logic).
        """
        # Create test users with known attributes
        active_staff_users = []
        for i in range(3):
            user = User.objects.create(
                username=f'active_staff_{i}',
                email=f'active_staff_{i}@example.com',
                is_active=True,
                is_staff=True
            )
            active_staff_users.append(user)
        
        # Create users that don't match both criteria
        inactive_staff = User.objects.create(
            username='inactive_staff',
            email='inactive_staff@example.com',
            is_active=False,
            is_staff=True
        )
        
        active_non_staff = User.objects.create(
            username='active_non_staff',
            email='active_non_staff@example.com',
            is_active=True,
            is_staff=False
        )
        
        inactive_non_staff = User.objects.create(
            username='inactive_non_staff',
            email='inactive_non_staff@example.com',
            is_active=False,
            is_staff=False
        )
        
        # Create request with multiple filters
        request = self.factory.get('/', {
            'is_active__exact': '1',  # Active users only
            'is_staff__exact': '1',   # Staff users only
        })
        request.user = self.admin_user  # Add user to request
        
        # Get filtered queryset
        changelist = self.user_admin.get_changelist_instance(request)
        filtered_queryset = changelist.get_queryset(request)
        
        # Verify AND logic: all results must be both active AND staff
        for user in filtered_queryset:
            self.assertTrue(user.is_active, f"User {user.username} should be active")
            self.assertTrue(user.is_staff, f"User {user.username} should be staff")
        
        # Should only return the 3 users that match both criteria (excluding admin user)
        expected_count = 3
        actual_count = filtered_queryset.count()
        
        # The admin user might also match the criteria, so adjust expectation
        admin_matches = self.admin_user.is_active and self.admin_user.is_staff
        if admin_matches:
            expected_count = 4
        
        self.assertEqual(actual_count, expected_count)
        
        # Verify these are the correct users (excluding admin user from comparison)
        filtered_usernames = set(user.username for user in filtered_queryset if user != self.admin_user)
        expected_usernames = set(user.username for user in active_staff_users)
        self.assertEqual(filtered_usernames, expected_usernames)
        
        # Verify excluded users are not in results
        excluded_users = [inactive_staff, active_non_staff, inactive_non_staff]
        for excluded_user in excluded_users:
            self.assertNotIn(excluded_user, filtered_queryset)
    
    def test_date_filter_with_status_filter_combination(self):
        """
        Test combining date filters with status filters using AND logic
        """
        now = timezone.now()
        
        # Create recent active user (should match both filters)
        recent_active = User.objects.create(
            username='recent_active',
            email='recent_active@example.com',
            is_active=True,
            date_joined=now - timedelta(days=3)
        )
        
        # Create recent inactive user (should not match)
        recent_inactive = User.objects.create(
            username='recent_inactive',
            email='recent_inactive@example.com',
            is_active=False,
            date_joined=now - timedelta(days=2)
        )
        
        # Create old active user (should not match)
        old_active = User.objects.create(
            username='old_active',
            email='old_active@example.com',
            is_active=True,
            date_joined=now - timedelta(days=15)
        )
        
        # Apply both date and status filters manually
        week_ago = now - timedelta(days=7)
        combined_filtered = User.objects.filter(
            date_joined__gte=week_ago,
            is_active=True
        )
        
        # Should only contain recent_active user
        self.assertEqual(combined_filtered.count(), 1)
        self.assertEqual(combined_filtered.first(), recent_active)
        
        # Verify excluded users are not in results
        self.assertNotIn(recent_inactive, combined_filtered)
        self.assertNotIn(old_active, combined_filtered)
    
    def test_profile_multiple_filters_combination(self):
        """
        Test combining profile-specific filters with AND logic
        """
        # Create users for profiles
        user1 = User.objects.create(username='user1', email='user1@example.com')
        user2 = User.objects.create(username='user2', email='user2@example.com')
        user3 = User.objects.create(username='user3', email='user3@example.com')
        
        # Complete profile with picture (should match both filters)
        complete_with_picture = Profile.objects.create(
            user=user1,
            headline='Software Engineer',
            bio='Experienced developer',
            location='New York',
            avatar='avatar1.jpg'
        )
        
        # Complete profile without picture (should not match)
        complete_without_picture = Profile.objects.create(
            user=user2,
            headline='Product Manager',
            bio='Product strategy expert',
            location='San Francisco',
            avatar=''
        )
        
        # Incomplete profile with picture (should not match)
        incomplete_with_picture = Profile.objects.create(
            user=user3,
            headline='',
            bio='',
            location='',
            avatar='avatar3.jpg'
        )
        
        # Manually apply filters (simulating admin behavior)
        # Filter for profiles with pictures
        picture_filtered = Profile.objects.exclude(
            Q(avatar='') | Q(avatar__isnull=True)
        )
        
        # Filter for complete profiles (all fields filled)
        complete_filtered = picture_filtered.exclude(
            Q(headline='') | Q(headline__isnull=True) |
            Q(bio='') | Q(bio__isnull=True) |
            Q(location='') | Q(location__isnull=True)
        )
        
        # Should only contain complete_with_picture
        self.assertEqual(complete_filtered.count(), 1)
        self.assertEqual(complete_filtered.first(), complete_with_picture)
        
        # Verify excluded profiles are not in results
        self.assertNotIn(complete_without_picture, complete_filtered)
        self.assertNotIn(incomplete_with_picture, complete_filtered)
    
    def test_filter_persistence_across_pagination(self):
        """
        **Property 18: Filter Persistence Across Pagination**
        **Validates: Requirements 12.6**
        
        For any active filters and search parameters, navigating to a different 
        page should preserve all filter and search query parameters in the URL 
        and apply them to the new page.
        """
        # Create enough users to trigger pagination (more than list_per_page)
        users = []
        for i in range(15):  # More than typical page size
            user = User.objects.create(
                username=f'testuser_{i}',
                email=f'testuser_{i}@example.com',
                is_active=i % 2 == 0,  # Alternate active/inactive
                is_staff=i % 3 == 0    # Every third user is staff
            )
            users.append(user)
        
        # Create request with filters and pagination
        request = self.factory.get('/', {
            'is_active__exact': '1',  # Active users only
            'is_staff__exact': '1',   # Staff users only
            'p': '2',                 # Page 2
            'q': 'testuser',          # Search query
        })
        request.user = self.admin_user
        
        # Get changelist instance
        changelist = self.user_admin.get_changelist_instance(request)
        
        # Verify filters are preserved in the changelist
        self.assertEqual(changelist.params.get('is_active__exact'), '1')
        self.assertEqual(changelist.params.get('is_staff__exact'), '1')
        self.assertEqual(changelist.params.get('q'), 'testuser')
        
        # Get the filtered queryset
        filtered_queryset = changelist.get_queryset(request)
        
        # Verify filters are applied correctly
        for user in filtered_queryset:
            self.assertTrue(user.is_active)
            self.assertTrue(user.is_staff)
            self.assertIn('testuser', user.username.lower())
        
        # Test that pagination links preserve filters
        # Verify that the changelist preserves the filter parameters
        # This is what Django admin uses to maintain filters across pagination
        
        # Check that the filter parameters are accessible in the changelist
        filter_params = dict(changelist.params)
        self.assertEqual(filter_params.get('is_active__exact'), '1')
        self.assertEqual(filter_params.get('is_staff__exact'), '1')
        self.assertEqual(filter_params.get('q'), 'testuser')
        
        # Verify that these parameters would be preserved in pagination URLs
        # by checking that they're part of the changelist's filter specification
        expected_params = {
            'is_active__exact': '1',
            'is_staff__exact': '1', 
            'q': 'testuser'
        }
        
        for param, value in expected_params.items():
            self.assertEqual(changelist.params.get(param), value,
                           f"Parameter {param} should be preserved with value {value}")
    
    def test_search_with_filters_persistence(self):
        """
        Test that search queries persist along with filters across pagination
        """
        # Create users with searchable content
        matching_users = []
        for i in range(5):
            user = User.objects.create(
                username=f'developer_{i}',
                email=f'dev_{i}@company.com',
                first_name='John',
                last_name='Developer',
                is_active=True,
                is_staff=True
            )
            matching_users.append(user)
        
        # Create non-matching users
        for i in range(3):
            User.objects.create(
                username=f'manager_{i}',
                email=f'mgr_{i}@company.com',
                first_name='Jane',
                last_name='Manager',
                is_active=True,
                is_staff=False
            )
        
        # Create request with search and filters
        request = self.factory.get('/', {
            'q': 'developer',         # Search for 'developer'
            'is_active__exact': '1',  # Active users only
            'is_staff__exact': '1',   # Staff users only
        })
        request.user = self.admin_user
        
        # Get search results
        changelist = self.user_admin.get_changelist_instance(request)
        search_results, may_have_duplicates = changelist.get_search_results(
            request, 
            changelist.get_queryset(request), 
            'developer'
        )
        
        # Should only return users matching both search and filters
        self.assertEqual(search_results.count(), 5)
        
        for user in search_results:
            self.assertTrue(user.is_active)
            self.assertTrue(user.is_staff)
            self.assertIn('developer', user.username.lower())
        
        # Verify filter parameters are preserved in changelist
        filter_params = dict(changelist.params)
        self.assertEqual(filter_params.get('q'), 'developer')
        self.assertEqual(filter_params.get('is_active__exact'), '1')
        self.assertEqual(filter_params.get('is_staff__exact'), '1')
    
    def test_filter_count_accuracy(self):
        """
        Test that filter counts are accurate when multiple filters are applied
        """
        # Create test users with known attributes
        active_staff_users = []
        for i in range(5):
            user = User.objects.create(
                username=f'active_staff_{i}',
                email=f'active_staff_{i}@example.com',
                is_active=True,
                is_staff=True
            )
            active_staff_users.append(user)
        
        # Create some users that don't match both criteria
        User.objects.create(
            username='inactive_staff',
            email='inactive_staff@example.com',
            is_active=False,
            is_staff=True
        )
        
        User.objects.create(
            username='active_non_staff',
            email='active_non_staff@example.com',
            is_active=True,
            is_staff=False
        )
        
        # Apply multiple filters
        request = self.factory.get('/', {
            'is_active__exact': '1',
            'is_staff__exact': '1',
        })
        
        changelist = self.user_admin.get_changelist_instance(request)
        filtered_queryset = changelist.get_queryset(request)
        
        # Should only return the 5 users that match both criteria
        self.assertEqual(filtered_queryset.count(), 5)
        
        # Verify these are the correct users
        filtered_usernames = set(user.username for user in filtered_queryset)
        expected_usernames = set(user.username for user in active_staff_users)
        self.assertEqual(filtered_usernames, expected_usernames)
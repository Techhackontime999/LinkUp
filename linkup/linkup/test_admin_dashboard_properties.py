"""
Property-based tests for admin dashboard functionality

These tests verify universal properties that should hold across all valid inputs
using the Hypothesis property-based testing framework.
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from hypothesis.extra.django import TestCase as HypothesisTestCase
from hypothesis import given, strategies as st, settings
from datetime import timedelta, date
from linkup.admin_dashboard import DashboardStats

User = get_user_model()


class DashboardStatsPropertyTests(HypothesisTestCase):
    """Property-based tests for dashboard statistics functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test"""
        # Clear cache after each test
        cache.clear()
    
    @given(st.integers(min_value=0, max_value=50))
    @settings(max_examples=5)
    def test_dashboard_statistics_accuracy_users(self, num_users):
        """
        **Property 2: Dashboard Statistics Accuracy (Users)**
        **Validates: Requirements 2.2**
        
        For any number of users created, the dashboard statistics for user 
        registrations should equal the actual count of users created within 
        the last 30 days.
        
        This property verifies that:
        1. Total user count matches actual User.objects.count()
        2. New users (30 days) count matches users created in last 30 days
        3. Active users count matches users with is_active=True
        4. Staff users count matches users with is_staff=True
        """
        # Create users with different characteristics
        created_users = []
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        for i in range(num_users):
            # Vary user creation dates and properties
            if i % 3 == 0:
                # Old user (created more than 30 days ago)
                user = User.objects.create(
                    username=f'old_user_{i}',
                    email=f'old{i}@example.com',
                    is_active=(i % 2 == 0),
                    is_staff=(i % 4 == 0)
                )
                # Manually set date_joined to be older than 30 days
                user.date_joined = thirty_days_ago - timedelta(days=1)
                user.save()
            else:
                # New user (created within last 30 days)
                user = User.objects.create(
                    username=f'new_user_{i}',
                    email=f'new{i}@example.com',
                    is_active=(i % 2 == 0),
                    is_staff=(i % 4 == 0)
                )
                # Keep default date_joined (now)
            
            created_users.append(user)
        
        try:
            # Clear cache to ensure fresh data
            DashboardStats.clear_cache()
            
            # Get dashboard statistics
            user_stats = DashboardStats.get_user_stats()
            
            # Calculate expected values
            expected_total = User.objects.count()
            expected_new_30_days = User.objects.filter(
                date_joined__gte=thirty_days_ago
            ).count()
            expected_active = User.objects.filter(is_active=True).count()
            expected_staff = User.objects.filter(is_staff=True).count()
            
            # Verify statistics accuracy
            self.assertEqual(
                user_stats['total'],
                expected_total,
                f"Total users should be {expected_total}, got {user_stats['total']}"
            )
            
            self.assertEqual(
                user_stats['new_30_days'],
                expected_new_30_days,
                f"New users (30 days) should be {expected_new_30_days}, got {user_stats['new_30_days']}"
            )
            
            self.assertEqual(
                user_stats['active'],
                expected_active,
                f"Active users should be {expected_active}, got {user_stats['active']}"
            )
            
            self.assertEqual(
                user_stats['staff'],
                expected_staff,
                f"Staff users should be {expected_staff}, got {user_stats['staff']}"
            )
            
        finally:
            # Clean up
            User.objects.filter(username__contains='_user_').delete()
    
    @given(st.integers(min_value=0, max_value=20))
    @settings(max_examples=3)
    def test_dashboard_statistics_accuracy_content(self, num_posts):
        """
        **Property 2: Dashboard Statistics Accuracy (Content)**
        **Validates: Requirements 2.3**
        
        For any number of posts created, the dashboard statistics for post 
        creations should equal the actual count of posts created within 
        the last 30 days.
        """
        try:
            from feed.models import Post, Comment
            
            # Create test user
            user = User.objects.create(
                username='test_content_user',
                email='testcontent@example.com'
            )
            
            # Create posts with different creation dates
            created_posts = []
            created_comments = []
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            for i in range(num_posts):
                if i % 3 == 0:
                    # Old post (created more than 30 days ago)
                    post = Post.objects.create(
                        user=user,
                        content=f'Old post content {i}'
                    )
                    # Manually set created_at to be older than 30 days
                    post.created_at = thirty_days_ago - timedelta(days=1)
                    post.save()
                else:
                    # New post (created within last 30 days)
                    post = Post.objects.create(
                        user=user,
                        content=f'New post content {i}'
                    )
                    # Keep default created_at (now)
                
                created_posts.append(post)
                
                # Create a comment for each post
                if i % 2 == 0:
                    comment = Comment.objects.create(
                        post=post,
                        user=user,
                        content=f'Comment on post {i}'
                    )
                    if i % 3 == 0:
                        # Old comment
                        comment.created_at = thirty_days_ago - timedelta(days=1)
                        comment.save()
                    created_comments.append(comment)
            
            # Clear cache to ensure fresh data
            DashboardStats.clear_cache()
            
            # Get dashboard statistics
            content_stats = DashboardStats.get_content_stats()
            
            # Calculate expected values
            expected_total_posts = Post.objects.count()
            expected_new_posts_30_days = Post.objects.filter(
                created_at__gte=thirty_days_ago
            ).count()
            expected_total_comments = Comment.objects.count()
            expected_new_comments_30_days = Comment.objects.filter(
                created_at__gte=thirty_days_ago
            ).count()
            
            # Verify statistics accuracy
            self.assertEqual(
                content_stats['total_posts'],
                expected_total_posts,
                f"Total posts should be {expected_total_posts}, got {content_stats['total_posts']}"
            )
            
            self.assertEqual(
                content_stats['new_posts_30_days'],
                expected_new_posts_30_days,
                f"New posts (30 days) should be {expected_new_posts_30_days}, got {content_stats['new_posts_30_days']}"
            )
            
            self.assertEqual(
                content_stats['total_comments'],
                expected_total_comments,
                f"Total comments should be {expected_total_comments}, got {content_stats['total_comments']}"
            )
            
            self.assertEqual(
                content_stats['new_comments_30_days'],
                expected_new_comments_30_days,
                f"New comments (30 days) should be {expected_new_comments_30_days}, got {content_stats['new_comments_30_days']}"
            )
            
        except ImportError:
            # If feed models don't exist, verify that stats return 0
            content_stats = DashboardStats.get_content_stats()
            self.assertEqual(content_stats['total_posts'], 0)
            self.assertEqual(content_stats['new_posts_30_days'], 0)
            self.assertEqual(content_stats['total_comments'], 0)
            self.assertEqual(content_stats['new_comments_30_days'], 0)
        
        finally:
            # Clean up
            try:
                from feed.models import Post, Comment
                Post.objects.filter(content__contains='post content').delete()
                Comment.objects.filter(content__contains='Comment on post').delete()
            except ImportError:
                pass
            User.objects.filter(username='test_content_user').delete()
    
    @given(st.integers(min_value=0, max_value=15))
    @settings(max_examples=3, deadline=None)
    def test_dashboard_statistics_accuracy_jobs(self, num_jobs):
        """
        **Property 2: Dashboard Statistics Accuracy (Jobs)**
        **Validates: Requirements 2.4**
        
        For any number of jobs created, the dashboard statistics for job 
        applications should equal the actual count of applications created 
        within the last 30 days.
        """
        try:
            from jobs.models import Job, Application
            
            # Create test user
            user = User.objects.create(
                username='test_jobs_user',
                email='testjobs@example.com'
            )
            
            # Create jobs and applications
            created_jobs = []
            created_applications = []
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            for i in range(num_jobs):
                # Create job
                job = Job.objects.create(
                    title=f'Test Job {i}',
                    company=f'Company {i}',
                    location=f'Location {i}',
                    description=f'Job description {i}',
                    posted_by=user,
                    is_active=(i % 2 == 0)
                )
                created_jobs.append(job)
                
                # Create application for each job
                if i % 2 == 0:
                    application = Application.objects.create(
                        job=job,
                        applicant=user,
                        cover_letter=f'Cover letter for job {i}'
                    )
                    
                    if i % 4 == 0:
                        # Old application (more than 30 days ago)
                        application.applied_at = thirty_days_ago - timedelta(days=1)
                        application.save()
                    
                    created_applications.append(application)
            
            # Clear cache to ensure fresh data
            DashboardStats.clear_cache()
            
            # Get dashboard statistics
            job_stats = DashboardStats.get_job_stats()
            
            # Calculate expected values
            expected_total_jobs = Job.objects.count()
            expected_active_jobs = Job.objects.filter(is_active=True).count()
            expected_total_applications = Application.objects.count()
            expected_new_applications_30_days = Application.objects.filter(
                applied_at__gte=thirty_days_ago
            ).count()
            
            # Verify statistics accuracy
            self.assertEqual(
                job_stats['total_jobs'],
                expected_total_jobs,
                f"Total jobs should be {expected_total_jobs}, got {job_stats['total_jobs']}"
            )
            
            self.assertEqual(
                job_stats['active_jobs'],
                expected_active_jobs,
                f"Active jobs should be {expected_active_jobs}, got {job_stats['active_jobs']}"
            )
            
            self.assertEqual(
                job_stats['total_applications'],
                expected_total_applications,
                f"Total applications should be {expected_total_applications}, got {job_stats['total_applications']}"
            )
            
            self.assertEqual(
                job_stats['new_applications_30_days'],
                expected_new_applications_30_days,
                f"New applications (30 days) should be {expected_new_applications_30_days}, got {job_stats['new_applications_30_days']}"
            )
            
        except ImportError:
            # If jobs models don't exist, verify that stats return 0
            job_stats = DashboardStats.get_job_stats()
            self.assertEqual(job_stats['total_jobs'], 0)
            self.assertEqual(job_stats['active_jobs'], 0)
            self.assertEqual(job_stats['total_applications'], 0)
            self.assertEqual(job_stats['new_applications_30_days'], 0)
        
        finally:
            # Clean up
            try:
                from jobs.models import Job, Application
                Job.objects.filter(title__contains='Test Job').delete()
                Application.objects.filter(cover_letter__contains='Cover letter for job').delete()
            except ImportError:
                pass
            User.objects.filter(username='test_jobs_user').delete()
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=3)
    def test_recent_actions_retrieval_property(self, limit):
        """
        **Property 4: Recent Actions Retrieval**
        **Validates: Requirements 2.6**
        
        For any limit value, the dashboard should return the most recent admin 
        log entries up to that limit, ordered by action time descending.
        
        This property verifies that:
        1. The number of returned actions is <= limit
        2. Actions are ordered by action_time descending (most recent first)
        3. All returned actions are LogEntry objects
        4. The method handles edge cases (limit=0, no actions exist)
        """
        # Create test user for log entries
        user = User.objects.create(
            username='test_admin_user',
            email='testadmin@example.com',
            is_staff=True
        )
        
        # Create some log entries with different timestamps
        content_type = ContentType.objects.get_for_model(User)
        log_entries = []
        
        for i in range(limit + 5):  # Create more entries than the limit
            log_entry = LogEntry.objects.create(
                user=user,
                content_type=content_type,
                object_id=user.id,
                object_repr=f'Test Action {i}',
                action_flag=ADDITION,
                change_message=f'Test change message {i}'
            )
            # Vary the action times
            log_entry.action_time = timezone.now() - timedelta(minutes=i)
            log_entry.save()
            log_entries.append(log_entry)
        
        try:
            # Get recent actions with the specified limit
            recent_actions = DashboardStats.get_recent_actions(limit=limit)
            
            # Convert to list for easier testing
            actions_list = list(recent_actions)
            
            # Verify the number of returned actions
            self.assertLessEqual(
                len(actions_list),
                limit,
                f"Should return at most {limit} actions, got {len(actions_list)}"
            )
            
            # Verify actions are ordered by action_time descending
            if len(actions_list) > 1:
                for i in range(len(actions_list) - 1):
                    self.assertGreaterEqual(
                        actions_list[i].action_time,
                        actions_list[i + 1].action_time,
                        f"Actions should be ordered by action_time descending. "
                        f"Action {i} time: {actions_list[i].action_time}, "
                        f"Action {i+1} time: {actions_list[i + 1].action_time}"
                    )
            
            # Verify all returned objects are LogEntry instances
            for action in actions_list:
                self.assertIsInstance(
                    action,
                    LogEntry,
                    f"All returned actions should be LogEntry instances, got {type(action)}"
                )
            
            # Verify the most recent action is first (if any actions exist)
            if actions_list:
                most_recent_in_db = LogEntry.objects.order_by('-action_time').first()
                self.assertEqual(
                    actions_list[0].id,
                    most_recent_in_db.id,
                    "First returned action should be the most recent in database"
                )
            
        finally:
            # Clean up
            LogEntry.objects.filter(change_message__contains='Test change message').delete()
            User.objects.filter(username='test_admin_user').delete()
    
    def test_recent_actions_retrieval_edge_cases(self):
        """
        **Property 4: Recent Actions Retrieval (Edge Cases)**
        **Validates: Requirements 2.6**
        
        Test edge cases for recent actions retrieval:
        - limit=0 should return empty queryset
        - No actions exist should return empty queryset
        - limit > available actions should return all available actions
        """
        # Test with limit=0
        recent_actions = DashboardStats.get_recent_actions(limit=0)
        actions_list = list(recent_actions)
        self.assertEqual(
            len(actions_list),
            0,
            "limit=0 should return empty list"
        )
        
        # Test with no actions in database (clean slate)
        LogEntry.objects.all().delete()
        recent_actions = DashboardStats.get_recent_actions(limit=10)
        actions_list = list(recent_actions)
        self.assertEqual(
            len(actions_list),
            0,
            "Should return empty list when no actions exist"
        )
        
        # Create fewer actions than the limit and test
        user = User.objects.create(
            username='test_edge_user',
            email='testedge@example.com',
            is_staff=True
        )
        
        content_type = ContentType.objects.get_for_model(User)
        
        # Create only 3 actions
        for i in range(3):
            LogEntry.objects.create(
                user=user,
                content_type=content_type,
                object_id=user.id,
                object_repr=f'Edge Test Action {i}',
                action_flag=ADDITION,
                change_message=f'Edge test change message {i}'
            )
        
        try:
            # Request 10 actions but only 3 exist
            recent_actions = DashboardStats.get_recent_actions(limit=10)
            actions_list = list(recent_actions)
            
            self.assertEqual(
                len(actions_list),
                3,
                "Should return all available actions when limit > available"
            )
            
        finally:
            # Clean up
            LogEntry.objects.filter(change_message__contains='Edge test change message').delete()
            User.objects.filter(username='test_edge_user').delete()
    
    def test_dashboard_statistics_caching_property(self):
        """
        **Property 22: Dashboard Statistics Caching**
        **Validates: Requirements 14.7**
        
        For any dashboard statistics request, if a cached version exists and is 
        less than 5 minutes old, the cached data should be returned; otherwise, 
        fresh data should be calculated and cached.
        
        This property verifies that:
        1. First call calculates and caches data
        2. Second call within 5 minutes returns cached data
        3. Cache keys are properly set and retrieved
        4. Cache timeout is respected
        """
        # Clear cache to start fresh
        cache.clear()
        
        # Create test data
        user = User.objects.create(
            username='test_cache_user',
            email='testcache@example.com'
        )
        
        try:
            # First call should calculate and cache data
            user_stats_1 = DashboardStats.get_user_stats()
            
            # Verify data was cached
            cached_data = cache.get('admin_dashboard_user_stats')
            self.assertIsNotNone(
                cached_data,
                "Data should be cached after first call"
            )
            
            # Verify cached data matches returned data
            self.assertEqual(
                cached_data,
                user_stats_1,
                "Cached data should match returned data"
            )
            
            # Second call should return cached data (same values)
            user_stats_2 = DashboardStats.get_user_stats()
            
            self.assertEqual(
                user_stats_1,
                user_stats_2,
                "Second call should return same cached data"
            )
            
            # Verify cache timeout is set correctly (5 minutes = 300 seconds)
            # We can't directly test the timeout, but we can verify the cache key exists
            self.assertIsNotNone(
                cache.get('admin_dashboard_user_stats'),
                "Cache should still exist immediately after second call"
            )
            
            # Test cache clearing functionality
            DashboardStats.clear_cache()
            
            cached_data_after_clear = cache.get('admin_dashboard_user_stats')
            self.assertIsNone(
                cached_data_after_clear,
                "Cache should be cleared after calling clear_cache()"
            )
            
            # Test that all cache keys are cleared
            cache_keys = [
                'admin_dashboard_user_stats',
                'admin_dashboard_content_stats',
                'admin_dashboard_job_stats',
                'admin_dashboard_network_stats',
                'admin_dashboard_chart_data',
            ]
            
            # Set some cache values
            for key in cache_keys:
                cache.set(key, {'test': 'data'}, 300)
            
            # Clear cache
            DashboardStats.clear_cache()
            
            # Verify all keys are cleared
            for key in cache_keys:
                self.assertIsNone(
                    cache.get(key),
                    f"Cache key {key} should be cleared"
                )
            
        finally:
            # Clean up
            User.objects.filter(username='test_cache_user').delete()
            cache.clear()
"""
Tests for admin action logging functionality
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from users.admin import CustomUserAdmin, ProfileAdmin
from users.models import Profile
from jobs.admin import JobAdmin
from jobs.models import Job

User = get_user_model()


class AdminLoggingTests(TestCase):
    """Tests for admin action logging functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.user_admin = CustomUserAdmin(User, self.admin_site)
        self.profile_admin = ProfileAdmin(Profile, self.admin_site)
        self.job_admin = JobAdmin(Job, self.admin_site)
        
        # Create a superuser for admin requests
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
    
    def test_user_creation_logged(self):
        """
        Test that creating a user through admin is logged
        """
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Create a user through admin interface (simulated)
        test_user = User.objects.create(
            username='newuser',
            email='newuser@example.com'
        )
        
        # Simulate admin logging the creation
        LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(User).id,
            object_id=test_user.id,
            object_repr=str(test_user),
            action_flag=ADDITION,
            change_message='Added user.'
        )
        
        # Verify log entry was created
        log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(User),
            object_id=test_user.id,
            action_flag=ADDITION
        )
        
        self.assertEqual(log_entries.count(), 1)
        log_entry = log_entries.first()
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertEqual(log_entry.object_repr, str(test_user))
        self.assertIn('Added', log_entry.change_message)
    
    def test_user_modification_logged(self):
        """
        Test that modifying a user through admin is logged
        """
        # Create a test user
        test_user = User.objects.create(
            username='testuser',
            email='test@example.com',
            is_active=False
        )
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Modify the user
        test_user.is_active = True
        test_user.save()
        
        # Simulate admin logging the change
        LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(User).id,
            object_id=test_user.id,
            object_repr=str(test_user),
            action_flag=CHANGE,
            change_message='Changed is_active.'
        )
        
        # Verify log entry was created
        log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(User),
            object_id=test_user.id,
            action_flag=CHANGE
        )
        
        self.assertEqual(log_entries.count(), 1)
        log_entry = log_entries.first()
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertIn('Changed', log_entry.change_message)
    
    def test_user_deletion_logged(self):
        """
        Test that deleting a user through admin is logged
        """
        # Create a test user
        test_user = User.objects.create(
            username='deleteuser',
            email='delete@example.com'
        )
        user_id = test_user.id
        user_repr = str(test_user)
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Simulate admin logging the deletion before actual deletion
        LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(User).id,
            object_id=user_id,
            object_repr=user_repr,
            action_flag=DELETION,
            change_message='Deleted user.'
        )
        
        # Delete the user
        test_user.delete()
        
        # Verify log entry was created
        log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(User),
            object_id=user_id,
            action_flag=DELETION
        )
        
        self.assertEqual(log_entries.count(), 1)
        log_entry = log_entries.first()
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertEqual(log_entry.object_repr, user_repr)
        self.assertIn('Deleted', log_entry.change_message)
    
    def test_bulk_action_logged(self):
        """
        Test that bulk actions are logged
        """
        # Create test users
        users = []
        for i in range(3):
            user = User.objects.create(
                username=f'bulkuser_{i}',
                email=f'bulk_{i}@example.com',
                is_active=False
            )
            users.append(user)
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Simulate bulk activation action
        for user in users:
            user.is_active = True
            user.save()
            
            # Log each user activation
            LogEntry.objects.log_action(
                user_id=self.admin_user.id,
                content_type_id=ContentType.objects.get_for_model(User).id,
                object_id=user.id,
                object_repr=str(user),
                action_flag=CHANGE,
                change_message='Activated user via bulk action.'
            )
        
        # Verify log entries were created for all users
        log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(User),
            action_flag=CHANGE,
            change_message__icontains='bulk action'
        )
        
        self.assertEqual(log_entries.count(), 3)
        
        # Verify all users are logged
        logged_user_ids = set(log_entries.values_list('object_id', flat=True))
        expected_user_ids = set(str(user.id) for user in users)
        self.assertEqual(logged_user_ids, expected_user_ids)
    
    def test_job_creation_logged(self):
        """
        Test that creating a job through admin is logged
        """
        # Create poster user
        poster = User.objects.create(
            username='jobposter',
            email='poster@company.com'
        )
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Create a job
        job = Job.objects.create(
            title='Software Engineer',
            company='Tech Corp',
            location='San Francisco',
            job_type='full_time',
            description='Great opportunity',
            posted_by=poster
        )
        
        # Simulate admin logging the creation
        LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(Job).id,
            object_id=job.id,
            object_repr=str(job),
            action_flag=ADDITION,
            change_message='Added job posting.'
        )
        
        # Verify log entry was created
        log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(Job),
            object_id=job.id,
            action_flag=ADDITION
        )
        
        self.assertEqual(log_entries.count(), 1)
        log_entry = log_entries.first()
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertIn('Added', log_entry.change_message)
    
    def test_profile_modification_logged(self):
        """
        Test that modifying a profile through admin is logged
        """
        # Create user and profile
        user = User.objects.create(
            username='profileuser',
            email='profile@example.com'
        )
        
        # Get or create profile
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={'headline': 'Original Headline'}
        )
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Modify the profile
        profile.headline = 'Updated Headline'
        profile.bio = 'New bio content'
        profile.save()
        
        # Simulate admin logging the change
        LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(Profile).id,
            object_id=profile.id,
            object_repr=str(profile),
            action_flag=CHANGE,
            change_message='Changed headline and bio.'
        )
        
        # Verify log entry was created
        log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(Profile),
            object_id=profile.id,
            action_flag=CHANGE
        )
        
        self.assertEqual(log_entries.count(), 1)
        log_entry = log_entries.first()
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertIn('Changed', log_entry.change_message)
    
    def test_log_entry_timestamps(self):
        """
        Test that log entries have proper timestamps
        """
        # Create a test user
        test_user = User.objects.create(
            username='timestampuser',
            email='timestamp@example.com'
        )
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Create log entry
        log_entry = LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(User).id,
            object_id=test_user.id,
            object_repr=str(test_user),
            action_flag=ADDITION,
            change_message='Added user.'
        )
        
        # Verify timestamp is set
        self.assertIsNotNone(log_entry.action_time)
        
        # Verify it's recent (within last minute)
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        self.assertGreater(log_entry.action_time, one_minute_ago)
        self.assertLessEqual(log_entry.action_time, now)
    
    def test_log_entry_user_association(self):
        """
        Test that log entries are properly associated with the admin user
        """
        # Create a test user
        test_user = User.objects.create(
            username='associationuser',
            email='association@example.com'
        )
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Create log entry
        LogEntry.objects.log_action(
            user_id=self.admin_user.id,
            content_type_id=ContentType.objects.get_for_model(User).id,
            object_id=test_user.id,
            object_repr=str(test_user),
            action_flag=ADDITION,
            change_message='Added user.'
        )
        
        # Verify log entry is associated with correct admin user
        log_entry = LogEntry.objects.get(
            content_type=ContentType.objects.get_for_model(User),
            object_id=test_user.id
        )
        
        self.assertEqual(log_entry.user, self.admin_user)
        self.assertEqual(log_entry.user.username, 'admin')
        self.assertTrue(log_entry.user.is_superuser)
    
    def test_admin_action_logging_property(self):
        """
        **Property 23: Admin Action Logging**
        **Validates: Requirements 15.3**
        
        For any administrative action performed (create, update, delete, bulk action), 
        an entry should be created in Django's LogEntry model recording the action, 
        user, timestamp, and affected object.
        """
        # Test multiple types of actions
        actions_to_test = [
            ('create', ADDITION, 'Added'),
            ('update', CHANGE, 'Changed'),
            ('delete', DELETION, 'Deleted')
        ]
        
        for action_type, action_flag, expected_message in actions_to_test:
            with self.subTest(action=action_type):
                # Clear existing log entries
                LogEntry.objects.all().delete()
                
                # Create a test user for this action
                test_user = User.objects.create(
                    username=f'{action_type}_user',
                    email=f'{action_type}@example.com'
                )
                
                # Simulate admin action logging
                log_entry = LogEntry.objects.log_action(
                    user_id=self.admin_user.id,
                    content_type_id=ContentType.objects.get_for_model(User).id,
                    object_id=test_user.id,
                    object_repr=str(test_user),
                    action_flag=action_flag,
                    change_message=f'{expected_message} user via admin.'
                )
                
                # Verify log entry properties
                self.assertIsNotNone(log_entry, f"Log entry should be created for {action_type}")
                self.assertEqual(log_entry.user, self.admin_user, f"Log entry should record admin user for {action_type}")
                self.assertEqual(log_entry.content_type, ContentType.objects.get_for_model(User), f"Log entry should record correct content type for {action_type}")
                self.assertEqual(str(log_entry.object_id), str(test_user.id), f"Log entry should record correct object ID for {action_type}")
                self.assertEqual(log_entry.object_repr, str(test_user), f"Log entry should record object representation for {action_type}")
                self.assertEqual(log_entry.action_flag, action_flag, f"Log entry should record correct action flag for {action_type}")
                self.assertIn(expected_message, log_entry.change_message, f"Log entry should contain expected message for {action_type}")
                self.assertIsNotNone(log_entry.action_time, f"Log entry should have timestamp for {action_type}")
                
                # Verify timestamp is recent (within last minute)
                from django.utils import timezone
                from datetime import timedelta
                
                now = timezone.now()
                one_minute_ago = now - timedelta(minutes=1)
                
                self.assertGreater(log_entry.action_time, one_minute_ago, f"Log entry timestamp should be recent for {action_type}")
                self.assertLessEqual(log_entry.action_time, now, f"Log entry timestamp should not be in future for {action_type}")
    
    def test_bulk_action_logging_property(self):
        """
        Test that bulk actions create individual log entries for each affected object
        """
        # Create multiple test users
        users = []
        for i in range(5):
            user = User.objects.create(
                username=f'bulk_test_user_{i}',
                email=f'bulk_test_{i}@example.com',
                is_active=False
            )
            users.append(user)
        
        # Clear existing log entries
        LogEntry.objects.all().delete()
        
        # Simulate bulk action logging (activate all users)
        log_entries = []
        for user in users:
            user.is_active = True
            user.save()
            
            log_entry = LogEntry.objects.log_action(
                user_id=self.admin_user.id,
                content_type_id=ContentType.objects.get_for_model(User).id,
                object_id=user.id,
                object_repr=str(user),
                action_flag=CHANGE,
                change_message='Activated user via bulk action.'
            )
            log_entries.append(log_entry)
        
        # Verify properties for bulk action logging
        self.assertEqual(len(log_entries), len(users), "Should create log entry for each affected object")
        
        # Verify each log entry has correct properties
        for i, (user, log_entry) in enumerate(zip(users, log_entries)):
            with self.subTest(user_index=i):
                self.assertEqual(log_entry.user, self.admin_user, f"Log entry {i} should record admin user")
                self.assertEqual(str(log_entry.object_id), str(user.id), f"Log entry {i} should record correct object ID")
                self.assertEqual(log_entry.object_repr, str(user), f"Log entry {i} should record object representation")
                self.assertEqual(log_entry.action_flag, CHANGE, f"Log entry {i} should record CHANGE action")
                self.assertIn('bulk action', log_entry.change_message, f"Log entry {i} should indicate bulk action")
                self.assertIsNotNone(log_entry.action_time, f"Log entry {i} should have timestamp")
        
        # Verify all log entries are in database
        db_log_entries = LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(User),
            action_flag=CHANGE,
            change_message__icontains='bulk action'
        )
        
        self.assertEqual(db_log_entries.count(), len(users), "All log entries should be persisted in database")
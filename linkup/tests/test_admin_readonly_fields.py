"""
Test that sensitive data and audit trail fields are marked as read-only
"""
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from users.admin import CustomUserAdmin, ProfileAdmin, ExperienceAdmin, EducationAdmin
from jobs.admin import JobAdmin, ApplicationAdmin
from network.admin import ConnectionAdmin, FollowAdmin
from feed.admin import PostAdmin, CommentAdmin
from messaging.admin import MessageAdmin, NotificationAdmin, UserStatusAdmin
from users.models import Profile, Experience, Education
from jobs.models import Job, Application
from network.models import Connection, Follow
from feed.models import Post, Comment
from messaging.models import Message, Notification, UserStatus

User = get_user_model()


class AdminReadOnlyFieldsTest(TestCase):
    """Test that audit trail and sensitive fields are marked as read-only"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.admin_site = AdminSite()
    
    def test_user_admin_readonly_fields(self):
        """Test that UserAdmin has audit trail fields as readonly"""
        user_admin = CustomUserAdmin(User, self.admin_site)
        
        # Verify date_joined and last_login are readonly
        self.assertIn('date_joined', user_admin.readonly_fields)
        self.assertIn('last_login', user_admin.readonly_fields)
    
    def test_job_admin_readonly_fields(self):
        """Test that JobAdmin has timestamp fields as readonly"""
        job_admin = JobAdmin(Job, self.admin_site)
        
        # Verify created_at and updated_at are readonly
        self.assertIn('created_at', job_admin.readonly_fields)
        self.assertIn('updated_at', job_admin.readonly_fields)
    
    def test_application_admin_readonly_fields(self):
        """Test that ApplicationAdmin has applied_at as readonly"""
        app_admin = ApplicationAdmin(Application, self.admin_site)
        
        # Verify applied_at is readonly
        self.assertIn('applied_at', app_admin.readonly_fields)
    
    def test_connection_admin_readonly_fields(self):
        """Test that ConnectionAdmin has created_at as readonly"""
        conn_admin = ConnectionAdmin(Connection, self.admin_site)
        
        # Verify created_at is readonly
        self.assertIn('created_at', conn_admin.readonly_fields)
    
    def test_follow_admin_readonly_fields(self):
        """Test that FollowAdmin has created_at as readonly"""
        follow_admin = FollowAdmin(Follow, self.admin_site)
        
        # Verify created_at is readonly
        self.assertIn('created_at', follow_admin.readonly_fields)
    
    def test_post_admin_readonly_fields(self):
        """Test that PostAdmin has timestamp and engagement fields as readonly"""
        post_admin = PostAdmin(Post, self.admin_site)
        
        # Verify timestamp fields are readonly
        self.assertIn('created_at', post_admin.readonly_fields)
        self.assertIn('updated_at', post_admin.readonly_fields)
        
        # Verify engagement metrics are readonly (calculated fields)
        self.assertIn('like_count', post_admin.readonly_fields)
        self.assertIn('comment_count', post_admin.readonly_fields)
    
    def test_comment_admin_readonly_fields(self):
        """Test that CommentAdmin has timestamp fields as readonly"""
        comment_admin = CommentAdmin(Comment, self.admin_site)
        
        # Verify timestamp fields are readonly
        self.assertIn('created_at', comment_admin.readonly_fields)
        self.assertIn('updated_at', comment_admin.readonly_fields)
    
    def test_message_admin_readonly_fields(self):
        """Test that MessageAdmin has timestamp as readonly"""
        message_admin = MessageAdmin(Message, self.admin_site)
        
        # Verify timestamp is readonly
        self.assertIn('timestamp', message_admin.readonly_fields)
    
    def test_notification_admin_readonly_fields(self):
        """Test that NotificationAdmin has timestamp fields as readonly"""
        notif_admin = NotificationAdmin(Notification, self.admin_site)
        
        # Verify timestamp fields are readonly
        self.assertIn('created_at', notif_admin.readonly_fields)
        self.assertIn('delivered_at', notif_admin.readonly_fields)
        self.assertIn('read_at', notif_admin.readonly_fields)
    
    def test_user_status_admin_readonly_fields(self):
        """Test that UserStatusAdmin has last_seen as readonly"""
        status_admin = UserStatusAdmin(UserStatus, self.admin_site)
        
        # Verify last_seen is readonly
        self.assertIn('last_seen', status_admin.readonly_fields)
    
    def test_readonly_fields_cannot_be_edited(self):
        """Test that readonly fields cannot be edited through admin forms"""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        # Get the UserAdmin form
        user_admin = CustomUserAdmin(User, self.admin_site)
        form_class = user_admin.get_form(None, obj=user)
        
        # Verify that readonly fields are not in the form fields
        form = form_class(instance=user)
        
        # date_joined and last_login should not be editable fields
        self.assertNotIn('date_joined', form.fields)
        self.assertNotIn('last_login', form.fields)
    
    def test_inline_readonly_fields(self):
        """Test that inline admin classes have appropriate readonly fields"""
        from users.admin import ProfileInline
        from jobs.admin import ApplicationInline
        from feed.admin import CommentInline
        
        # ProfileInline should have profile_picture_preview as readonly
        profile_inline = ProfileInline(Profile, self.admin_site)
        self.assertIn('profile_picture_preview', profile_inline.readonly_fields)
        
        # ApplicationInline should have applied_at as readonly
        app_inline = ApplicationInline(Application, self.admin_site)
        self.assertIn('applied_at', app_inline.readonly_fields)
        
        # CommentInline should have created_at and content_preview as readonly
        comment_inline = CommentInline(Comment, self.admin_site)
        self.assertIn('created_at', comment_inline.readonly_fields)
        self.assertIn('content_preview', comment_inline.readonly_fields)

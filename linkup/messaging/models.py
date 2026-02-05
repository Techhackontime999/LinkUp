from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from core.validators import AttachmentUploadValidator, get_upload_path


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to=get_upload_path, 
        null=True, 
        blank=True,
        validators=[AttachmentUploadValidator()],
        help_text="Attach a file (max 10MB, images and documents only)"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'created_at']), 
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['recipient', 'is_read'])
        ]

    def __str__(self):
        return f"Message {self.id} from {self.sender} to {self.recipient}"
    
    def mark_as_read(self):
        """Mark message as read with timestamp"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_delivered(self):
        """Mark message as delivered with timestamp"""
        if not self.delivered_at:
            self.delivered_at = timezone.now()
            self.save(update_fields=['delivered_at'])
    
    def to_dict(self) -> dict:
        """Returns JSON-serializable dictionary representation"""
        return {
            'id': self.id,
            'sender': self.sender.username,
            'recipient': self.recipient.username,
            'content': self.content,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'created_at': self.created_at.isoformat(),
            'attachment_url': self.attachment.url if self.attachment else None,
        }
    
    def to_websocket_message(self) -> dict:
        """Returns WebSocket-ready message format"""
        return {
            'type': 'message',
            'id': self.id,
            'sender': self.sender.username,
            'recipient': self.recipient.username,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
        }


class UserStatus(models.Model):
    """Track user online/offline status"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "User statuses"
    
    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"


class QueuedMessage(models.Model):
    """Store messages that failed to send for retry later"""
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='queued_sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='queued_received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'is_processed']),
            models.Index(fields=['recipient', 'is_processed']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Queued message {self.id} from {self.sender} to {self.recipient}"
    
    def can_retry(self):
        """Check if message can be retried"""
        return self.retry_count < self.max_retries and not self.is_processed
    
    def mark_processed(self):
        """Mark message as successfully processed"""
        self.is_processed = True
        self.save(update_fields=['is_processed'])


class Notification(models.Model):
    """Comprehensive notification system for all platform events"""
    
    NOTIFICATION_TYPES = [
        # Connection-related notifications
        ('connection_request', 'Connection Request'),
        ('connection_accepted', 'Connection Accepted'),
        ('connection_rejected', 'Connection Rejected'),
        
        # Messaging notifications
        ('new_message', 'New Message'),
        ('message_delivered', 'Message Delivered'),
        ('message_read', 'Message Read'),
        
        # Job-related notifications
        ('job_application', 'Job Application Received'),
        ('application_status', 'Application Status Update'),
        ('new_job_posted', 'New Job Posted'),
        
        # Post interaction notifications
        ('post_liked', 'Post Liked'),
        ('post_commented', 'Post Commented'),
        ('post_shared', 'Post Shared'),
        ('mention', 'Mentioned in Post'),
        
        # Follow notifications
        ('new_follower', 'New Follower'),
        ('follow_accepted', 'Follow Request Accepted'),
        
        # System notifications
        ('system_announcement', 'System Announcement'),
        ('security_alert', 'Security Alert'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Core notification fields
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    
    # Generic foreign key to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Status and metadata
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Grouping support
    group_key = models.CharField(max_length=255, null=True, blank=True, help_text="Key for grouping similar notifications")
    is_grouped = models.BooleanField(default=False)
    group_count = models.IntegerField(default=1, help_text="Number of notifications in this group")
    
    # Action URL for notification clicks
    action_url = models.URLField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'notification_type']),
            models.Index(fields=['group_key']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read with timestamp"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered with timestamp"""
        if not self.is_delivered:
            self.is_delivered = True
            self.delivered_at = timezone.now()
            self.save(update_fields=['is_delivered', 'delivered_at'])
    
    def get_grouped_notifications(self):
        """Get all notifications in the same group"""
        if not self.group_key:
            return Notification.objects.filter(id=self.id)
        return Notification.objects.filter(
            recipient=self.recipient,
            group_key=self.group_key
        ).order_by('-created_at')
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, 
                          sender=None, content_object=None, priority='normal', 
                          action_url=None, group_key=None):
        """
        Create a new notification with automatic grouping support
        """
        # Check if we should group this notification
        if group_key:
            existing_group = cls.objects.filter(
                recipient=recipient,
                group_key=group_key,
                is_grouped=True
            ).first()
            
            if existing_group:
                # Update existing group
                existing_group.group_count += 1
                existing_group.message = message  # Update with latest message
                existing_group.created_at = timezone.now()  # Update timestamp
                existing_group.is_read = False  # Mark as unread
                existing_group.read_at = None
                existing_group.save()
                return existing_group
            else:
                # Create new grouped notification
                notification = cls.objects.create(
                    recipient=recipient,
                    sender=sender,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    priority=priority,
                    action_url=action_url,
                    group_key=group_key,
                    is_grouped=True,
                    group_count=1
                )
        else:
            # Create individual notification
            notification = cls.objects.create(
                recipient=recipient,
                sender=sender,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                action_url=action_url
            )
        
        # Set content object if provided
        if content_object:
            notification.content_object = content_object
            notification.save()
        
        return notification


    def to_dict(self) -> dict:
        """Returns JSON-serializable dictionary representation"""
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'priority': self.priority,
            'sender': self.sender.username if self.sender else None,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_delivered': self.is_delivered,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'created_at': self.created_at.isoformat(),
            'action_url': self.action_url,
            'is_grouped': self.is_grouped,
            'group_count': self.group_count,
        }
    
    def to_websocket_message(self) -> dict:
        """Returns WebSocket-ready notification format"""
        return {
            'type': 'notification',
            'notification': {
                'id': self.id,
                'notification_type': self.notification_type,
                'title': self.title,
                'message': self.message,
                'priority': self.priority,
                'sender': self.sender.username if self.sender else None,
                'created_at': self.created_at.isoformat(),
                'action_url': self.action_url,
                'is_grouped': self.is_grouped,
                'group_count': self.group_count,
            }
        }


class NotificationPreference(models.Model):
    """User preferences for different types of notifications"""
    
    DELIVERY_METHODS = [
        ('realtime', 'Real-time WebSocket'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('none', 'Disabled'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.CharField(max_length=50, choices=Notification.NOTIFICATION_TYPES)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS, default='realtime')
    is_enabled = models.BooleanField(default=True)
    
    # Timing preferences
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours (no notifications)")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours")
    
    class Meta:
        unique_together = ('user', 'notification_type')
        indexes = [
            models.Index(fields=['user', 'notification_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()}: {self.get_delivery_method_display()}"
    
    @classmethod
    def get_user_preference(cls, user, notification_type):
        """Get user preference for a specific notification type"""
        try:
            return cls.objects.get(user=user, notification_type=notification_type)
        except cls.DoesNotExist:
            # Return default preference
            return cls(
                user=user,
                notification_type=notification_type,
                delivery_method='realtime',
                is_enabled=True
            )
    
    def is_in_quiet_hours(self):
        """Check if current time is within user's quiet hours"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        from datetime import time
        current_time = timezone.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day quiet hours (e.g., 22:00 to 08:00 next day)
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:
            # Overnight quiet hours (e.g., 22:00 to 08:00 next day)
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end


class MessagingError(models.Model):
    """Model for structured error logging in messaging system"""
    
    ERROR_TYPES = [
        ('async_context', 'Async Context Error'),
        ('json_serialization', 'JSON Serialization Error'),
        ('connection_handling', 'Connection Handling Error'),
        ('routing_pattern', 'Routing Pattern Error'),
        ('websocket_transmission', 'WebSocket Transmission Error'),
        ('database_operation', 'Database Operation Error'),
        ('notification_delivery', 'Notification Delivery Error'),
        ('message_processing', 'Message Processing Error'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    error_type = models.CharField(max_length=50, choices=ERROR_TYPES)
    error_message = models.TextField()
    context_data = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User associated with the error, if applicable"
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    occurred_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['error_type', '-occurred_at']),
            models.Index(fields=['severity', '-occurred_at']),
            models.Index(fields=['resolved', '-occurred_at']),
            models.Index(fields=['user', '-occurred_at']),
        ]
    
    def __str__(self):
        return f"{self.get_error_type_display()} - {self.error_message[:100]}"
    
    def mark_resolved(self, resolution_notes=""):
        """Mark error as resolved with optional notes"""
        self.resolved = True
        self.resolved_at = timezone.now()
        if resolution_notes:
            self.resolution_notes = resolution_notes
        self.save(update_fields=['resolved', 'resolved_at', 'resolution_notes'])
    
    @classmethod
    def log_error(cls, error_type, error_message, context_data=None, user=None, severity='medium'):
        """Convenience method to log an error"""
        return cls.objects.create(
            error_type=error_type,
            error_message=error_message,
            context_data=context_data or {},
            user=user,
            severity=severity
        )
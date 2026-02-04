from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from core.validators import AttachmentUploadValidator, get_upload_path


class Message(models.Model):
    # Message status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ]
    
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
    
    # Enhanced status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    client_id = models.CharField(max_length=100, null=True, blank=True, help_text="Client-side message ID for deduplication")
    retry_count = models.IntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    
    # Legacy fields (kept for backward compatibility)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # New timestamp fields
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'created_at']), 
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client_id']),
            models.Index(fields=['sender', 'status']),
            models.Index(fields=['recipient', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'client_id'],
                condition=models.Q(client_id__isnull=False),
                name='unique_client_message'
            )
        ]

    def __str__(self):
        return f"Message {self.id} from {self.sender} to {self.recipient} ({self.status})"
    
    def mark_as_sent(self):
        """Mark message as sent with timestamp"""
        if self.status == 'pending':
            self.status = 'sent'
            self.sent_at = timezone.now()
            self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Mark message as delivered with timestamp"""
        if self.status in ['pending', 'sent']:
            self.status = 'delivered'
            self.delivered_at = timezone.now()
            self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self, read_timestamp=None):
        """Mark message as read with timestamp"""
        if not self.is_read:
            self.status = 'read'
            self.is_read = True
            self.read_at = read_timestamp or timezone.now()
            self.save(update_fields=['status', 'is_read', 'read_at'])
    
    def mark_as_failed(self, error_message=None):
        """Mark message as failed with error details"""
        self.status = 'failed'
        self.failed_at = timezone.now()
        self.retry_count += 1
        if error_message:
            self.last_error = error_message
        self.save(update_fields=['status', 'failed_at', 'retry_count', 'last_error'])
    
    def can_retry(self, max_retries=3):
        """Check if message can be retried"""
        return self.status == 'failed' and self.retry_count < max_retries
    
    def get_status_icon(self):
        """Get appropriate status icon for frontend display"""
        status_icons = {
            'pending': 'clock',
            'sent': 'check',
            'delivered': 'check-double',
            'read': 'check-double-blue',
            'failed': 'exclamation-triangle'
        }
        return status_icons.get(self.status, 'clock')


class UserStatus(models.Model):
    """Track user online/offline status with enhanced connection tracking"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Enhanced connection tracking
    active_connections = models.IntegerField(default=0, help_text="Number of active WebSocket connections")
    last_ping = models.DateTimeField(null=True, blank=True, help_text="Last heartbeat ping timestamp")
    connection_id = models.CharField(max_length=100, null=True, blank=True, help_text="Current connection identifier")
    device_info = models.JSONField(default=dict, blank=True, help_text="Device and browser information")
    
    class Meta:
        verbose_name_plural = "User statuses"
        indexes = [
            models.Index(fields=['is_online', 'last_seen']),
            models.Index(fields=['last_ping']),
            models.Index(fields=['active_connections']),
        ]
    
    def __str__(self):
        status = "Online" if self.is_online else "Offline"
        connections = f" ({self.active_connections} connections)" if self.active_connections > 0 else ""
        return f"{self.user.username} - {status}{connections}"
    
    def increment_connections(self, connection_id=None):
        """Increment active connection count"""
        self.active_connections += 1
        if connection_id:
            self.connection_id = connection_id
        self.is_online = True
        self.last_ping = timezone.now()
        self.save(update_fields=['active_connections', 'connection_id', 'is_online', 'last_ping'])
    
    def decrement_connections(self):
        """Decrement active connection count"""
        if self.active_connections > 0:
            self.active_connections -= 1
        
        # Mark offline if no active connections
        if self.active_connections == 0:
            self.is_online = False
            self.connection_id = None
        
        self.save(update_fields=['active_connections', 'is_online', 'connection_id'])
    
    def update_ping(self):
        """Update last ping timestamp"""
        self.last_ping = timezone.now()
        self.save(update_fields=['last_ping'])
    
    def is_connection_stale(self, timeout_seconds=30):
        """Check if connection is stale based on last ping"""
        if not self.last_ping:
            return True
        
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)
        return self.last_ping < cutoff_time
    
    def get_last_seen_display(self):
        """Get human-readable last seen text"""
        if self.is_online:
            return "Online"
        
        if not self.last_seen:
            return "Never"
        
        from django.utils.timesince import timesince
        return f"Last seen {timesince(self.last_seen)} ago"
    
    @classmethod
    def cleanup_stale_connections(cls, timeout_seconds=30):
        """Clean up stale connections and update online status"""
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)
        
        # Find users with stale connections
        stale_statuses = cls.objects.filter(
            is_online=True,
            last_ping__lt=cutoff_time
        )
        
        count = 0
        for status in stale_statuses:
            status.is_online = False
            status.active_connections = 0
            status.connection_id = None
            status.save(update_fields=['is_online', 'active_connections', 'connection_id'])
            count += 1
        
        return count


class TypingStatus(models.Model):
    """Track typing indicators for real-time chat"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='typing_statuses')
    chat_partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partner_typing_statuses')
    is_typing = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'chat_partner')
        indexes = [
            models.Index(fields=['user', 'chat_partner']),
            models.Index(fields=['is_typing', 'last_updated']),
        ]
    
    def __str__(self):
        status = "typing" if self.is_typing else "not typing"
        return f"{self.user.username} is {status} to {self.chat_partner.username}"
    
    def is_stale(self, timeout_seconds=5):
        """Check if typing status is stale (older than timeout)"""
        if not self.is_typing:
            return False
        
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)
        return self.last_updated < cutoff_time
    
    @classmethod
    def cleanup_stale_statuses(cls, timeout_seconds=5):
        """Clean up stale typing indicators"""
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)
        
        stale_statuses = cls.objects.filter(
            is_typing=True,
            last_updated__lt=cutoff_time
        )
        
        count = stale_statuses.count()
        stale_statuses.update(is_typing=False)
        
        return count


class QueuedMessage(models.Model):
    """
    Store messages for offline handling and retry logic.
    Enhanced for WhatsApp-like messaging system with comprehensive queue management.
    """
    
    QUEUE_TYPES = [
        ('outgoing', 'Outgoing'),  # Messages waiting to be sent
        ('incoming', 'Incoming'),  # Messages waiting for offline recipients
        ('retry', 'Retry'),        # Failed messages awaiting retry
    ]
    
    PRIORITY_LEVELS = [
        (1, 'High'),     # Critical messages
        (2, 'Normal'),   # Regular messages
        (3, 'Low'),      # Non-urgent messages
    ]
    
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='queued_sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='queued_received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    
    # Queue management fields
    queue_type = models.CharField(max_length=20, choices=QUEUE_TYPES, default='outgoing')
    priority = models.IntegerField(choices=PRIORITY_LEVELS, default=2)
    
    # Timing fields
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # 7-day expiration
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Retry and error handling
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True)
    error_count = models.IntegerField(default=0)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Message identification and deduplication
    client_id = models.CharField(max_length=100, blank=True, db_index=True)
    original_message_id = models.IntegerField(null=True, blank=True)  # Reference to original Message
    
    # Exponential backoff fields
    base_delay_seconds = models.IntegerField(default=2)  # Base delay for exponential backoff
    backoff_multiplier = models.FloatField(default=2.0)  # Multiplier for exponential backoff
    max_delay_seconds = models.IntegerField(default=300)  # Maximum delay (5 minutes)
    
    class Meta:
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['queue_type', 'is_processed']),
            models.Index(fields=['recipient', 'is_processed']),
            models.Index(fields=['sender', 'is_processed']),
            models.Index(fields=['next_retry_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['client_id']),
        ]
    
    def __str__(self):
        return f"Queued {self.queue_type} message {self.id} from {self.sender} to {self.recipient}"
    
    def save(self, *args, **kwargs):
        """Override save to set expiration date"""
        if not self.expires_at:
            # Set 7-day expiration for offline messages
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def can_retry(self):
        """Check if message can be retried"""
        if self.is_processed:
            return False
        if self.retry_count >= self.max_retries:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def calculate_next_retry_delay(self):
        """Calculate next retry delay using exponential backoff"""
        if self.retry_count == 0:
            return self.base_delay_seconds
        
        # Exponential backoff: base_delay * (multiplier ^ retry_count)
        delay = self.base_delay_seconds * (self.backoff_multiplier ** self.retry_count)
        
        # Cap at maximum delay
        return min(delay, self.max_delay_seconds)
    
    def schedule_next_retry(self):
        """Schedule the next retry attempt"""
        if not self.can_retry():
            return False
        
        delay_seconds = self.calculate_next_retry_delay()
        self.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.retry_count += 1
        self.save(update_fields=['next_retry_at', 'retry_count'])
        return True
    
    def mark_processed(self, success=True):
        """Mark message as processed"""
        self.is_processed = True
        self.processed_at = timezone.now()
        if success:
            self.last_error = ''
        self.save(update_fields=['is_processed', 'processed_at', 'last_error'])
    
    def mark_failed(self, error_message):
        """Mark message as failed with error"""
        self.last_error = error_message
        self.error_count += 1
        self.last_retry_at = timezone.now()
        
        if self.can_retry():
            self.schedule_next_retry()
        else:
            # Max retries exceeded or expired
            self.is_processed = True
            self.processed_at = timezone.now()
        
        self.save(update_fields=[
            'last_error', 'error_count', 'last_retry_at', 
            'next_retry_at', 'retry_count', 'is_processed', 'processed_at'
        ])
    
    def is_expired(self):
        """Check if message has expired"""
        return self.expires_at and timezone.now() > self.expires_at
    
    def get_retry_info(self):
        """Get retry information for debugging"""
        return {
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'can_retry': self.can_retry(),
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'last_error': self.last_error,
            'is_expired': self.is_expired(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def cleanup_expired_messages(cls):
        """Clean up expired messages"""
        expired_count = cls.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        return expired_count
    
    @classmethod
    def get_pending_retries(cls):
        """Get messages that are ready for retry"""
        return cls.objects.filter(
            is_processed=False,
            next_retry_at__lte=timezone.now(),
            retry_count__lt=models.F('max_retries')
        ).order_by('priority', 'next_retry_at')


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
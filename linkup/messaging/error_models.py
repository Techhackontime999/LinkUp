"""
Enhanced error handling and logging models for messaging system
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


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
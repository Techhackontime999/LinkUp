from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
from django.db.models import Q
from .models import Message, UserStatus, Notification, NotificationPreference
import sys
import os

# Add parent directory to path to import admin_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linkup.admin_utils import ExportCSVMixin, status_badge
from linkup.admin import admin_site


# Custom filter for message activity
class MessageActivityFilter(admin.SimpleListFilter):
    title = 'message activity'
    parameter_name = 'msg_activity'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('week', 'This week'),
            ('month', 'This month'),
            ('unread', 'Unread messages'),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        elif self.value() == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        elif self.value() == 'unread':
            return queryset.filter(is_read=False)


# Custom filter for notification priority
class NotificationPriorityFilter(admin.SimpleListFilter):
    title = 'notification priority'
    parameter_name = 'priority'
    
    def lookups(self, request, model_admin):
        return (
            ('high', 'High priority'),
            ('normal', 'Normal priority'),
            ('low', 'Low priority'),
        )
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(priority=self.value())


# Custom filter for notification delivery status
class NotificationDeliveryFilter(admin.SimpleListFilter):
    title = 'delivery status'
    parameter_name = 'delivery'
    
    def lookups(self, request, model_admin):
        return (
            ('delivered', 'Delivered'),
            ('pending', 'Pending delivery'),
            ('failed', 'Failed delivery'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'delivered':
            return queryset.filter(is_delivered=True)
        elif self.value() == 'pending':
            return queryset.filter(is_delivered=False, delivered_at__isnull=True)
        elif self.value() == 'failed':
            return queryset.filter(is_delivered=False, delivered_at__isnull=False)


class MessageAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('sender', 'recipient', 'content_preview', 'timestamp', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'content')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('sender', 'recipient')
    readonly_fields = ('created_at',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    fieldsets = (
        ('Message Information', {
            'fields': ('sender', 'recipient', 'content', 'attachment')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'delivered_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        """Return truncated message content"""
        if obj.content:
            return Truncator(obj.content).chars(50)
        return '-'
    content_preview.short_description = 'Message Preview'
    
    def timestamp(self, obj):
        """Return created_at as timestamp"""
        return obj.created_at
    timestamp.short_description = 'Timestamp'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('sender', 'recipient')


class UserStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'last_updated')
    list_filter = ('is_online', 'last_seen')
    autocomplete_fields = ('user',)
    readonly_fields = ('last_seen',)
    list_per_page = 100
    
    def status_badge(self, obj):
        """Return HTML badge for online status"""
        return status_badge(obj.is_online, "Online", "Offline")
    status_badge.short_description = 'Status'
    
    def status(self, obj):
        """Return status as text"""
        return "Online" if obj.is_online else "Offline"
    status.short_description = 'Status'
    
    def last_updated(self, obj):
        """Return last_seen as last_updated"""
        return obj.last_seen
    last_updated.short_description = 'Last Updated'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


class NotificationAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('user', 'notification_type', 'message_preview', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', NotificationPriorityFilter, 
                  NotificationDeliveryFilter, 'created_at')
    search_fields = ('recipient__username', 'message')
    readonly_fields = ('created_at', 'delivered_at', 'read_at')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('recipient',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('recipient', 'sender', 'notification_type', 'title', 'message', 'priority')
        }),
        ('Content Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_delivered', 'delivered_at', 'created_at')
        }),
        ('Grouping', {
            'fields': ('group_key', 'is_grouped', 'group_count'),
            'classes': ('collapse',)
        }),
        ('Action', {
            'fields': ('action_url',),
            'classes': ('collapse',)
        })
    )
    
    def message_preview(self, obj):
        """Return truncated notification message"""
        if obj.message:
            return Truncator(obj.message).chars(50)
        return '-'
    message_preview.short_description = 'Message'
    
    def user(self, obj):
        """Return recipient as user"""
        return obj.recipient
    user.short_description = 'User'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'sender', 'content_type')


class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'delivery_method', 'is_enabled', 
                   'quiet_hours_start', 'quiet_hours_end')
    list_filter = ('notification_type', 'delivery_method', 'is_enabled')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)
    list_per_page = 100
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('user', 'notification_type', 'delivery_method', 'is_enabled')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')

# Register all models with custom admin site
admin_site.register(Message, MessageAdmin)
admin_site.register(UserStatus, UserStatusAdmin)
admin_site.register(Notification, NotificationAdmin)
admin_site.register(NotificationPreference, NotificationPreferenceAdmin)
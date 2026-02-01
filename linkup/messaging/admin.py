from django.contrib import admin
from .models import Message, UserStatus, Notification, NotificationPreference


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'is_read', 'delivered_at', 'read_at', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'content')
    readonly_fields = ('created_at', 'delivered_at', 'read_at')
    raw_id_fields = ('sender', 'recipient')


@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen')
    list_filter = ('is_online', 'last_seen')
    search_fields = ('user__username',)
    readonly_fields = ('last_seen',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'sender', 'notification_type', 'title', 'priority', 'is_read', 'is_delivered', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'is_delivered', 'created_at')
    search_fields = ('recipient__username', 'sender__username', 'title', 'message')
    readonly_fields = ('created_at', 'delivered_at', 'read_at')
    raw_id_fields = ('recipient', 'sender')
    
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
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'sender', 'content_type')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'delivery_method', 'is_enabled', 'quiet_hours_start', 'quiet_hours_end')
    list_filter = ('notification_type', 'delivery_method', 'is_enabled')
    search_fields = ('user__username',)
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('user', 'notification_type', 'delivery_method', 'is_enabled')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',)
        })
    )
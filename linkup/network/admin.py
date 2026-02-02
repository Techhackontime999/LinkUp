from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from .models import Connection, Follow
import sys
import os

# Add parent directory to path to import admin_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linkup.admin_utils import ExportCSVMixin, status_badge
from linkup.admin import admin_site


# Custom filter for connection activity
class ConnectionActivityFilter(admin.SimpleListFilter):
    title = 'connection activity'
    parameter_name = 'activity'
    
    def lookups(self, request, model_admin):
        return (
            ('recent', 'Recent (7 days)'),
            ('month', 'This month'),
            ('old', 'Older than 3 months'),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        if self.value() == 'recent':
            week_ago = now - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        elif self.value() == 'old':
            three_months_ago = now - timedelta(days=90)
            return queryset.filter(created_at__lt=three_months_ago)


# Custom filter for mutual connections
class MutualConnectionFilter(admin.SimpleListFilter):
    title = 'mutual connections'
    parameter_name = 'mutual'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Mutual connections'),
            ('no', 'One-way connections'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            # Find connections where both users are connected to each other
            mutual_ids = []
            for conn in queryset:
                reverse_exists = Connection.objects.filter(
                    user=conn.friend, 
                    friend=conn.user,
                    status='accepted'
                ).exists()
                if reverse_exists and conn.status == 'accepted':
                    mutual_ids.append(conn.id)
            return queryset.filter(id__in=mutual_ids)
        elif self.value() == 'no':
            # Find connections that are not mutual
            mutual_ids = []
            for conn in queryset:
                reverse_exists = Connection.objects.filter(
                    user=conn.friend, 
                    friend=conn.user,
                    status='accepted'
                ).exists()
                if reverse_exists and conn.status == 'accepted':
                    mutual_ids.append(conn.id)
            return queryset.exclude(id__in=mutual_ids)


# Enhanced ConnectionAdmin
class ConnectionAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('user', 'friend', 'status_badge', 'created_at')
    list_filter = ('status', ConnectionActivityFilter, MutualConnectionFilter, 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name',
                    'friend__username', 'friend__email', 'friend__first_name', 'friend__last_name')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('user', 'friend')
    readonly_fields = ('created_at',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    fieldsets = (
        ('Connection Information', {
            'fields': ('user', 'friend', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Return HTML badge for connection status"""
        status_colors = {
            'pending': ('#ffc107', 'Pending'),
            'accepted': ('#28a745', 'Accepted'),
            'rejected': ('#dc3545', 'Rejected'),
        }
        color, label = status_colors.get(obj.status, ('#6c757d', obj.status))
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'friend')


# Enhanced FollowAdmin
class FollowAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('follower', 'followed', 'created_at')
    list_filter = (ConnectionActivityFilter, 'created_at')
    search_fields = ('follower__username', 'follower__email', 'follower__first_name', 'follower__last_name',
                    'followed__username', 'followed__email', 'followed__first_name', 'followed__last_name')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('follower', 'followed')
    readonly_fields = ('created_at',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    fieldsets = (
        ('Follow Information', {
            'fields': ('follower', 'followed')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('follower', 'followed')

# Register all models with custom admin site
admin_site.register(Connection, ConnectionAdmin)
admin_site.register(Follow, FollowAdmin)
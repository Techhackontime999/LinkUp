from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
from django.db.models import Q
from .models import Job, Application
import sys
import os

# Add parent directory to path to import admin_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linkup.admin_utils import ExportCSVMixin, status_badge, truncate_html
from linkup.admin import admin_site


# Custom filter for job posting date
class JobPostingDateFilter(admin.SimpleListFilter):
    title = 'posting period'
    parameter_name = 'posting_period'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('week', 'This week'),
            ('month', 'This month'),
            ('quarter', 'This quarter'),
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
        elif self.value() == 'quarter':
            quarter_ago = now - timedelta(days=90)
            return queryset.filter(created_at__gte=quarter_ago)


# Custom filter for application status
class ApplicationStatusFilter(admin.SimpleListFilter):
    title = 'application status'
    parameter_name = 'app_status'
    
    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending'),
            ('reviewed', 'Reviewed'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        )
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


# Custom filter for jobs with applications
class JobApplicationCountFilter(admin.SimpleListFilter):
    title = 'application count'
    parameter_name = 'app_count'
    
    def lookups(self, request, model_admin):
        return (
            ('none', 'No applications'),
            ('few', '1-5 applications'),
            ('many', '6+ applications'),
        )
    
    def queryset(self, request, queryset):
        from django.db.models import Count
        
        if self.value() == 'none':
            return queryset.annotate(app_count=Count('applications')).filter(app_count=0)
        elif self.value() == 'few':
            return queryset.annotate(app_count=Count('applications')).filter(app_count__range=(1, 5))
        elif self.value() == 'many':
            return queryset.annotate(app_count=Count('applications')).filter(app_count__gte=6)


# Inline admin for Applications
class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    fields = ('applicant', 'status', 'applied_at')
    readonly_fields = ('applied_at',)
    autocomplete_fields = ('applicant',)
    can_delete = False


# Enhanced JobAdmin
class JobAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('title', 'company', 'location', 'job_type', 'status_badge', 'description_preview')
    list_filter = ('job_type', 'location', 'is_active', JobPostingDateFilter, JobApplicationCountFilter, 'created_at')
    search_fields = ('title', 'company', 'description', 'location', 'requirements',
                    'posted_by__username', 'posted_by__email', 'posted_by__first_name', 'posted_by__last_name')
    date_hierarchy = 'created_at'
    inlines = [ApplicationInline]
    actions = ['mark_active', 'mark_inactive', 'export_as_csv']
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 100
    autocomplete_fields = ('posted_by',)
    
    fieldsets = (
        ('Job Information', {
            'fields': ('title', 'company', 'location', 'workplace_type', 'job_type')
        }),
        ('Details', {
            'fields': ('description', 'requirements', 'salary_range')
        }),
        ('Posting Information', {
            'fields': ('posted_by', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    def status_badge(self, obj):
        """Return HTML badge for job status"""
        return status_badge(obj.is_active, "Active", "Inactive")
    status_badge.short_description = 'Status'
    
    def description_preview(self, obj):
        """Return truncated description"""
        return truncate_html(obj.description, 100)
    description_preview.short_description = 'Description'
    
    def mark_active(self, request, queryset):
        """Bulk action to activate jobs"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} job(s) marked as active.')
    mark_active.short_description = 'Mark selected jobs as active'
    
    def mark_inactive(self, request, queryset):
        """Bulk action to deactivate jobs"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} job(s) marked as inactive.')
    mark_inactive.short_description = 'Mark selected jobs as inactive'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related"""
        qs = super().get_queryset(request)
        return qs.select_related('posted_by').prefetch_related('applications')


# Enhanced ApplicationAdmin
class ApplicationAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('applicant', 'job_title', 'applied_at', 'status', 'cover_letter_preview', 'has_resume')
    list_filter = (ApplicationStatusFilter, 'status', 'applied_at')
    search_fields = ('applicant__username', 'applicant__email', 'applicant__first_name', 'applicant__last_name',
                    'job__title', 'job__company', 'cover_letter')
    date_hierarchy = 'applied_at'
    autocomplete_fields = ('job', 'applicant')
    actions = ['export_as_csv']
    readonly_fields = ('applied_at',)
    list_per_page = 100
    
    fieldsets = (
        ('Application Information', {
            'fields': ('job', 'applicant', 'status', 'applied_at')
        }),
        ('Application Materials', {
            'fields': ('resume', 'cover_letter')
        }),
    )
    
    def job_title(self, obj):
        """Return job title"""
        return obj.job.title
    job_title.short_description = 'Job'
    job_title.admin_order_field = 'job__title'
    
    def cover_letter_preview(self, obj):
        """Return truncated cover letter"""
        if obj.cover_letter:
            return Truncator(obj.cover_letter).chars(100)
        return '-'
    cover_letter_preview.short_description = 'Cover Letter'
    
    def has_resume(self, obj):
        """Show if resume is attached"""
        if obj.resume:
            return format_html(
                '<span style="color: green;">✓</span>'
            )
        return format_html(
            '<span style="color: red;">✗</span>'
        )
    has_resume.short_description = 'Resume'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('job', 'applicant')
# Register all models with custom admin site
admin_site.register(Job, JobAdmin)
admin_site.register(Application, ApplicationAdmin)
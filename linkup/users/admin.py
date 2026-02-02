from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.text import Truncator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import User, Profile, Experience, Education
import sys
import os

# Add parent directory to path to import admin_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linkup.admin_utils import ExportCSVMixin, status_badge
from linkup.admin import admin_site


# Custom date range filter for user registration
class UserRegistrationDateFilter(admin.SimpleListFilter):
    title = 'registration period'
    parameter_name = 'reg_period'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('week', 'This week'),
            ('month', 'This month'),
            ('quarter', 'This quarter'),
            ('year', 'This year'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'today':
            return queryset.filter(date_joined__date=now.date())
        elif self.value() == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(date_joined__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(date_joined__gte=month_ago)
        elif self.value() == 'quarter':
            quarter_ago = now - timedelta(days=90)
            return queryset.filter(date_joined__gte=quarter_ago)
        elif self.value() == 'year':
            year_ago = now - timedelta(days=365)
            return queryset.filter(date_joined__gte=year_ago)


# Custom filter for profile completion
class ProfileCompletionFilter(admin.SimpleListFilter):
    title = 'profile completion'
    parameter_name = 'completion'
    
    def lookups(self, request, model_admin):
        return (
            ('complete', 'Complete (80%+)'),
            ('partial', 'Partial (50-79%)'),
            ('minimal', 'Minimal (<50%)'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'complete':
            # Profiles with headline, bio, avatar, and location
            return queryset.exclude(
                Q(headline='') | Q(headline__isnull=True) |
                Q(bio='') | Q(bio__isnull=True) |
                Q(avatar='') | Q(avatar__isnull=True) |
                Q(location='') | Q(location__isnull=True)
            )
        elif self.value() == 'partial':
            # Profiles with at least 2-3 fields filled
            complete_profiles = queryset.exclude(
                Q(headline='') | Q(headline__isnull=True) |
                Q(bio='') | Q(bio__isnull=True) |
                Q(avatar='') | Q(avatar__isnull=True) |
                Q(location='') | Q(location__isnull=True)
            )
            minimal_profiles = queryset.filter(
                (Q(headline='') | Q(headline__isnull=True)) &
                (Q(bio='') | Q(bio__isnull=True)) &
                (Q(location='') | Q(location__isnull=True))
            )
            return queryset.exclude(id__in=complete_profiles).exclude(id__in=minimal_profiles)
        elif self.value() == 'minimal':
            # Profiles with only 0-1 fields filled
            return queryset.filter(
                (Q(headline='') | Q(headline__isnull=True)) &
                (Q(bio='') | Q(bio__isnull=True)) &
                (Q(location='') | Q(location__isnull=True))
            )


# Inline admin classes
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('avatar', 'profile_picture_preview', 'headline', 'bio', 'location')
    readonly_fields = ('profile_picture_preview',)
    
    def profile_picture_preview(self, obj):
        """Display larger preview of profile picture"""
        if obj.avatar:
            try:
                return format_html(
                    '<img src="{}" style="max-width: 200px; max-height: 200px; '
                    'border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                    obj.avatar.url
                )
            except Exception:
                return "No image"
        return "No image"
    profile_picture_preview.short_description = 'Profile Picture Preview'


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0
    fields = ('company', 'title', 'start_date', 'end_date', 'is_current', 'location')
    ordering = ('-start_date',)


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0
    fields = ('school', 'degree', 'field_of_study', 'start_date', 'end_date')
    ordering = ('-start_date',)


# Enhanced UserAdmin
class CustomUserAdmin(BaseUserAdmin, ExportCSVMixin):
    list_display = ('username', 'email', 'get_full_name', 'is_active', 
                   'is_staff', 'date_joined', 'account_status_badge')
    list_filter = ('is_staff', 'is_superuser', 'is_active', UserRegistrationDateFilter, 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 
                    'profile__headline', 'profile__bio', 'profile__location')
    date_hierarchy = 'date_joined'
    inlines = [ProfileInline, ExperienceInline, EducationInline]
    readonly_fields = ('date_joined', 'last_login')
    actions = ['activate_users', 'deactivate_users', 'export_as_csv']
    list_per_page = 100
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('username', 'password', 'first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """Return formatted full name"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'first_name'
    
    def account_status_badge(self, obj):
        """Return HTML badge for account status"""
        return status_badge(obj.is_active, "Active", "Inactive")
    account_status_badge.short_description = 'Status'
    
    def activate_users(self, request, queryset):
        """Bulk action to activate users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) successfully activated.')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Bulk action to deactivate users"""
        if request.POST.get('post'):
            # User confirmed the action
            updated = queryset.update(is_active=False)
            self.message_user(request, f'{updated} user(s) successfully deactivated.')
            return
        
        # Show confirmation page
        from django.template.response import TemplateResponse
        context = {
            'title': 'Deactivate selected users',
            'queryset': queryset,
            'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/users/user/deactivate_confirmation.html', context)
    deactivate_users.short_description = 'Deactivate selected users'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('profile').prefetch_related('experiences', 'educations')


# Custom filter for profiles with pictures
class HasProfilePictureFilter(admin.SimpleListFilter):
    title = 'has profile picture'
    parameter_name = 'has_picture'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(Q(avatar='') | Q(avatar__isnull=True))
        if self.value() == 'no':
            return queryset.filter(Q(avatar='') | Q(avatar__isnull=True))


# Custom date range filter for user registration
class UserRegistrationDateFilter(admin.SimpleListFilter):
    title = 'registration period'
    parameter_name = 'reg_period'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('week', 'This week'),
            ('month', 'This month'),
            ('quarter', 'This quarter'),
            ('year', 'This year'),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        if self.value() == 'today':
            return queryset.filter(date_joined__date=now.date())
        elif self.value() == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(date_joined__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(date_joined__gte=month_ago)
        elif self.value() == 'quarter':
            quarter_ago = now - timedelta(days=90)
            return queryset.filter(date_joined__gte=quarter_ago)
        elif self.value() == 'year':
            year_ago = now - timedelta(days=365)
            return queryset.filter(date_joined__gte=year_ago)


# Custom filter for profile completion
class ProfileCompletionFilter(admin.SimpleListFilter):
    title = 'profile completion'
    parameter_name = 'completion'
    
    def lookups(self, request, model_admin):
        return (
            ('complete', 'Complete (80%+)'),
            ('partial', 'Partial (50-79%)'),
            ('minimal', 'Minimal (<50%)'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'complete':
            # Profiles with headline, bio, avatar, and location
            return queryset.exclude(
                Q(headline='') | Q(headline__isnull=True) |
                Q(bio='') | Q(bio__isnull=True) |
                Q(avatar='') | Q(avatar__isnull=True) |
                Q(location='') | Q(location__isnull=True)
            )
        elif self.value() == 'partial':
            # Profiles with at least 2-3 fields filled
            complete_profiles = queryset.exclude(
                Q(headline='') | Q(headline__isnull=True) |
                Q(bio='') | Q(bio__isnull=True) |
                Q(avatar='') | Q(avatar__isnull=True) |
                Q(location='') | Q(location__isnull=True)
            )
            minimal_profiles = queryset.filter(
                (Q(headline='') | Q(headline__isnull=True)) &
                (Q(bio='') | Q(bio__isnull=True)) &
                (Q(location='') | Q(location__isnull=True))
            )
            return queryset.exclude(id__in=complete_profiles).exclude(id__in=minimal_profiles)
        elif self.value() == 'minimal':
            # Profiles with only 0-1 fields filled
            return queryset.filter(
                (Q(headline='') | Q(headline__isnull=True)) &
                (Q(bio='') | Q(bio__isnull=True)) &
                (Q(location='') | Q(location__isnull=True))
            )


# Enhanced ProfileAdmin
class ProfileAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('profile_picture_thumbnail', 'user', 'headline', 'location', 'completion_percentage')
    list_filter = ('location', HasProfilePictureFilter, ProfileCompletionFilter)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name',
                    'headline', 'bio', 'location')
    autocomplete_fields = ('user',)
    readonly_fields = ('profile_picture_preview',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    def profile_picture_thumbnail(self, obj):
        """Return HTML img tag for thumbnail (50x50)"""
        if obj.avatar:
            try:
                return format_html(
                    '<img src="{}" width="50" height="50" '
                    'style="border-radius: 4px; object-fit: cover;" />',
                    obj.avatar.url
                )
            except Exception:
                return "No image"
        return "No image"
    profile_picture_thumbnail.short_description = 'Profile Picture'
    
    def profile_picture_preview(self, obj):
        """Return HTML img tag for preview (200x200)"""
        if obj.avatar:
            try:
                return format_html(
                    '<img src="{}" style="max-width: 200px; max-height: 200px; '
                    'border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                    obj.avatar.url
                )
            except Exception:
                return "No image"
        return "No image"
    profile_picture_preview.short_description = 'Profile Picture Preview'
    
    def completion_percentage(self, obj):
        """Calculate and display profile completion"""
        fields = ['headline', 'bio', 'avatar', 'location']
        filled = sum(1 for field in fields if getattr(obj, field))
        percentage = int((filled / len(fields)) * 100)
        
        # Color based on completion
        if percentage >= 80:
            color = "#28a745"
        elif percentage >= 50:
            color = "#ffc107"
        else:
            color = "#dc3545"
        
        return format_html(
            '<div style="width: 100px; height: 20px; background-color: #e9ecef; '
            'border-radius: 4px; overflow: hidden; display: inline-block;">'
            '<div style="width: {}%; height: 100%; background-color: {}; '
            'display: flex; align-items: center; justify-content: center; '
            'color: white; font-size: 11px; font-weight: bold;">{}</div></div>',
            percentage, color, f"{percentage}%"
        )
    completion_percentage.short_description = 'Completion'
    def has_profile_picture(self, obj):
        """Custom filter for profiles with pictures"""
        return bool(obj.avatar)
    has_profile_picture.boolean = True
    has_profile_picture.short_description = 'Has Profile Picture'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


# Enhanced ExperienceAdmin
class ExperienceAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('user', 'company', 'title', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name',
                    'company', 'title', 'description', 'location')
    date_hierarchy = 'start_date'
    autocomplete_fields = ('user',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


# Custom filter for education years
class EducationYearFilter(admin.SimpleListFilter):
    title = 'year'
    parameter_name = 'year'
    
    def lookups(self, request, model_admin):
        years = set()
        for education in model_admin.model.objects.all():
            if education.start_date:
                years.add(education.start_date.year)
            if education.end_date:
                years.add(education.end_date.year)
        return [(year, str(year)) for year in sorted(years, reverse=True)]
    
    def queryset(self, request, queryset):
        if self.value():
            year = int(self.value())
            return queryset.filter(
                Q(start_date__year=year) | Q(end_date__year=year)
            )


# Enhanced EducationAdmin
class EducationAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('user', 'school', 'degree', 'field_of_study', 'years')
    list_filter = ('degree', EducationYearFilter)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 
                    'school', 'degree', 'field_of_study')
    date_hierarchy = 'start_date'
    autocomplete_fields = ('user',)
    actions = ['export_as_csv']
    list_per_page = 100
    
    def years(self, obj):
        """Display education years in formatted way"""
        start_year = obj.start_date.year if obj.start_date else 'Unknown'
        if obj.end_date:
            end_year = obj.end_date.year
            return f"{start_year} - {end_year}"
        else:
            return f"{start_year} - Present"
    years.short_description = 'Years'
    years.admin_order_field = 'start_date'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


# Register all models with custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(Profile, ProfileAdmin)
admin_site.register(Experience, ExperienceAdmin)
admin_site.register(Education, EducationAdmin)

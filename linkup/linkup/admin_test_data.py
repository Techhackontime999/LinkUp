from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render
from django.urls import path
from django.http import JsonResponse
import json

from .models import Profile, Experience, Education, Report, Block
from feed.models import Post, Comment
from jobs.models import Job, Application
from network.models import Connection, Follow
from messaging.models import Message, Notification

User = get_user_model()

# Custom admin actions for test data management
@admin.action(description='🌱 Seed Test Data (50 users, 200 posts, 20 jobs)')
def seed_test_data_default(modeladmin, request, queryset):
    return HttpResponseRedirect(reverse('admin:seed_test_data') + '?users=50&posts=200&jobs=20')

@admin.action(description='🌱 Seed Large Dataset (100 users, 500 posts, 50 jobs)')
def seed_test_data_large(modeladmin, request, queryset):
    return HttpResponseRedirect(reverse('admin:seed_test_data') + '?users=100&posts=500&jobs=50')

@admin.action(description='🗑️ Clear All Test Data')
def clear_test_data(modeladmin, request, queryset):
    return HttpResponseRedirect(reverse('admin:clear_test_data'))

# Enhanced User Admin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'profile_headline')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]
    
    def profile_headline(self, obj):
        if hasattr(obj, 'profile') and obj.profile.headline:
            return obj.profile.headline[:50] + '...' if len(obj.profile.headline) > 50 else obj.profile.headline
        return '-'
    profile_headline.short_description = 'Profile Headline'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'headline', 'location', 'get_avatar_preview')
    list_filter = ('location',)
    search_fields = ('user__username', 'headline', 'bio')
    readonly_fields = ('get_avatar_preview',)
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]
    
    def get_avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.avatar.url)
        return 'No Avatar'
    get_avatar_preview.short_description = 'Avatar Preview'

@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'company', 'location', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'start_date', 'company')
    search_fields = ('user__username', 'title', 'company')
    date_hierarchy = 'start_date'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'degree', 'field_of_study', 'start_date', 'end_date')
    list_filter = ('school', 'degree', 'start_date')
    search_fields = ('user__username', 'school', 'degree', 'field_of_study')
    date_hierarchy = 'start_date'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported', 'reason', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reporter__username', 'reported__username', 'reason')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__username', 'blocked__username')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

# Feed models admin
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_content_preview', 'get_image_preview', 'total_likes', 'total_comments', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'content')
    date_hierarchy = 'created_at'
    readonly_fields = ('get_image_preview', 'total_likes', 'total_comments')
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]
    
    def get_content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    get_content_preview.short_description = 'Content Preview'
    
    def get_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="auto" />', obj.image.url)
        return 'No Image'
    get_image_preview.short_description = 'Image Preview'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'get_content_preview', 'created_at')
    list_filter = ('created_at', 'post')
    search_fields = ('user__username', 'content', 'post__content')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]
    
    def get_content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = 'Content Preview'

# Jobs models admin
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'workplace_type', 'job_type', 'salary_range', 'is_active', 'created_at')
    list_filter = ('workplace_type', 'job_type', 'is_active', 'created_at', 'company')
    search_fields = ('title', 'company', 'location', 'description')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'status', 'applied_at')
    list_filter = ('status', 'applied_at', 'job__company')
    search_fields = ('job__title', 'applicant__username', 'cover_letter')
    date_hierarchy = 'applied_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

# Network models admin
@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'friend', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'friend__username')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followed', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__username', 'followed__username')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

# Messaging models admin
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'get_content_preview', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'content')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]
    
    def get_content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = 'Content Preview'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'message')
    date_hierarchy = 'created_at'
    actions = [seed_test_data_default, seed_test_data_large, clear_test_data]

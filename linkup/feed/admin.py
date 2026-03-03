from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.utils.html import format_html, strip_tags
from django.utils.text import Truncator
from django.utils.translation import ngettext
from django.shortcuts import render
from .models import Post, Comment
import sys
import os

# Add parent directory to path to import admin_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linkup.admin_utils import ExportCSVMixin, truncate_html
from linkup.admin import admin_site


# Inline admin for Comments
class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('user', 'content_preview', 'created_at')
    readonly_fields = ('content_preview', 'created_at')
    can_delete = True
    
    def content_preview(self, obj):
        """Return truncated comment content"""
        return Truncator(obj.content).chars(50)
    content_preview.short_description = 'Comment'


class PostAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('author', 'content_preview', 'image_thumbnail', 
                   'like_count', 'comment_count', 'created_at')
    list_select_related = ('user',)
    readonly_fields = ('image_preview', 'content_rendered', 'created_at', 'updated_at',
                      'like_count', 'comment_count')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'content')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['delete_selected_posts', 'export_as_csv']
    inlines = [CommentInline]
    list_per_page = 100
    
    fieldsets = (
        ('Post Information', {
            'fields': ('user', 'content', 'content_rendered', 'image', 'image_preview')
        }),
        ('Engagement', {
            'fields': ('likes', 'like_count', 'comment_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def author(self, obj):
        """Display the post author"""
        return obj.user.username
    author.short_description = 'Author'
    author.admin_order_field = 'user__username'

    def content_preview(self, obj):
        """Return truncated content with HTML stripped"""
        text = strip_tags(obj.content or '')
        truncated = Truncator(text).chars(100)
        if len(text) > 100:
            return truncated
        return text
    content_preview.short_description = 'Content Preview'

    def image_thumbnail(self, obj):
        """Display image thumbnail if image exists"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" style="width:50px; height:50px; object-fit:cover; border-radius:4px;" />',
                    obj.image.url
                )
            except Exception:
                return ''
        return ''
    image_thumbnail.short_description = 'Image'

    def like_count(self, obj):
        """Return count of likes"""
        return obj.total_likes()
    like_count.short_description = 'Likes'
    
    def comment_count(self, obj):
        """Return count of comments"""
        return obj.total_comments()
    comment_count.short_description = 'Comments'

    def image_preview(self, obj):
        """Display larger image preview for detail view"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" style="max-width:200px; height:auto; border-radius:6px;" />',
                    obj.image.url
                )
            except Exception:
                return '-'
        return '-'
    image_preview.short_description = 'Image Preview'

    def content_rendered(self, obj):
        """Display rendered HTML content"""
        return format_html(obj.content or '')
    content_rendered.short_description = 'Rendered Content'

    def delete_selected_posts(self, request, queryset):
        """Bulk delete action with confirmation"""
        if 'apply' in request.POST:
            count = queryset.count()
            queryset.delete()
            self.message_user(
                request,
                ngettext(
                    '%d post was successfully deleted.',
                    '%d posts were successfully deleted.',
                    count
                ) % count,
                messages.SUCCESS
            )
            return None
        
        # Render confirmation page
        opts = self.model._meta
        context = {
            'title': 'Confirm deletion',
            'objects': queryset,
            'opts': opts,
            'queryset': queryset,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'admin/delete_confirmation.html', context)
    delete_selected_posts.short_description = 'Delete selected posts'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('comments', 'likes')


class CommentAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('author', 'post_preview', 'content_preview', 'created_at')
    list_select_related = ('user', 'post')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name',
                    'content', 'post__content', 'post__user__username')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    actions = ['delete_selected_comments', 'export_as_csv']
    list_per_page = 100
    
    fieldsets = (
        ('Comment Information', {
            'fields': ('post', 'user', 'content')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def author(self, obj):
        """Display the comment author"""
        return obj.user.username
    author.short_description = 'Author'
    author.admin_order_field = 'user__username'
    
    def post_preview(self, obj):
        """Return truncated post content"""
        text = strip_tags(obj.post.content or '')
        return Truncator(text).chars(50)
    post_preview.short_description = 'Post'
    
    def content_preview(self, obj):
        """Return truncated comment content"""
        return Truncator(obj.content).chars(100)
    content_preview.short_description = 'Comment'
    
    def delete_selected_comments(self, request, queryset):
        """Bulk delete action with confirmation"""
        if 'apply' in request.POST:
            count = queryset.count()
            queryset.delete()
            self.message_user(
                request,
                ngettext(
                    '%d comment was successfully deleted.',
                    '%d comments were successfully deleted.',
                    count
                ) % count,
                messages.SUCCESS
            )
            return None
        
        # Render confirmation page
        opts = self.model._meta
        context = {
            'title': 'Confirm deletion',
            'objects': queryset,
            'opts': opts,
            'queryset': queryset,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'admin/delete_confirmation.html', context)
    delete_selected_comments.short_description = 'Delete selected comments'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'post')
# Register all models with custom admin site
admin_site.register(Post, PostAdmin)
admin_site.register(Comment, CommentAdmin)
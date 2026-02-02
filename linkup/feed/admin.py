from django.contrib import admin, messages
from django.utils.html import format_html, strip_tags
from django.utils.text import Truncator
from django.utils.translation import ngettext
from django.shortcuts import render
import bleach
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
    list_display = ('id', 'user', 'short_content', 'image_preview', 'created_at', 
                   'total_likes_count', 'total_comments_count')
    list_select_related = ('user',)
    readonly_fields = ('image_preview', 'content_rendered', 'created_at', 'updated_at',
                      'total_likes_count', 'total_comments_count')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'content')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['sanitize_selected_content', 'export_as_csv']
    inlines = [CommentInline]
    list_per_page = 100
    
    fieldsets = (
        ('Post Information', {
            'fields': ('user', 'content', 'content_rendered', 'image', 'image_preview')
        }),
        ('Engagement', {
            'fields': ('likes', 'total_likes_count', 'total_comments_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # Allowed tags/attributes for sanitization (conservative set)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'blockquote', 'code', 'pre', 
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img'
    ]
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'rel', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
    }

    def short_content(self, obj):
        text = strip_tags(obj.content or '')
        return Truncator(text).chars(120)
    short_content.short_description = 'Content Preview'

    def image_preview(self, obj):
        """Display image thumbnail"""
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" style="max-width:150px; height:auto; border-radius:6px;" />',
                    obj.image.url
                )
            except Exception:
                return '-'
        return '-'
    image_preview.short_description = 'Image'

    def content_rendered(self, obj):
        return format_html(obj.content or '')
    content_rendered.short_description = 'Rendered Content'

    def total_likes_count(self, obj):
        return obj.total_likes()
    total_likes_count.short_description = 'Likes'
    
    def total_comments_count(self, obj):
        return obj.total_comments()
    total_comments_count.short_description = 'Comments'

    def sanitize_selected_content(self, request, queryset):
        """Admin action that sanitizes HTML content of selected posts."""
        selected = request.POST.getlist('_selected_action') or [str(o.pk) for o in queryset]

        # Build preview data
        preview = []
        for post in queryset:
            original = post.content or ''
            cleaned = bleach.clean(
                original,
                tags=self.ALLOWED_TAGS,
                attributes=self.ALLOWED_ATTRIBUTES,
                strip=True
            )
            preview.append({
                'id': post.pk,
                'user': str(post.user),
                'created': post.created_at,
                'original': original,
                'cleaned': cleaned,
                'changed': cleaned != original,
            })

        # If the confirmation form was submitted with 'apply', either perform or simulate the changes
        if 'apply' in request.POST:
            dry_run = 'dry_run' in request.POST
            sanitized = 0
            for post in queryset:
                original = post.content or ''
                cleaned = bleach.clean(
                    original,
                    tags=self.ALLOWED_TAGS,
                    attributes=self.ALLOWED_ATTRIBUTES,
                    strip=True
                )
                if cleaned != original:
                    if not dry_run:
                        post.content = cleaned
                        post.save(update_fields=['content', 'updated_at'])
                    sanitized += 1

            if dry_run:
                self.message_user(request, ngettext(
                    'Dry run complete: %d post would be sanitized (no changes saved).',
                    'Dry run complete: %d posts would be sanitized (no changes saved).',
                    sanitized
                ) % sanitized, messages.INFO)
            else:
                self.message_user(request, ngettext(
                    '%d post sanitized.',
                    '%d posts sanitized.',
                    sanitized
                ) % sanitized, messages.SUCCESS if sanitized else messages.INFO)
            return None

        # Otherwise render confirmation page
        opts = self.model._meta
        context = {
            'title': 'Confirm sanitize HTML content',
            'objects': preview,
            'opts': opts,
            'selected_ids': selected,
            'app_label': opts.app_label,
            'model_name': opts.model_name,
            'dry_run_default': True,
            'return_url': request.get_full_path(),
        }
        return render(request, 'admin/feed/sanitize_confirm.html', context)
    sanitize_selected_content.short_description = 'Sanitize HTML content of selected posts (preview & dry-run)'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('comments', 'likes')


class CommentAdmin(admin.ModelAdmin, ExportCSVMixin):
    list_display = ('id', 'user', 'post_link', 'short_content', 'created_at')
    list_select_related = ('user', 'post')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name',
                    'content', 'post__content', 'post__user__username')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    actions = ['export_as_csv']
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
    
    def short_content(self, obj):
        return Truncator(obj.content).chars(100)
    short_content.short_description = 'Comment'
    
    def post_link(self, obj):
        return format_html(
            '<a href="/admin/feed/post/{}/change/">Post #{}</a>',
            obj.post.id, obj.post.id
        )
    post_link.short_description = 'Post'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'post')
# Register all models with custom admin site
admin_site.register(Post, PostAdmin)
admin_site.register(Comment, CommentAdmin)
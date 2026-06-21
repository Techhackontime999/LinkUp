from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from ckeditor_uploader.fields import RichTextUploadingField
from core.validators import AttachmentUploadValidator

class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    content = RichTextUploadingField(blank=True)
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s post at {self.created_at}"
    
    def total_likes(self):
        return self.likes.count()
    
    def total_comments(self):
        return self.comments.count()


class PostAttachment(models.Model):
    FILE_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='posts/', validators=[AttachmentUploadValidator()])
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    sort_order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.post.id} - {self.file.name}"

    def filename(self):
        import os
        return os.path.basename(self.file.name)

    def file_size(self):
        try:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except:
            return "Unknown"

    def is_video(self):
        return self.file_type == 'video'

    def is_image(self):
        return self.file_type == 'image'

    def is_document(self):
        return self.file_type == 'document'

    def is_audio(self):
        return self.file_type == 'audio'

    def file_extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')

    def thumbnail_url(self):
        if self.is_image():
            return self.file.url
        return None


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username}'s comment on post {self.post.id}"


class DocumentPage(models.Model):
    attachment = models.ForeignKey(PostAttachment, on_delete=models.CASCADE, related_name='pages')
    page_number = models.PositiveIntegerField()
    image = models.ImageField(upload_to='document_pages/')
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['page_number']

    def __str__(self):
        return f"Page {self.page_number} of {self.attachment.filename()}"

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.validators import ImageUploadValidator, get_upload_path

class User(AbstractUser):
    pass

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    headline = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(
        upload_to=get_upload_path, 
        blank=True, 
        null=True,
        validators=[ImageUploadValidator()],
        help_text="Upload a profile picture (max 5MB, JPG/PNG/GIF/WebP only)"
    )
    location = models.CharField(max_length=100, blank=True)
    cover_photo = models.ImageField(
        upload_to=get_upload_path,
        blank=True,
        null=True,
        validators=[ImageUploadValidator(max_size=20 * 1024 * 1024)],
        help_text="Upload a cover photo (max 20MB, JPG/PNG/GIF/WebP only)"
    )
    
    # Social media links
    website = models.URLField(max_length=500, blank=True, help_text="Personal website URL")
    linkedin = models.URLField(max_length=500, blank=True, help_text="LinkedIn profile URL")
    github = models.URLField(max_length=500, blank=True, help_text="GitHub profile URL")
    youtube = models.URLField(max_length=500, blank=True, help_text="YouTube channel URL")
    instagram = models.URLField(max_length=500, blank=True, help_text="Instagram profile URL")
    twitter = models.URLField(max_length=500, blank=True, help_text="X (Twitter) profile URL")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()

class Experience(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='experiences')
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} at {self.company}"

class Education(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='educations')
    school = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.degree} at {self.school}"


class Report(models.Model):
    reporter = models.ForeignKey(User, related_name='reports_made', on_delete=models.CASCADE)
    reported = models.ForeignKey(User, related_name='reports_received', on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter} against {self.reported}"


class SocialLink(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_links')
    label = models.CharField(max_length=100, help_text="e.g. Website, LinkedIn, GitHub, Portfolio")
    url = models.URLField(max_length=500)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.label}: {self.url}"

    def icon_name(self):
        name = self.label.lower().strip()
        if 'website' in name or 'web' in name or 'portfolio' in name:
            return 'globe'
        if 'linkedin' in name:
            return 'linkedin'
        if 'github' in name or 'git' in name:
            return 'github'
        if 'youtube' in name or 'yt' in name:
            return 'youtube'
        if 'instagram' in name or 'insta' in name:
            return 'instagram'
        if 'twitter' in name or 'x.com' in self.url.lower():
            return 'twitter'
        if 'facebook' in name or 'fb' in name:
            return 'facebook'
        if 'tiktok' in name:
            return 'tiktok'
        if 'email' in name or 'mail' in name:
            return 'email'
        return 'link'


class Block(models.Model):
    blocker = models.ForeignKey(User, related_name='blocks_made', on_delete=models.CASCADE)
    blocked = models.ForeignKey(User, related_name='blocks_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"

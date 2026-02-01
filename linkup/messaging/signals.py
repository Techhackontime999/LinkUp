"""
Signal handlers for automatic notification creation
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Message
from .notification_service import (
    notify_new_message, 
    notify_connection_request, 
    notify_connection_accepted,
    notify_job_application,
    notify_post_liked,
    notify_new_follower,
    notify_mention
)

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """Create notification when a new message is sent"""
    if created:
        try:
            notify_new_message(
                sender=instance.sender,
                recipient=instance.recipient,
                message_obj=instance
            )
            logger.info(f"Message notification created for message {instance.id}")
        except Exception as e:
            logger.error(f"Error creating message notification: {e}")


# Connection-related signals
def setup_connection_signals():
    """Setup signals for connection-related notifications"""
    try:
        from network.models import Connection
        
        @receiver(post_save, sender=Connection)
        def create_connection_notification(sender, instance, created, **kwargs):
            """Create notification for connection requests and acceptances"""
            try:
                if created and instance.status == 'pending':
                    # New connection request
                    notify_connection_request(
                        sender=instance.user,
                        recipient=instance.friend,
                        connection_obj=instance
                    )
                    logger.info(f"Connection request notification created for connection {instance.id}")
                
                elif not created and instance.status == 'accepted':
                    # Connection accepted (status changed from pending to accepted)
                    notify_connection_accepted(
                        sender=instance.friend,  # The person who accepted
                        recipient=instance.user,  # The person who sent the request
                        connection_obj=instance
                    )
                    logger.info(f"Connection accepted notification created for connection {instance.id}")
                    
            except Exception as e:
                logger.error(f"Error creating connection notification: {e}")
                
    except ImportError:
        logger.warning("Network app not available, skipping connection signals")


# Job application signals
def setup_job_signals():
    """Setup signals for job-related notifications"""
    try:
        from jobs.models import Application
        
        @receiver(post_save, sender=Application)
        def create_job_application_notification(sender, instance, created, **kwargs):
            """Create notification when someone applies for a job"""
            if created:
                try:
                    notify_job_application(
                        applicant=instance.applicant,
                        job_poster=instance.job.posted_by,
                        application_obj=instance
                    )
                    logger.info(f"Job application notification created for application {instance.id}")
                except Exception as e:
                    logger.error(f"Error creating job application notification: {e}")
                    
    except ImportError:
        logger.warning("Jobs app not available, skipping job signals")


# Post interaction signals
def setup_post_signals():
    """Setup signals for post-related notifications"""
    try:
        from feed.models import Post
        
        # Handle post likes
        def post_liked_handler(sender, instance, action, pk_set, **kwargs):
            """Handle post like notifications"""
            if action == 'post_add':  # When likes are added
                try:
                    post = instance
                    for user_id in pk_set:
                        liker = User.objects.get(id=user_id)
                        notify_post_liked(
                            liker=liker,
                            post_owner=post.user,
                            post_obj=post
                        )
                        logger.info(f"Post like notification created for post {post.id}")
                except Exception as e:
                    logger.error(f"Error creating post like notification: {e}")
        
        # Connect the m2m_changed signal for likes
        from django.db.models.signals import m2m_changed
        m2m_changed.connect(post_liked_handler, sender=Post.likes.through)
        
    except ImportError:
        logger.warning("Feed app not available, skipping post signals")


# Follow signals
def setup_follow_signals():
    """Setup signals for follow-related notifications"""
    try:
        from network.models import Follow
        
        @receiver(post_save, sender=Follow)
        def create_follow_notification(sender, instance, created, **kwargs):
            """Create notification when someone follows a user"""
            if created:
                try:
                    notify_new_follower(
                        follower=instance.follower,
                        followed=instance.followed,
                        follow_obj=instance
                    )
                    logger.info(f"Follow notification created for follow {instance.id}")
                except Exception as e:
                    logger.error(f"Error creating follow notification: {e}")
                    
    except ImportError:
        logger.warning("Network app not available, skipping follow signals")


# Mention detection (this would typically be called from post creation/update views)
def detect_and_notify_mentions(post_content, post_obj, author):
    """
    Detect @mentions in post content and create notifications
    This should be called from the post creation/update views
    """
    import re
    
    # Find all @username mentions
    mention_pattern = r'@(\w+)'
    mentioned_usernames = re.findall(mention_pattern, post_content)
    
    for username in mentioned_usernames:
        try:
            mentioned_user = User.objects.get(username=username)
            if mentioned_user != author:  # Don't notify self-mentions
                notify_mention(
                    mentioner=author,
                    mentioned=mentioned_user,
                    post_obj=post_obj
                )
                logger.info(f"Mention notification created for user {mentioned_user.username}")
        except User.DoesNotExist:
            logger.warning(f"Mentioned user @{username} not found")
        except Exception as e:
            logger.error(f"Error creating mention notification for @{username}: {e}")


# Initialize all signal handlers
def setup_all_signals():
    """Setup all notification signal handlers"""
    setup_connection_signals()
    setup_job_signals()
    setup_post_signals()
    setup_follow_signals()
    logger.info("All notification signal handlers setup complete")
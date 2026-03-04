"""
Social Platform models for AI Agent interactions.

This module contains models for the AI Agent Social Platform including:
- AgentSocialProfile: Social profiles for agents
- AgentPost: Posts created by agents
- AgentFollow: Follow relationships between agents
- AgentReaction: Reactions to posts and comments
- AgentComment: Comments on posts
- AgentCollaborationSpace: Group collaboration spaces
- AgentCapabilityListing: Marketplace for agent capabilities
- AgentNotification: Notification system
- AgentReputation: Reputation tracking
"""
import uuid
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from .models import AIAgent


class AgentSocialProfile(models.Model):
    """
    Social profile for AI agents with bio, avatar, and social stats.
    """
    agent = models.OneToOneField(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='social_profile',
        help_text="Agent this profile belongs to"
    )
    display_name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(3), MaxLengthValidator(100)],
        help_text="Display name for the agent (3-100 characters)"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Agent bio (max 500 characters)"
    )
    avatar_url = models.URLField(
        blank=True,
        help_text="URL to agent avatar image"
    )
    banner_url = models.URLField(
        blank=True,
        help_text="URL to agent banner image"
    )
    website = models.URLField(
        blank=True,
        help_text="Agent website URL"
    )
    tags = models.JSONField(
        default=list,
        help_text="Tags for agent interests and capabilities (max 10)"
    )
    
    # Social stats
    follower_count = models.IntegerField(
        default=0,
        help_text="Number of followers"
    )
    following_count = models.IntegerField(
        default=0,
        help_text="Number of agents being followed"
    )
    post_count = models.IntegerField(
        default=0,
        help_text="Number of posts created"
    )
    reputation_score = models.FloatField(
        default=0.0,
        help_text="Overall reputation score (0.0 to 100.0)"
    )
    
    # Visibility settings
    is_public = models.BooleanField(
        default=True,
        help_text="Whether profile is publicly visible"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether agent is verified"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agent_social_profiles'
        verbose_name = 'Agent Social Profile'
        verbose_name_plural = 'Agent Social Profiles'
        indexes = [
            models.Index(fields=['display_name']),
            models.Index(fields=['reputation_score']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return f"{self.display_name} (@{self.agent.name})"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate display_name length
        if len(self.display_name) < 3 or len(self.display_name) > 100:
            raise ValidationError({
                'display_name': 'Display name must be between 3 and 100 characters.'
            })
        
        # Validate bio length
        if len(self.bio) > 500:
            raise ValidationError({
                'bio': 'Bio cannot exceed 500 characters.'
            })
        
        # Validate tags
        if not isinstance(self.tags, list):
            raise ValidationError({
                'tags': 'Tags must be a valid JSON array.'
            })
        
        if len(self.tags) > 10:
            raise ValidationError({
                'tags': 'Maximum 10 tags allowed.'
            })
        
        for tag in self.tags:
            if len(tag) > 30:
                raise ValidationError({
                    'tags': 'Each tag must be max 30 characters.'
                })
        
        # Validate reputation score
        if not (0.0 <= self.reputation_score <= 100.0):
            raise ValidationError({
                'reputation_score': 'Reputation score must be between 0.0 and 100.0.'
            })


class AgentPost(models.Model):
    """
    Posts created by AI agents on the social platform.
    """
    POST_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('CODE', 'Code Snippet'),
        ('DATA', 'Data/Analysis'),
        ('ANNOUNCEMENT', 'Announcement'),
        ('QUESTION', 'Question'),
    ]
    
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('FOLLOWERS', 'Followers Only'),
        ('CONNECTIONS', 'Connections Only'),
        ('PRIVATE', 'Private'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='social_posts',
        help_text="Agent who created the post"
    )
    post_type = models.CharField(
        max_length=20,
        choices=POST_TYPE_CHOICES,
        default='TEXT',
        help_text="Type of post content"
    )
    content = models.TextField(
        max_length=5000,
        help_text="Post content (max 5000 characters)"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional post metadata (language, syntax, attachments, etc.)"
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='PUBLIC',
        help_text="Post visibility level"
    )
    
    # Engagement metrics
    view_count = models.IntegerField(
        default=0,
        help_text="Number of views"
    )
    reaction_count = models.IntegerField(
        default=0,
        help_text="Number of reactions"
    )
    comment_count = models.IntegerField(
        default=0,
        help_text="Number of comments"
    )
    share_count = models.IntegerField(
        default=0,
        help_text="Number of shares"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
    is_flagged = models.BooleanField(
        default=False,
        help_text="Whether post is flagged for moderation"
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Whether post is soft-deleted"
    )
    
    class Meta:
        db_table = 'agent_posts'
        ordering = ['-created_at']
        verbose_name = 'Agent Post'
        verbose_name_plural = 'Agent Posts'
        indexes = [
            models.Index(fields=['agent', 'created_at']),
            models.Index(fields=['post_type']),
            models.Index(fields=['visibility']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"Post by {self.agent.name} ({self.post_type})"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate content length
        if len(self.content) > 5000:
            raise ValidationError({
                'content': 'Post content cannot exceed 5000 characters.'
            })
        
        # Validate metadata is a dict
        if not isinstance(self.metadata, dict):
            raise ValidationError({
                'metadata': 'Metadata must be a valid JSON object.'
            })


class AgentFollow(models.Model):
    """
    Follow relationships between AI agents.
    """
    follower = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='agent_following',
        help_text="Agent who is following"
    )
    followed = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='agent_followers',
        help_text="Agent being followed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Interaction tracking
    notification_enabled = models.BooleanField(
        default=True,
        help_text="Whether notifications are enabled for this follow"
    )
    interaction_count = models.IntegerField(
        default=0,
        help_text="Number of interactions between these agents"
    )
    last_interaction_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last interaction"
    )
    
    class Meta:
        db_table = 'agent_follows'
        unique_together = ('follower', 'followed')
        verbose_name = 'Agent Follow'
        verbose_name_plural = 'Agent Follows'
        indexes = [
            models.Index(fields=['follower', 'created_at']),
            models.Index(fields=['followed', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.follower.name} follows {self.followed.name}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Prevent self-follows
        if self.follower_id == self.followed_id:
            raise ValidationError({
                'followed': 'Agents cannot follow themselves.'
            })


class AgentReaction(models.Model):
    """
    Reactions to posts and comments by AI agents.
    """
    REACTION_TYPE_CHOICES = [
        ('LIKE', 'Like'),
        ('INSIGHTFUL', 'Insightful'),
        ('HELPFUL', 'Helpful'),
        ('INNOVATIVE', 'Innovative'),
        ('AGREE', 'Agree'),
        ('DISAGREE', 'Disagree'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='agent_reactions',
        help_text="Agent who reacted"
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=REACTION_TYPE_CHOICES,
        help_text="Type of reaction"
    )
    
    # Polymorphic target (post or comment)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of content being reacted to"
    )
    object_id = models.UUIDField(
        help_text="ID of the content being reacted to"
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_reactions'
        unique_together = ('agent', 'content_type', 'object_id')
        verbose_name = 'Agent Reaction'
        verbose_name_plural = 'Agent Reactions'
        indexes = [
            models.Index(fields=['agent', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['reaction_type']),
        ]
    
    def __str__(self):
        return f"{self.agent.name} reacted {self.reaction_type}"


class AgentComment(models.Model):
    """
    Comments on agent posts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        AgentPost,
        on_delete=models.CASCADE,
        related_name='agent_comments',
        help_text="Post being commented on"
    )
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='agent_comments',
        help_text="Agent who created the comment"
    )
    content = models.TextField(
        max_length=2000,
        help_text="Comment content (max 2000 characters)"
    )
    
    # Threading support
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Parent comment for threading"
    )
    
    # Engagement
    reaction_count = models.IntegerField(
        default=0,
        help_text="Number of reactions"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(
        default=False,
        help_text="Whether comment is soft-deleted"
    )
    
    class Meta:
        db_table = 'agent_comments'
        ordering = ['created_at']
        verbose_name = 'Agent Comment'
        verbose_name_plural = 'Agent Comments'
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['agent', 'created_at']),
            models.Index(fields=['parent_comment']),
        ]
    
    def __str__(self):
        return f"Comment by {self.agent.name} on post {self.post.id}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate content length
        if len(self.content) > 2000:
            raise ValidationError({
                'content': 'Comment content cannot exceed 2000 characters.'
            })


class AgentCollaborationSpace(models.Model):
    """
    Collaboration spaces for groups of AI agents.
    """
    SPACE_TYPE_CHOICES = [
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
        ('INVITE_ONLY', 'Invite Only'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200,
        help_text="Space name"
    )
    description = models.TextField(
        max_length=1000,
        help_text="Space description"
    )
    creator = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='created_spaces',
        help_text="Agent who created the space"
    )
    members = models.ManyToManyField(
        AIAgent,
        through='SpaceMembership',
        related_name='collaboration_spaces',
        help_text="Members of the space"
    )
    
    space_type = models.CharField(
        max_length=20,
        choices=SPACE_TYPE_CHOICES,
        default='PUBLIC',
        help_text="Space visibility type"
    )
    tags = models.JSONField(
        default=list,
        help_text="Tags for categorization"
    )
    
    # Stats
    member_count = models.IntegerField(
        default=0,
        help_text="Number of members"
    )
    post_count = models.IntegerField(
        default=0,
        help_text="Number of posts in space"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether space is active"
    )
    
    class Meta:
        db_table = 'agent_collaboration_spaces'
        ordering = ['-created_at']
        verbose_name = 'Agent Collaboration Space'
        verbose_name_plural = 'Agent Collaboration Spaces'
        indexes = [
            models.Index(fields=['creator', 'created_at']),
            models.Index(fields=['space_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.space_type})"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate tags is a list
        if not isinstance(self.tags, list):
            raise ValidationError({
                'tags': 'Tags must be a valid JSON array.'
            })


class SpaceMembership(models.Model):
    """
    Membership in collaboration spaces.
    """
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('ADMIN', 'Admin'),
        ('MEMBER', 'Member'),
    ]
    
    space = models.ForeignKey(
        AgentCollaborationSpace,
        on_delete=models.CASCADE,
        help_text="Collaboration space"
    )
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        help_text="Agent member"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='MEMBER',
        help_text="Member role"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    contribution_count = models.IntegerField(
        default=0,
        help_text="Number of contributions"
    )
    
    class Meta:
        db_table = 'space_memberships'
        unique_together = ('space', 'agent')
        verbose_name = 'Space Membership'
        verbose_name_plural = 'Space Memberships'
        indexes = [
            models.Index(fields=['space', 'agent']),
            models.Index(fields=['agent', 'joined_at']),
        ]
    
    def __str__(self):
        return f"{self.agent.name} in {self.space.name} ({self.role})"



class AgentCapabilityListing(models.Model):
    """
    Marketplace listings for agent capabilities.
    """
    LISTING_TYPE_CHOICES = [
        ('SERVICE', 'Service'),
        ('API', 'API'),
        ('SKILL', 'Skill'),
        ('RESOURCE', 'Resource'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('INACTIVE', 'Inactive'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='capability_listings',
        help_text="Agent offering the capability"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Listing title"
    )
    description = models.TextField(
        max_length=2000,
        help_text="Listing description"
    )
    listing_type = models.CharField(
        max_length=20,
        choices=LISTING_TYPE_CHOICES,
        help_text="Type of listing"
    )
    
    # Capability details
    capabilities = models.JSONField(
        default=dict,
        help_text="Capability specifications"
    )
    requirements = models.JSONField(
        default=dict,
        help_text="Requirements for using capability"
    )
    pricing_model = models.JSONField(
        default=dict,
        help_text="Pricing information"
    )
    
    # Discovery
    tags = models.JSONField(
        default=list,
        help_text="Tags for discovery"
    )
    category = models.CharField(
        max_length=100,
        help_text="Category"
    )
    
    # Stats
    view_count = models.IntegerField(
        default=0,
        help_text="Number of views"
    )
    request_count = models.IntegerField(
        default=0,
        help_text="Number of requests"
    )
    rating_average = models.FloatField(
        default=0.0,
        help_text="Average rating"
    )
    rating_count = models.IntegerField(
        default=0,
        help_text="Number of ratings"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text="Listing status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agent_capability_listings'
        ordering = ['-created_at']
        verbose_name = 'Agent Capability Listing'
        verbose_name_plural = 'Agent Capability Listings'
        indexes = [
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['listing_type']),
            models.Index(fields=['category']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.agent.name}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate JSON fields
        for field_name, field_value in [
            ('capabilities', self.capabilities),
            ('requirements', self.requirements),
            ('pricing_model', self.pricing_model)
        ]:
            if not isinstance(field_value, dict):
                raise ValidationError({
                    field_name: f'{field_name} must be a valid JSON object.'
                })
        
        if not isinstance(self.tags, list):
            raise ValidationError({
                'tags': 'Tags must be a valid JSON array.'
            })


class AgentNotification(models.Model):
    """
    Notifications for agent interactions.
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('NEW_FOLLOWER', 'New Follower'),
        ('POST_REACTION', 'Post Reaction'),
        ('POST_COMMENT', 'Post Comment'),
        ('COMMENT_REPLY', 'Comment Reply'),
        ('MENTION', 'Mention'),
        ('SPACE_INVITE', 'Space Invite'),
        ('CAPABILITY_REQUEST', 'Capability Request'),
        ('SYSTEM', 'System'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='agent_notifications',
        help_text="Agent receiving the notification"
    )
    sender = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sent_agent_notifications',
        help_text="Agent who triggered the notification"
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text="Type of notification"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text="Notification priority"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Notification title"
    )
    message = models.TextField(
        max_length=500,
        help_text="Notification message"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata"
    )
    
    # Target object (polymorphic)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Type of target object"
    )
    object_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of target object"
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    is_read = models.BooleanField(
        default=False,
        help_text="Whether notification has been read"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When notification was read"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_notifications'
        ordering = ['-created_at']
        verbose_name = 'Agent Notification'
        verbose_name_plural = 'Agent Notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"Notification for {self.recipient.name}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate metadata is a dict
        if not isinstance(self.metadata, dict):
            raise ValidationError({
                'metadata': 'Metadata must be a valid JSON object.'
            })


class AgentReputation(models.Model):
    """
    Reputation tracking for AI agents.
    """
    agent = models.OneToOneField(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='agent_reputation',
        help_text="Agent this reputation belongs to"
    )
    
    # Core reputation metrics
    overall_score = models.FloatField(
        default=0.0,
        help_text="Overall reputation score (0.0 to 100.0)"
    )
    trust_score = models.FloatField(
        default=0.0,
        help_text="Trust score (0.0 to 100.0)"
    )
    expertise_score = models.FloatField(
        default=0.0,
        help_text="Expertise score (0.0 to 100.0)"
    )
    engagement_score = models.FloatField(
        default=0.0,
        help_text="Engagement score (0.0 to 100.0)"
    )
    
    # Activity metrics
    total_posts = models.IntegerField(
        default=0,
        help_text="Total posts created"
    )
    total_comments = models.IntegerField(
        default=0,
        help_text="Total comments made"
    )
    total_reactions_received = models.IntegerField(
        default=0,
        help_text="Total reactions received"
    )
    total_reactions_given = models.IntegerField(
        default=0,
        help_text="Total reactions given"
    )
    
    # Quality metrics
    helpful_count = models.IntegerField(
        default=0,
        help_text="Number of helpful reactions received"
    )
    insightful_count = models.IntegerField(
        default=0,
        help_text="Number of insightful reactions received"
    )
    innovative_count = models.IntegerField(
        default=0,
        help_text="Number of innovative reactions received"
    )
    
    # Collaboration metrics
    collaboration_count = models.IntegerField(
        default=0,
        help_text="Number of collaborations"
    )
    successful_interactions = models.IntegerField(
        default=0,
        help_text="Number of successful interactions"
    )
    
    # Temporal data
    last_calculated_at = models.DateTimeField(
        auto_now=True,
        help_text="When reputation was last calculated"
    )
    calculation_version = models.IntegerField(
        default=1,
        help_text="Version of calculation algorithm"
    )
    
    class Meta:
        db_table = 'agent_reputations'
        verbose_name = 'Agent Reputation'
        verbose_name_plural = 'Agent Reputations'
        indexes = [
            models.Index(fields=['overall_score']),
            models.Index(fields=['last_calculated_at']),
        ]
    
    def __str__(self):
        return f"Reputation for {self.agent.name}: {self.overall_score:.2f}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate score bounds
        for score_name, score_value in [
            ('overall_score', self.overall_score),
            ('trust_score', self.trust_score),
            ('expertise_score', self.expertise_score),
            ('engagement_score', self.engagement_score)
        ]:
            if not (0.0 <= score_value <= 100.0):
                raise ValidationError({
                    score_name: f'{score_name} must be between 0.0 and 100.0.'
                })

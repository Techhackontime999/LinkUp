"""
AI Agents models for managing AI agent registration, authentication, and communication.
"""
import uuid
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class AIAgent(models.Model):
    """
    Model representing an AI agent registered on the platform.
    """
    AGENT_TYPE_CHOICES = [
        ('CONVERSATIONAL', 'Conversational'),
        ('TASK_BASED', 'Task-Based'),
        ('RESEARCH', 'Research'),
        ('CUSTOM', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(3), MaxLengthValidator(100)],
        help_text="Unique agent name (3-100 characters)"
    )
    agent_type = models.CharField(
        max_length=20,
        choices=AGENT_TYPE_CHOICES,
        default='CONVERSATIONAL',
        help_text="Type of AI agent"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the agent's purpose and capabilities"
    )
    capabilities = models.JSONField(
        default=dict,
        help_text="JSON object describing agent capabilities"
    )
    version = models.CharField(
        max_length=50,
        default='1.0.0',
        help_text="Agent version"
    )
    owner_email = models.EmailField(
        validators=[EmailValidator()],
        help_text="Email address of the agent owner"
    )
    api_key_hash = models.CharField(
        max_length=255,
        help_text="Securely hashed API key"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the agent is active"
    )
    is_suspended = models.BooleanField(
        default=False,
        help_text="Whether the agent is suspended"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when agent was created"
    )
    last_active_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last agent activity"
    )
    total_interactions = models.IntegerField(
        default=0,
        help_text="Total number of interactions"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata in JSON format"
    )
    
    class Meta:
        db_table = 'ai_agents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['agent_type']),
            models.Index(fields=['is_active', 'is_suspended']),
            models.Index(fields=['owner_email']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'AI Agent'
        verbose_name_plural = 'AI Agents'
    
    def __str__(self):
        return f"{self.name} ({self.agent_type})"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate name length
        if len(self.name) < 3 or len(self.name) > 100:
            raise ValidationError({
                'name': 'Agent name must be between 3 and 100 characters.'
            })
        
        # Validate capabilities is a dict
        if not isinstance(self.capabilities, dict):
            raise ValidationError({
                'capabilities': 'Capabilities must be a valid JSON object.'
            })
        
        # Validate metadata is a dict
        if not isinstance(self.metadata, dict):
            raise ValidationError({
                'metadata': 'Metadata must be a valid JSON object.'
            })


class AgentAPIKey(models.Model):
    """
    Model representing API keys for agent authentication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text="Agent this API key belongs to"
    )
    key_hash = models.CharField(
        max_length=255,
        help_text="Securely hashed API key"
    )
    key_prefix = models.CharField(
        max_length=8,
        help_text="First 8 characters of the key for identification"
    )
    name = models.CharField(
        max_length=100,
        help_text="Descriptive name for this API key"
    )
    scopes = models.JSONField(
        default=list,
        help_text="List of allowed operations/scopes"
    )
    rate_limit = models.IntegerField(
        default=1000,
        help_text="Maximum requests per minute"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this API key is active"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration timestamp (null = no expiration)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when key was created"
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last key usage"
    )
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this key has been used"
    )
    
    class Meta:
        db_table = 'agent_api_keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'is_active']),
            models.Index(fields=['key_prefix']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Agent API Key'
        verbose_name_plural = 'Agent API Keys'
    
    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate scopes is a list
        if not isinstance(self.scopes, list):
            raise ValidationError({
                'scopes': 'Scopes must be a valid JSON array.'
            })
        
        # Validate rate_limit is positive
        if self.rate_limit <= 0:
            raise ValidationError({
                'rate_limit': 'Rate limit must be a positive integer.'
            })
        
        # Validate expires_at is in the future
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError({
                'expires_at': 'Expiration date must be in the future.'
            })


class AgentMessage(models.Model):
    """
    Model representing messages exchanged between AI agents.
    """
    MESSAGE_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('JSON', 'JSON'),
        ('STRUCTURED', 'Structured'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('READ', 'Read'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text="Agent who sent the message"
    )
    recipient = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='received_messages',
        help_text="Agent who receives the message"
    )
    content = models.TextField(
        help_text="Message content (max 100KB)"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='TEXT',
        help_text="Type of message content"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional message metadata"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current message status"
    )
    priority = models.IntegerField(
        default=3,
        help_text="Message priority (1=highest, 5=lowest)"
    )
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Parent message for threading"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when message was created"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when message was sent"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when message was delivered"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when message was read"
    )
    latency_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Message delivery latency in milliseconds"
    )
    size_bytes = models.IntegerField(
        default=0,
        help_text="Message size in bytes"
    )
    
    class Meta:
        db_table = 'agent_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['parent_message']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Agent Message'
        verbose_name_plural = 'Agent Messages'
    
    def __str__(self):
        return f"Message from {self.sender.name} to {self.recipient.name}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate content size (100KB = 102400 bytes)
        content_size = len(self.content.encode('utf-8'))
        if content_size > 102400:
            raise ValidationError({
                'content': 'Message content cannot exceed 100KB.'
            })
        
        # Validate priority range
        if not (1 <= self.priority <= 5):
            raise ValidationError({
                'priority': 'Priority must be between 1 (highest) and 5 (lowest).'
            })
        
        # Validate metadata is a dict
        if not isinstance(self.metadata, dict):
            raise ValidationError({
                'metadata': 'Metadata must be a valid JSON object.'
            })
        
        # Validate sender and recipient are different
        if self.sender_id == self.recipient_id:
            raise ValidationError({
                'recipient': 'Sender and recipient must be different agents.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to calculate message size."""
        if not self.size_bytes:
            self.size_bytes = len(self.content.encode('utf-8'))
        super().save(*args, **kwargs)


class AgentInteraction(models.Model):
    """
    Model representing interactions between AI agents.
    """
    INTERACTION_TYPE_CHOICES = [
        ('CONVERSATION', 'Conversation'),
        ('COLLABORATION', 'Collaboration'),
        ('NEGOTIATION', 'Negotiation'),
        ('CUSTOM', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.UUIDField(
        default=uuid.uuid4,
        help_text="Session ID for grouping related interactions"
    )
    agent_1 = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='interactions_as_agent_1',
        help_text="First agent in the interaction"
    )
    agent_2 = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        related_name='interactions_as_agent_2',
        help_text="Second agent in the interaction"
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        default='CONVERSATION',
        help_text="Type of interaction"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when interaction started"
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when interaction ended"
    )
    message_count = models.IntegerField(
        default=0,
        help_text="Total number of messages exchanged"
    )
    total_duration_seconds = models.IntegerField(
        default=0,
        help_text="Total duration of interaction in seconds"
    )
    outcome = models.CharField(
        max_length=255,
        blank=True,
        help_text="Outcome or result of the interaction"
    )
    tags = models.JSONField(
        default=list,
        help_text="Tags for categorization and filtering"
    )
    metrics = models.JSONField(
        default=dict,
        help_text="Custom research metrics"
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Whether this interaction is archived"
    )
    
    class Meta:
        db_table = 'agent_interactions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['agent_1', 'agent_2']),
            models.Index(fields=['interaction_type']),
            models.Index(fields=['started_at']),
            models.Index(fields=['is_archived']),
        ]
        verbose_name = 'Agent Interaction'
        verbose_name_plural = 'Agent Interactions'
    
    def __str__(self):
        return f"Interaction between {self.agent_1.name} and {self.agent_2.name}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate tags is a list
        if not isinstance(self.tags, list):
            raise ValidationError({
                'tags': 'Tags must be a valid JSON array.'
            })
        
        # Validate metrics is a dict
        if not isinstance(self.metrics, dict):
            raise ValidationError({
                'metrics': 'Metrics must be a valid JSON object.'
            })
        
        # Validate ended_at is after started_at
        if self.ended_at and self.started_at and self.ended_at <= self.started_at:
            raise ValidationError({
                'ended_at': 'End time must be after start time.'
            })
        
        # Validate agents are different
        if self.agent_1_id == self.agent_2_id:
            raise ValidationError({
                'agent_2': 'Agents in an interaction must be different.'
            })


class ResearchMetric(models.Model):
    """
    Model representing research metrics for analyzing agent behavior.
    """
    METRIC_TYPE_CHOICES = [
        ('COUNTER', 'Counter'),
        ('GAUGE', 'Gauge'),
        ('HISTOGRAM', 'Histogram'),
        ('SUMMARY', 'Summary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_name = models.CharField(
        max_length=100,
        help_text="Name of the metric"
    )
    metric_type = models.CharField(
        max_length=20,
        choices=METRIC_TYPE_CHOICES,
        help_text="Type of metric"
    )
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='metrics',
        help_text="Agent this metric is associated with (optional)"
    )
    interaction = models.ForeignKey(
        AgentInteraction,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='metrics',
        help_text="Interaction this metric is associated with (optional)"
    )
    value = models.FloatField(
        help_text="Metric value"
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit of measurement"
    )
    dimensions = models.JSONField(
        default=dict,
        help_text="Multi-dimensional metric dimensions"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when metric was recorded"
    )
    aggregation_period = models.CharField(
        max_length=50,
        blank=True,
        help_text="Aggregation period (hourly, daily, weekly, etc.)"
    )
    
    class Meta:
        db_table = 'research_metrics'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_name', 'metric_type']),
            models.Index(fields=['agent', 'timestamp']),
            models.Index(fields=['interaction', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        verbose_name = 'Research Metric'
        verbose_name_plural = 'Research Metrics'
    
    def __str__(self):
        return f"{self.metric_name} ({self.metric_type}): {self.value}"
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Validate dimensions is a dict
        if not isinstance(self.dimensions, dict):
            raise ValidationError({
                'dimensions': 'Dimensions must be a valid JSON object.'
            })

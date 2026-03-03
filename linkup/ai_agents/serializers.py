"""
Serializers for AI Agents REST API.

This module provides serializers for converting model instances to/from JSON
for the REST API endpoints.
"""
from rest_framework import serializers
from .models import AIAgent, AgentAPIKey, AgentMessage, AgentInteraction, ResearchMetric


class AgentRegistrationSerializer(serializers.Serializer):
    """Serializer for agent registration requests."""
    name = serializers.CharField(min_length=3, max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    capabilities = serializers.JSONField()
    owner_email = serializers.EmailField()
    agent_type = serializers.ChoiceField(
        choices=['CONVERSATIONAL', 'TASK_BASED', 'RESEARCH', 'CUSTOM'],
        default='CONVERSATIONAL'
    )
    version = serializers.CharField(default='1.0.0', max_length=50)
    metadata = serializers.JSONField(required=False, default=dict)


class AgentAuthenticationSerializer(serializers.Serializer):
    """Serializer for agent authentication requests."""
    agent_id = serializers.UUIDField()
    api_key = serializers.CharField()


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh requests."""
    refresh_token = serializers.CharField()


class AgentProfileSerializer(serializers.ModelSerializer):
    """Serializer for agent profile data."""
    class Meta:
        model = AIAgent
        fields = [
            'id', 'name', 'agent_type', 'description', 'capabilities',
            'version', 'owner_email', 'is_active', 'is_suspended',
            'created_at', 'last_active_at', 'total_interactions', 'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'last_active_at', 'total_interactions']


class AgentProfileUpdateSerializer(serializers.Serializer):
    """Serializer for agent profile update requests."""
    description = serializers.CharField(required=False, allow_blank=True)
    capabilities = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    version = serializers.CharField(required=False, max_length=50)
    agent_type = serializers.ChoiceField(
        choices=['CONVERSATIONAL', 'TASK_BASED', 'RESEARCH', 'CUSTOM'],
        required=False
    )


class AgentDiscoverySerializer(serializers.ModelSerializer):
    """Serializer for agent discovery (list) responses."""
    class Meta:
        model = AIAgent
        fields = [
            'id', 'name', 'agent_type', 'description', 'capabilities',
            'version', 'created_at', 'last_active_at'
        ]


class MessageSendSerializer(serializers.Serializer):
    """Serializer for sending messages."""
    recipient_id = serializers.UUIDField()
    content = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=['TEXT', 'JSON', 'STRUCTURED'],
        default='TEXT'
    )
    metadata = serializers.JSONField(required=False, default=dict)
    priority = serializers.IntegerField(min_value=1, max_value=5, default=3)
    parent_message_id = serializers.UUIDField(required=False, allow_null=True)


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for message data."""
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)
    
    class Meta:
        model = AgentMessage
        fields = [
            'id', 'sender', 'sender_name', 'recipient', 'recipient_name',
            'content', 'message_type', 'metadata', 'status', 'priority',
            'parent_message', 'created_at', 'sent_at', 'delivered_at',
            'read_at', 'latency_ms', 'size_bytes'
        ]
        read_only_fields = [
            'id', 'sender', 'sender_name', 'recipient_name', 'status',
            'created_at', 'sent_at', 'delivered_at', 'read_at',
            'latency_ms', 'size_bytes'
        ]


class MessageMarkReadSerializer(serializers.Serializer):
    """Serializer for marking messages as read."""
    pass  # No fields needed, just the message_id from URL


class AgentMetricsSerializer(serializers.Serializer):
    """Serializer for agent metrics responses."""
    total_messages_sent = serializers.IntegerField()
    total_messages_received = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    unique_conversation_partners = serializers.IntegerField()
    conversation_partner_ids = serializers.ListField(child=serializers.CharField())
    average_response_time_ms = serializers.FloatField()
    min_response_time_ms = serializers.FloatField()
    max_response_time_ms = serializers.FloatField()
    response_count = serializers.IntegerField()
    message_frequency_per_hour = serializers.DictField()
    peak_activity_hours = serializers.ListField(child=serializers.IntegerField())
    peak_hour_message_count = serializers.IntegerField()
    conversation_style = serializers.CharField()
    average_message_length = serializers.FloatField()
    response_consistency = serializers.FloatField()
    topic_keywords = serializers.ListField(child=serializers.CharField())


class InteractionSerializer(serializers.ModelSerializer):
    """Serializer for interaction data."""
    agent_1_name = serializers.CharField(source='agent_1.name', read_only=True)
    agent_2_name = serializers.CharField(source='agent_2.name', read_only=True)
    
    class Meta:
        model = AgentInteraction
        fields = [
            'id', 'session_id', 'agent_1', 'agent_1_name', 'agent_2', 'agent_2_name',
            'interaction_type', 'started_at', 'ended_at', 'message_count',
            'total_duration_seconds', 'outcome', 'tags', 'metrics', 'is_archived'
        ]


class DataExportSerializer(serializers.Serializer):
    """Serializer for data export requests."""
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
    time_range_start = serializers.DateTimeField(required=False)
    time_range_end = serializers.DateTimeField(required=False)
    agent_id = serializers.UUIDField(required=False)
    interaction_type = serializers.ChoiceField(
        choices=['CONVERSATION', 'COLLABORATION', 'NEGOTIATION', 'CUSTOM'],
        required=False
    )


class DataAnonymizeSerializer(serializers.Serializer):
    """Serializer for data anonymization requests."""
    interaction_ids = serializers.ListField(child=serializers.UUIDField())


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API key data."""
    class Meta:
        model = AgentAPIKey
        fields = [
            'id', 'key_prefix', 'name', 'scopes', 'rate_limit',
            'is_active', 'expires_at', 'created_at', 'last_used_at', 'usage_count'
        ]
        read_only_fields = [
            'id', 'key_prefix', 'created_at', 'last_used_at', 'usage_count'
        ]


class SystemHealthSerializer(serializers.Serializer):
    """Serializer for system health metrics."""
    total_active_agents = serializers.IntegerField()
    messages_per_minute = serializers.FloatField()
    average_message_latency_ms = serializers.FloatField()
    websocket_connections = serializers.IntegerField()
    api_request_rate = serializers.DictField()
    timestamp = serializers.DateTimeField()

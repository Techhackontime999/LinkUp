"""
Django admin configuration for AI Agents models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.db.models import Count, Avg, Q
import csv
import json
from datetime import datetime
from .models import AIAgent, AgentAPIKey, AgentMessage, AgentInteraction, ResearchMetric


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    """Admin interface for AIAgent model with search, filters, and custom actions."""
    
    list_display = [
        'name',
        'agent_type',
        'owner_email',
        'is_active_badge',
        'is_suspended_badge',
        'total_interactions',
        'message_count',
        'created_at',
        'last_active_at',
    ]
    
    list_filter = [
        'agent_type',
        'is_active',
        'is_suspended',
        'created_at',
        'last_active_at',
    ]
    
    search_fields = [
        'name',
        'owner_email',
        'description',
        'id',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'last_active_at',
        'total_interactions',
        'api_key_hash',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'agent_type', 'description', 'version')
        }),
        ('Owner Information', {
            'fields': ('owner_email',)
        }),
        ('Configuration', {
            'fields': ('capabilities', 'metadata')
        }),
        ('Authentication', {
            'fields': ('api_key_hash',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_suspended')
        }),
        ('Statistics', {
            'fields': ('total_interactions', 'created_at', 'last_active_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['suspend_agents', 'unsuspend_agents', 'deactivate_agents', 'export_agents_csv']
    list_per_page = 100
    
    def is_active_badge(self, obj):
        """Display active status as colored badge."""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Active Status'
    
    def is_suspended_badge(self, obj):
        """Display suspended status as colored badge."""
        if obj.is_suspended:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Suspended</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Normal</span>'
        )
    is_suspended_badge.short_description = 'Suspension Status'
    
    def message_count(self, obj):
        """Display total message count (sent + received)."""
        sent = obj.sent_messages.count()
        received = obj.received_messages.count()
        return f"{sent + received} ({sent} sent, {received} received)"
    message_count.short_description = 'Messages'
    
    def suspend_agents(self, request, queryset):
        """Custom action to suspend selected agents."""
        updated = queryset.update(is_suspended=True)
        self.message_user(request, f'{updated} agent(s) successfully suspended.')
    suspend_agents.short_description = 'Suspend selected agents'
    
    def unsuspend_agents(self, request, queryset):
        """Custom action to unsuspend selected agents."""
        updated = queryset.update(is_suspended=False)
        self.message_user(request, f'{updated} agent(s) successfully unsuspended.')
    unsuspend_agents.short_description = 'Unsuspend selected agents'
    
    def deactivate_agents(self, request, queryset):
        """Custom action to deactivate selected agents."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} agent(s) successfully deactivated.')
    deactivate_agents.short_description = 'Deactivate selected agents'
    
    def export_agents_csv(self, request, queryset):
        """Custom action to export selected agents to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="agents_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Type', 'Owner Email', 'Active', 'Suspended', 'Total Interactions', 'Created At', 'Last Active'])
        
        for agent in queryset:
            writer.writerow([
                str(agent.id),
                agent.name,
                agent.agent_type,
                agent.owner_email,
                agent.is_active,
                agent.is_suspended,
                agent.total_interactions,
                agent.created_at.strftime('%Y-%m-%d %H:%M:%S') if agent.created_at else '',
                agent.last_active_at.strftime('%Y-%m-%d %H:%M:%S') if agent.last_active_at else '',
            ])
        
        return response
    export_agents_csv.short_description = 'Export selected agents to CSV'


class AgentAPIKeyInline(admin.TabularInline):
    """Inline display for Agent API Keys."""
    model = AgentAPIKey
    extra = 0
    fields = ['name', 'key_prefix', 'is_active', 'rate_limit', 'usage_count', 'last_used_at', 'created_at']
    readonly_fields = ['key_prefix', 'usage_count', 'last_used_at', 'created_at']
    can_delete = False


@admin.register(AgentAPIKey)
class AgentAPIKeyAdmin(admin.ModelAdmin):
    """Admin interface for AgentAPIKey model."""
    
    list_display = [
        'name',
        'agent_link',
        'key_prefix',
        'is_active_badge',
        'rate_limit',
        'usage_count',
        'last_used_at',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'created_at',
        'last_used_at',
    ]
    
    search_fields = [
        'name',
        'key_prefix',
        'agent__name',
    ]
    
    readonly_fields = [
        'id',
        'key_hash',
        'key_prefix',
        'usage_count',
        'last_used_at',
        'created_at',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'agent', 'name', 'key_prefix')
        }),
        ('Security', {
            'fields': ('key_hash', 'scopes'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('rate_limit', 'is_active', 'expires_at')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 100
    
    def agent_link(self, obj):
        """Display clickable link to agent."""
        url = reverse('admin:ai_agents_aiagent_change', args=[obj.agent.id])
        return format_html('<a href="{}">{}</a>', url, obj.agent.name)
    agent_link.short_description = 'Agent'
    
    def is_active_badge(self, obj):
        """Display active status as colored badge."""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'


class AgentMessageInline(admin.TabularInline):
    """Inline display for Agent Messages."""
    model = AgentMessage
    extra = 0
    fields = ['sender', 'recipient', 'content_preview', 'status', 'created_at']
    readonly_fields = ['sender', 'recipient', 'content_preview', 'status', 'created_at']
    can_delete = False
    
    def content_preview(self, obj):
        """Display truncated message content."""
        if len(obj.content) > 100:
            return obj.content[:100] + '...'
        return obj.content
    content_preview.short_description = 'Content'


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    """Admin interface for AgentMessage model with inline display."""
    
    list_display = [
        'id_short',
        'sender_link',
        'recipient_link',
        'content_preview',
        'message_type',
        'status_badge',
        'priority',
        'created_at',
        'latency_display',
    ]
    
    list_filter = [
        'message_type',
        'status',
        'priority',
        'created_at',
    ]
    
    search_fields = [
        'id',
        'sender__name',
        'recipient__name',
        'content',
    ]
    
    readonly_fields = [
        'id',
        'sender',
        'recipient',
        'created_at',
        'sent_at',
        'delivered_at',
        'read_at',
        'latency_ms',
        'size_bytes',
    ]
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'sender', 'recipient', 'message_type', 'priority')
        }),
        ('Content', {
            'fields': ('content', 'metadata')
        }),
        ('Threading', {
            'fields': ('parent_message',),
            'classes': ('collapse',)
        }),
        ('Status & Timing', {
            'fields': ('status', 'created_at', 'sent_at', 'delivered_at', 'read_at', 'latency_ms')
        }),
        ('Metrics', {
            'fields': ('size_bytes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_messages_csv', 'mark_as_read']
    list_per_page = 100
    
    def id_short(self, obj):
        """Display shortened ID."""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'
    
    def sender_link(self, obj):
        """Display clickable link to sender."""
        url = reverse('admin:ai_agents_aiagent_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.name)
    sender_link.short_description = 'Sender'
    
    def recipient_link(self, obj):
        """Display clickable link to recipient."""
        url = reverse('admin:ai_agents_aiagent_change', args=[obj.recipient.id])
        return format_html('<a href="{}">{}</a>', url, obj.recipient.name)
    recipient_link.short_description = 'Recipient'
    
    def content_preview(self, obj):
        """Display truncated message content."""
        if len(obj.content) > 50:
            return obj.content[:50] + '...'
        return obj.content
    content_preview.short_description = 'Content'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'PENDING': '#ffc107',
            'SENT': '#17a2b8',
            'DELIVERED': '#28a745',
            'READ': '#007bff',
            'FAILED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def latency_display(self, obj):
        """Display latency in human-readable format."""
        if obj.latency_ms is not None:
            if obj.latency_ms < 1000:
                return f"{obj.latency_ms} ms"
            else:
                return f"{obj.latency_ms / 1000:.2f} s"
        return '-'
    latency_display.short_description = 'Latency'
    
    def export_messages_csv(self, request, queryset):
        """Custom action to export selected messages to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="messages_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Sender', 'Recipient', 'Content', 'Type', 'Status', 'Priority', 'Created At', 'Latency (ms)'])
        
        for message in queryset:
            writer.writerow([
                str(message.id),
                message.sender.name,
                message.recipient.name,
                message.content,
                message.message_type,
                message.status,
                message.priority,
                message.created_at.strftime('%Y-%m-%d %H:%M:%S') if message.created_at else '',
                message.latency_ms if message.latency_ms else '',
            ])
        
        return response
    export_messages_csv.short_description = 'Export selected messages to CSV'
    
    def mark_as_read(self, request, queryset):
        """Custom action to mark selected messages as read."""
        from django.utils import timezone
        updated = queryset.filter(status__in=['DELIVERED', 'SENT']).update(
            status='READ',
            read_at=timezone.now()
        )
        self.message_user(request, f'{updated} message(s) marked as read.')
    mark_as_read.short_description = 'Mark selected messages as read'


@admin.register(AgentInteraction)
class AgentInteractionAdmin(admin.ModelAdmin):
    """Admin interface for AgentInteraction model with analytics."""
    
    list_display = [
        'id_short',
        'agent_1_link',
        'agent_2_link',
        'interaction_type',
        'message_count',
        'duration_display',
        'started_at',
        'ended_at',
        'is_archived',
    ]
    
    list_filter = [
        'interaction_type',
        'is_archived',
        'started_at',
    ]
    
    search_fields = [
        'id',
        'session_id',
        'agent_1__name',
        'agent_2__name',
        'outcome',
    ]
    
    readonly_fields = [
        'id',
        'session_id',
        'started_at',
        'analytics_summary',
    ]
    
    fieldsets = (
        ('Interaction Information', {
            'fields': ('id', 'session_id', 'agent_1', 'agent_2', 'interaction_type')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at', 'total_duration_seconds')
        }),
        ('Statistics', {
            'fields': ('message_count', 'outcome')
        }),
        ('Analytics', {
            'fields': ('analytics_summary',),
            'classes': ('collapse',)
        }),
        ('Categorization', {
            'fields': ('tags', 'metrics', 'is_archived'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['archive_interactions', 'unarchive_interactions', 'export_interactions_csv', 'export_interactions_json']
    list_per_page = 100
    
    def id_short(self, obj):
        """Display shortened ID."""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'
    
    def agent_1_link(self, obj):
        """Display clickable link to agent 1."""
        url = reverse('admin:ai_agents_aiagent_change', args=[obj.agent_1.id])
        return format_html('<a href="{}">{}</a>', url, obj.agent_1.name)
    agent_1_link.short_description = 'Agent 1'
    
    def agent_2_link(self, obj):
        """Display clickable link to agent 2."""
        url = reverse('admin:ai_agents_aiagent_change', args=[obj.agent_2.id])
        return format_html('<a href="{}">{}</a>', url, obj.agent_2.name)
    agent_2_link.short_description = 'Agent 2'
    
    def duration_display(self, obj):
        """Display duration in human-readable format."""
        if obj.total_duration_seconds:
            hours = obj.total_duration_seconds // 3600
            minutes = (obj.total_duration_seconds % 3600) // 60
            seconds = obj.total_duration_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return '-'
    duration_display.short_description = 'Duration'
    
    def analytics_summary(self, obj):
        """Display analytics summary for the interaction."""
        # Get messages for this interaction
        messages = AgentMessage.objects.filter(
            Q(sender=obj.agent_1, recipient=obj.agent_2) |
            Q(sender=obj.agent_2, recipient=obj.agent_1),
            created_at__gte=obj.started_at
        )
        
        if obj.ended_at:
            messages = messages.filter(created_at__lte=obj.ended_at)
        
        # Calculate analytics
        total_messages = messages.count()
        avg_latency = messages.aggregate(Avg('latency_ms'))['latency_ms__avg']
        
        agent_1_sent = messages.filter(sender=obj.agent_1).count()
        agent_2_sent = messages.filter(sender=obj.agent_2).count()
        
        html = f"""
        <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
            <h4 style="margin-top: 0;">Interaction Analytics</h4>
            <table style="width: 100%;">
                <tr><td><strong>Total Messages:</strong></td><td>{total_messages}</td></tr>
                <tr><td><strong>{obj.agent_1.name} sent:</strong></td><td>{agent_1_sent}</td></tr>
                <tr><td><strong>{obj.agent_2.name} sent:</strong></td><td>{agent_2_sent}</td></tr>
                <tr><td><strong>Avg Latency:</strong></td><td>{f"{avg_latency:.2f} ms" if avg_latency else "N/A"}</td></tr>
            </table>
        </div>
        """
        return mark_safe(html)
    analytics_summary.short_description = 'Analytics Summary'
    
    def archive_interactions(self, request, queryset):
        """Custom action to archive selected interactions."""
        updated = queryset.update(is_archived=True)
        self.message_user(request, f'{updated} interaction(s) successfully archived.')
    archive_interactions.short_description = 'Archive selected interactions'
    
    def unarchive_interactions(self, request, queryset):
        """Custom action to unarchive selected interactions."""
        updated = queryset.update(is_archived=False)
        self.message_user(request, f'{updated} interaction(s) successfully unarchived.')
    unarchive_interactions.short_description = 'Unarchive selected interactions'
    
    def export_interactions_csv(self, request, queryset):
        """Custom action to export selected interactions to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="interactions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Session ID', 'Agent 1', 'Agent 2', 'Type', 'Message Count', 'Duration (s)', 'Started At', 'Ended At', 'Outcome'])
        
        for interaction in queryset:
            writer.writerow([
                str(interaction.id),
                str(interaction.session_id),
                interaction.agent_1.name,
                interaction.agent_2.name,
                interaction.interaction_type,
                interaction.message_count,
                interaction.total_duration_seconds,
                interaction.started_at.strftime('%Y-%m-%d %H:%M:%S') if interaction.started_at else '',
                interaction.ended_at.strftime('%Y-%m-%d %H:%M:%S') if interaction.ended_at else '',
                interaction.outcome,
            ])
        
        return response
    export_interactions_csv.short_description = 'Export selected interactions to CSV'
    
    def export_interactions_json(self, request, queryset):
        """Custom action to export selected interactions to JSON."""
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="interactions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        data = []
        for interaction in queryset:
            data.append({
                'id': str(interaction.id),
                'session_id': str(interaction.session_id),
                'agent_1': {
                    'id': str(interaction.agent_1.id),
                    'name': interaction.agent_1.name,
                },
                'agent_2': {
                    'id': str(interaction.agent_2.id),
                    'name': interaction.agent_2.name,
                },
                'interaction_type': interaction.interaction_type,
                'message_count': interaction.message_count,
                'total_duration_seconds': interaction.total_duration_seconds,
                'started_at': interaction.started_at.isoformat() if interaction.started_at else None,
                'ended_at': interaction.ended_at.isoformat() if interaction.ended_at else None,
                'outcome': interaction.outcome,
                'tags': interaction.tags,
                'metrics': interaction.metrics,
                'is_archived': interaction.is_archived,
            })
        
        response.write(json.dumps(data, indent=2))
        return response
    export_interactions_json.short_description = 'Export selected interactions to JSON'



@admin.register(ResearchMetric)
class ResearchMetricAdmin(admin.ModelAdmin):
    """Admin interface for ResearchMetric model."""
    
    list_display = [
        'metric_name',
        'metric_type',
        'agent_link',
        'interaction_link',
        'value',
        'unit',
        'aggregation_period',
        'timestamp',
    ]
    
    list_filter = [
        'metric_type',
        'aggregation_period',
        'timestamp',
    ]
    
    search_fields = [
        'metric_name',
        'agent__name',
        'unit',
    ]
    
    readonly_fields = [
        'id',
        'timestamp',
    ]
    
    fieldsets = (
        ('Metric Information', {
            'fields': ('id', 'metric_name', 'metric_type', 'value', 'unit')
        }),
        ('Associations', {
            'fields': ('agent', 'interaction')
        }),
        ('Dimensions', {
            'fields': ('dimensions', 'aggregation_period'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    actions = ['export_metrics_csv']
    list_per_page = 100
    
    def agent_link(self, obj):
        """Display clickable link to agent."""
        if obj.agent:
            url = reverse('admin:ai_agents_aiagent_change', args=[obj.agent.id])
            return format_html('<a href="{}">{}</a>', url, obj.agent.name)
        return '-'
    agent_link.short_description = 'Agent'
    
    def interaction_link(self, obj):
        """Display clickable link to interaction."""
        if obj.interaction:
            url = reverse('admin:ai_agents_agentinteraction_change', args=[obj.interaction.id])
            return format_html('<a href="{}">View Interaction</a>', url)
        return '-'
    interaction_link.short_description = 'Interaction'
    
    def export_metrics_csv(self, request, queryset):
        """Custom action to export selected metrics to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="metrics_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Metric Name', 'Type', 'Agent', 'Value', 'Unit', 'Aggregation Period', 'Timestamp'])
        
        for metric in queryset:
            writer.writerow([
                str(metric.id),
                metric.metric_name,
                metric.metric_type,
                metric.agent.name if metric.agent else '',
                metric.value,
                metric.unit,
                metric.aggregation_period,
                metric.timestamp.strftime('%Y-%m-%d %H:%M:%S') if metric.timestamp else '',
            ])
        
        return response
    export_metrics_csv.short_description = 'Export selected metrics to CSV'

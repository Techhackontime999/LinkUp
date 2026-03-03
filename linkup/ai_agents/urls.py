"""
URL configuration for AI Agents REST API.

This module defines URL patterns for all agent API endpoints.
"""
from django.urls import path
from . import api_views
from . import admin_dashboard_views

app_name = 'ai_agents'

urlpatterns = [
    # Task 12.1: Agent registration and authentication endpoints
    path('agents/register', api_views.agent_register, name='agent_register'),
    path('agents/authenticate', api_views.agent_authenticate, name='agent_authenticate'),
    path('agents/token/refresh', api_views.token_refresh, name='token_refresh'),
    
    # Task 12.2: Agent profile management endpoints
    path('agents/<uuid:agent_id>', api_views.agent_profile_get, name='agent_profile_get'),
    path('agents/<uuid:agent_id>/update', api_views.agent_profile_update, name='agent_profile_update'),
    path('agents/<uuid:agent_id>/delete', api_views.agent_profile_delete, name='agent_profile_delete'),
    path('agents/<uuid:agent_id>/suspend', api_views.agent_suspend, name='agent_suspend'),
    path('agents/<uuid:agent_id>/unsuspend', api_views.agent_unsuspend, name='agent_unsuspend'),
    
    # Task 12.3: Agent discovery endpoints
    path('agents', api_views.agent_list, name='agent_list'),
    
    # Task 12.4: Messaging endpoints
    path('messages', api_views.message_send, name='message_send'),
    path('messages/list', api_views.message_list, name='message_list'),
    path('messages/conversation/<uuid:agent_id>', api_views.conversation_history, name='conversation_history'),
    path('messages/<uuid:message_id>/read', api_views.message_mark_read, name='message_mark_read'),
    
    # Task 12.5: Analytics and research endpoints
    path('analytics/agents/<uuid:agent_id>/metrics', api_views.agent_metrics, name='agent_metrics'),
    path('analytics/interactions', api_views.interactions_query, name='interactions_query'),
    path('analytics/export', api_views.data_export, name='data_export'),
    path('analytics/anonymize', api_views.data_anonymize, name='data_anonymize'),
    
    # Task 13.1: API key management endpoints
    path('agents/<uuid:agent_id>/api-keys', api_views.api_key_create, name='api_key_create'),
    path('agents/<uuid:agent_id>/api-keys/list', api_views.api_key_list, name='api_key_list'),
    path('agents/<uuid:agent_id>/api-keys/<uuid:key_id>', api_views.api_key_delete, name='api_key_delete'),
    
    # Task 14.2: System health monitoring endpoint
    path('health', api_views.system_health, name='system_health'),
    
    # Task 14.3: Threshold checking and alerting endpoints
    path('health/thresholds', api_views.check_thresholds, name='check_thresholds'),
    path('health/alerts', api_views.get_alerts, name='get_alerts'),
    path('health/alerts/<str:alert_timestamp>/acknowledge', api_views.acknowledge_alert, name='acknowledge_alert'),
    
    # Task 16.2: Admin dashboard views
    path('admin/dashboard', admin_dashboard_views.agent_dashboard, name='admin_dashboard'),
    path('admin/activity-chart-data/', admin_dashboard_views.agent_activity_chart_data, name='activity_chart_data'),
    path('admin/metrics-summary/', admin_dashboard_views.agent_metrics_summary, name='metrics_summary'),
    path('admin/interaction/<uuid:interaction_id>/', admin_dashboard_views.interaction_details, name='interaction_details'),
]

"""
URL configuration for AI Agents REST API.

This module defines URL patterns for all agent API endpoints.
"""
from django.urls import path
from . import api_views
from . import admin_dashboard_views
from . import multi_agent_views
from . import admin_ai_model_views

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
    
    # Admin AI Model Management
    path('admin/ai-models/', admin_ai_model_views.ai_model_management, name='ai_model_management'),
    path('admin/ai-models/add/', admin_ai_model_views.add_ai_model, name='add_ai_model'),
    path('admin/ai-models/<uuid:agent_id>/', admin_ai_model_views.ai_model_detail, name='ai_model_detail'),
    path('admin/ai-models/<uuid:agent_id>/edit/', admin_ai_model_views.edit_ai_model, name='edit_ai_model'),
    path('admin/ai-models/<uuid:agent_id>/toggle-status/', admin_ai_model_views.toggle_ai_model_status, name='toggle_ai_model_status'),
    path('admin/ai-models/<uuid:agent_id>/delete/', admin_ai_model_views.delete_ai_model, name='delete_ai_model'),
    path('admin/ai-models/<uuid:agent_id>/generate-key/', admin_ai_model_views.generate_api_key, name='generate_api_key'),
    path('admin/api-keys/<uuid:key_id>/revoke/', admin_ai_model_views.revoke_api_key, name='revoke_api_key'),
    
    # Multi-Agent Interaction endpoints
    path('multi-agent/chat/', multi_agent_views.multi_agent_chat, name='multi_agent_chat'),
    path('api/ask-multiple/', multi_agent_views.ask_multiple_agents, name='ask_multiple_agents'),
    path('api/discussion/', multi_agent_views.agent_discussion, name='agent_discussion'),
    path('api/consensus/', multi_agent_views.build_consensus, name='build_consensus'),
    path('interactions/feed/', multi_agent_views.agent_interactions_feed, name='interactions_feed'),
    path('api/capabilities/', multi_agent_views.get_agent_capabilities, name='get_capabilities'),
]


# AI Agent Social Platform endpoints
from . import social_auth_views
from . import social_profile_views
from . import social_post_views
from . import social_follow_views
from . import social_reaction_views
from . import social_comment_views
from . import social_feed_views
from . import social_discovery_views
from . import social_reputation_views
from . import social_notification_views

# Social Platform - Authentication
urlpatterns += [
    path('social/auth/token', social_auth_views.authenticate, name='social_auth_token'),
    path('social/auth/refresh', social_auth_views.refresh_token, name='social_auth_refresh'),
    path('social/auth/revoke', social_auth_views.revoke_token, name='social_auth_revoke'),
]

# Social Platform - Profiles
urlpatterns += [
    path('social/agents/<str:agent_id>/profile', social_profile_views.get_profile, name='social_profile_get'),
    path('social/agents/<str:agent_id>/profile/create', social_profile_views.create_profile, name='social_profile_create'),
    path('social/agents/<str:agent_id>/profile/update', social_profile_views.update_profile, name='social_profile_update'),
]

# Social Platform - Posts
urlpatterns += [
    path('social/agents/posts', social_post_views.create_post, name='social_post_create'),
    path('social/posts/<uuid:post_id>', social_post_views.get_post, name='social_post_get'),
    path('social/agents/<str:agent_id>/posts', social_post_views.get_agent_posts, name='social_agent_posts'),
    path('social/posts/<uuid:post_id>/delete', social_post_views.delete_post, name='social_post_delete'),
]

# Social Platform - Follow Relationships
urlpatterns += [
    path('social/agents/<str:agent_id>/follow', social_follow_views.follow_agent, name='social_follow'),
    path('social/agents/<str:agent_id>/unfollow', social_follow_views.unfollow_agent, name='social_unfollow'),
    path('social/agents/<str:agent_id>/followers', social_follow_views.get_followers, name='social_followers'),
    path('social/agents/<str:agent_id>/following', social_follow_views.get_following, name='social_following'),
]

# Social Platform - Reactions
urlpatterns += [
    path('social/posts/<uuid:post_id>/reactions', social_reaction_views.add_reaction, name='social_reaction_add'),
    path('social/posts/<uuid:post_id>/reactions/remove', social_reaction_views.remove_reaction, name='social_reaction_remove'),
    path('social/posts/<uuid:post_id>/reactions/list', social_reaction_views.get_reactions, name='social_reactions_list'),
    path('social/comments/<uuid:comment_id>/reactions', social_reaction_views.add_comment_reaction, name='social_comment_reaction_add'),
    path('social/comments/<uuid:comment_id>/reactions/remove', social_reaction_views.remove_comment_reaction, name='social_comment_reaction_remove'),
]

# Social Platform - Comments
urlpatterns += [
    path('social/posts/<uuid:post_id>/comments', social_comment_views.create_comment, name='social_comment_create'),
    path('social/posts/<uuid:post_id>/comments/list', social_comment_views.get_comments, name='social_comments_list'),
    path('social/comments/<uuid:comment_id>/replies', social_comment_views.create_reply, name='social_reply_create'),
    path('social/comments/<uuid:comment_id>/replies/list', social_comment_views.get_replies, name='social_replies_list'),
    path('social/comments/<uuid:comment_id>', social_comment_views.update_comment, name='social_comment_update'),
    path('social/comments/<uuid:comment_id>/delete', social_comment_views.delete_comment, name='social_comment_delete'),
]

# Social Platform - Feed
urlpatterns += [
    path('social/agents/feed', social_feed_views.get_feed, name='social_feed'),
]

# Social Platform - Discovery
urlpatterns += [
    path('social/agents/discover', social_discovery_views.discover_agents, name='social_discover'),
]

# Social Platform - Reputation
urlpatterns += [
    path('social/agents/<str:agent_id>/reputation', social_reputation_views.get_reputation, name='social_reputation_get'),
    path('social/agents/<str:agent_id>/reputation/calculate', social_reputation_views.calculate_reputation, name='social_reputation_calculate'),
]

# Social Platform - Notifications
urlpatterns += [
    path('social/notifications', social_notification_views.get_notifications, name='social_notifications'),
    path('social/notifications/unread', social_notification_views.get_unread_notifications, name='social_notifications_unread'),
    path('social/notifications/<uuid:notification_id>/read', social_notification_views.mark_notification_read, name='social_notification_read'),
]

# Social Platform - Collaboration Spaces
from . import social_collaboration_views

urlpatterns += [
    path('social/spaces', social_collaboration_views.create_space, name='social_space_create'),
    path('social/spaces/<uuid:space_id>/invite', social_collaboration_views.invite_to_space, name='social_space_invite'),
    path('social/spaces/<uuid:space_id>/join', social_collaboration_views.join_space, name='social_space_join'),
    path('social/spaces/<uuid:space_id>/members', social_collaboration_views.get_space_members, name='social_space_members'),
    path('social/spaces/<uuid:space_id>/posts', social_collaboration_views.create_space_post, name='social_space_post'),
]

# Social Platform - Marketplace
from . import social_marketplace_views

urlpatterns += [
    path('social/marketplace/listings', social_marketplace_views.create_listing, name='social_marketplace_create'),
    path('social/marketplace/search', social_marketplace_views.search_marketplace, name='social_marketplace_search'),
    path('social/marketplace/listings/<uuid:listing_id>', social_marketplace_views.get_listing, name='social_marketplace_get'),
    path('social/marketplace/listings/<uuid:listing_id>/rate', social_marketplace_views.rate_listing, name='social_marketplace_rate'),
]

# Social Platform - Moderation
from . import social_moderation_views

urlpatterns += [
    path('social/admin/posts/<uuid:post_id>/flag', social_moderation_views.flag_post, name='social_moderation_flag_post'),
    path('social/admin/comments/<uuid:comment_id>/flag', social_moderation_views.flag_comment, name='social_moderation_flag_comment'),
    path('social/admin/moderation/queue', social_moderation_views.get_moderation_queue, name='social_moderation_queue'),
    path('social/admin/posts/<uuid:post_id>', social_moderation_views.remove_post, name='social_moderation_remove_post'),
    path('social/admin/comments/<uuid:comment_id>', social_moderation_views.remove_comment, name='social_moderation_remove_comment'),
    path('social/admin/agents/<str:agent_id>/suspend', social_moderation_views.suspend_agent, name='social_moderation_suspend'),
    path('social/admin/agents/<str:agent_id>/unsuspend', social_moderation_views.unsuspend_agent, name='social_moderation_unsuspend'),
    path('social/admin/moderation/logs', social_moderation_views.get_moderation_logs, name='social_moderation_logs'),
]

# Social Platform - Analytics and Monitoring
from . import social_analytics_views

urlpatterns += [
    path('social/metrics', social_analytics_views.metrics_export, name='social_metrics_export'),
    path('social/analytics/metrics', social_analytics_views.platform_metrics, name='social_analytics_metrics'),
    path('social/analytics/errors', social_analytics_views.recent_errors, name='social_analytics_errors'),
    path('social/analytics/agents/<str:agent_id>/activity', social_analytics_views.agent_activity_report, name='social_analytics_agent_activity'),
    path('social/analytics/summary', social_analytics_views.platform_summary, name='social_analytics_summary'),
    path('social/analytics/trending', social_analytics_views.trending_content, name='social_analytics_trending'),
    path('social/analytics/alerts/check', social_analytics_views.check_thresholds, name='social_analytics_check_thresholds'),
    path('social/analytics/alerts', social_analytics_views.get_alerts, name='social_analytics_alerts'),
    path('social/analytics/alerts/<str:alert_timestamp>/acknowledge', social_analytics_views.acknowledge_alert, name='social_analytics_acknowledge_alert'),
]

# Social Platform - Analytics and Monitoring
from . import social_analytics_views

urlpatterns += [
    path('social/metrics', social_analytics_views.metrics_export, name='social_metrics_export'),
    path('social/analytics/metrics', social_analytics_views.platform_metrics, name='social_analytics_metrics'),
    path('social/analytics/errors', social_analytics_views.recent_errors, name='social_analytics_errors'),
    path('social/analytics/agents/<str:agent_id>/activity', social_analytics_views.agent_activity_report, name='social_analytics_agent_activity'),
    path('social/analytics/summary', social_analytics_views.platform_summary, name='social_analytics_summary'),
    path('social/analytics/trending', social_analytics_views.trending_content, name='social_analytics_trending'),
    path('social/analytics/alerts/check', social_analytics_views.check_thresholds, name='social_analytics_check_thresholds'),
    path('social/analytics/alerts', social_analytics_views.get_alerts, name='social_analytics_alerts'),
    path('social/analytics/alerts/<str:alert_timestamp>/acknowledge', social_analytics_views.acknowledge_alert, name='social_analytics_acknowledge_alert'),
]

# Social Platform - Metrics Consistency
from . import social_metrics_views

urlpatterns += [
    path('social/metrics/posts/<uuid:post_id>/reconcile', social_metrics_views.reconcile_post_metrics, name='social_metrics_reconcile_post'),
    path('social/metrics/profiles/<str:agent_id>/reconcile', social_metrics_views.reconcile_profile_metrics, name='social_metrics_reconcile_profile'),
    path('social/metrics/posts/reconcile-all', social_metrics_views.reconcile_all_posts, name='social_metrics_reconcile_all_posts'),
    path('social/metrics/profiles/reconcile-all', social_metrics_views.reconcile_all_profiles, name='social_metrics_reconcile_all_profiles'),
    path('social/metrics/reconcile-all', social_metrics_views.run_full_reconciliation, name='social_metrics_reconcile_all'),
]


# Social Platform - Metrics Consistency
from . import social_metrics_views

urlpatterns += [
    path('social/metrics/posts/<uuid:post_id>/reconcile', social_metrics_views.reconcile_post_metrics, name='social_metrics_reconcile_post'),
    path('social/metrics/profiles/<str:agent_id>/reconcile', social_metrics_views.reconcile_profile_metrics, name='social_metrics_reconcile_profile'),
    path('social/metrics/posts/reconcile-all', social_metrics_views.reconcile_all_posts, name='social_metrics_reconcile_all_posts'),
    path('social/metrics/profiles/reconcile-all', social_metrics_views.reconcile_all_profiles, name='social_metrics_reconcile_all_profiles'),
    path('social/metrics/reconcile-all', social_metrics_views.run_full_reconciliation, name='social_metrics_reconcile_all'),
]

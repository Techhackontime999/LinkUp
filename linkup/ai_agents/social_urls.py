"""
URL routing for AI Agent Social Platform API.

Provides routes for:
- Authentication
- Social profiles
- Posts
- Follow relationships
- Feed
- Reactions
- Comments
- Notifications
- Discovery
- Collaboration spaces
- Marketplace
- Reputation
"""
from django.urls import path
from . import social_auth_views
from . import social_profile_views
# from . import social_post_views
# from . import social_follow_views
# from . import social_feed_views
# from . import social_reaction_views
# from . import social_comment_views
# from . import social_notification_views
# from . import social_discovery_views
# from . import social_space_views
# from . import social_marketplace_views
# from . import social_reputation_views

app_name = 'social'

urlpatterns = [
    # Authentication endpoints
    path('auth/token', social_auth_views.authenticate, name='auth_token'),
    path('auth/refresh', social_auth_views.refresh_token, name='auth_refresh'),
    path('auth/revoke', social_auth_views.revoke_token, name='auth_revoke'),
    
    # Profile management endpoints
    path('agents/<str:agent_id>/profile', social_profile_views.create_profile, name='profile_create'),
    path('agents/<str:agent_id>/profile', social_profile_views.get_profile, name='profile_get'),
    path('agents/<str:agent_id>/profile', social_profile_views.update_profile, name='profile_update'),
    
    # Post endpoints (to be implemented)
    # path('agents/posts', social_post_views.create_post, name='post_create'),
    # path('posts/<str:post_id>', social_post_views.get_post, name='post_get'),
    # path('agents/<str:agent_id>/posts', social_post_views.get_agent_posts, name='agent_posts'),
    # path('posts/<str:post_id>', social_post_views.delete_post, name='post_delete'),
    
    # Follow endpoints (to be implemented)
    # path('agents/<str:agent_id>/follow', social_follow_views.follow_agent, name='follow'),
    # path('agents/<str:agent_id>/follow', social_follow_views.unfollow_agent, name='unfollow'),
    # path('agents/<str:agent_id>/followers', social_follow_views.get_followers, name='followers'),
    # path('agents/<str:agent_id>/following', social_follow_views.get_following, name='following'),
    
    # Feed endpoints (to be implemented)
    # path('agents/feed', social_feed_views.get_feed, name='feed'),
    # path('agents/feed/trending', social_feed_views.get_trending, name='feed_trending'),
    
    # Reaction endpoints (to be implemented)
    # path('posts/<str:post_id>/reactions', social_reaction_views.add_reaction, name='reaction_add'),
    # path('posts/<str:post_id>/reactions/<str:reaction_type>', social_reaction_views.remove_reaction, name='reaction_remove'),
    # path('posts/<str:post_id>/reactions', social_reaction_views.get_reactions, name='reactions_get'),
    
    # Comment endpoints (to be implemented)
    # path('posts/<str:post_id>/comments', social_comment_views.create_comment, name='comment_create'),
    # path('posts/<str:post_id>/comments', social_comment_views.get_comments, name='comments_get'),
    # path('comments/<str:comment_id>/replies', social_comment_views.create_reply, name='comment_reply'),
    # path('comments/<str:comment_id>', social_comment_views.update_comment, name='comment_update'),
    # path('comments/<str:comment_id>', social_comment_views.delete_comment, name='comment_delete'),
    
    # Notification endpoints (to be implemented)
    # path('notifications', social_notification_views.get_notifications, name='notifications'),
    # path('notifications/unread', social_notification_views.get_unread, name='notifications_unread'),
    # path('notifications/<str:notification_id>/read', social_notification_views.mark_read, name='notification_read'),
    
    # Discovery endpoints (to be implemented)
    # path('agents/discover', social_discovery_views.discover_agents, name='discover'),
    # path('agents/search', social_discovery_views.search_agents, name='search'),
    
    # Collaboration space endpoints (to be implemented)
    # path('spaces', social_space_views.create_space, name='space_create'),
    # path('spaces/<str:space_id>', social_space_views.get_space, name='space_get'),
    # path('spaces/<str:space_id>/invite', social_space_views.invite_to_space, name='space_invite'),
    # path('spaces/<str:space_id>/join', social_space_views.join_space, name='space_join'),
    # path('spaces/<str:space_id>/members', social_space_views.get_members, name='space_members'),
    # path('spaces/<str:space_id>/posts', social_space_views.create_space_post, name='space_post'),
    
    # Marketplace endpoints (to be implemented)
    # path('marketplace/listings', social_marketplace_views.create_listing, name='listing_create'),
    # path('marketplace/search', social_marketplace_views.search_marketplace, name='marketplace_search'),
    # path('marketplace/listings/<str:listing_id>', social_marketplace_views.get_listing, name='listing_get'),
    # path('marketplace/listings/<str:listing_id>/rate', social_marketplace_views.rate_listing, name='listing_rate'),
    
    # Reputation endpoints (to be implemented)
    # path('agents/<str:agent_id>/reputation', social_reputation_views.get_reputation, name='reputation_get'),
]

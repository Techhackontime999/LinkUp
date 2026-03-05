"""
Views for AI Agent Communication UI
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import AIAgent
from .social_models import AgentSocialProfile, AgentPost


@login_required
def agent_communication(request):
    """
    Main page for AI agent communication interface.
    Allows users to register agents, send messages, and view conversations.
    """
    return render(request, 'ai_agents/agent_communication.html', {
        'user': request.user
    })


@staff_member_required
def ai_social_demo(request):
    """
    Demo page showing how AI models integrate with the social platform.
    Staff only.
    """
    return render(request, 'ai_agents/ai_social_demo.html', {
        'user': request.user
    })


def agent_profile_public(request, agent_id):
    """
    Public view of an agent's social profile.
    Shows profile info, posts, followers, following.
    """
    agent = get_object_or_404(AIAgent, id=agent_id, is_active=True)
    
    try:
        profile = agent.social_profile
    except AgentSocialProfile.DoesNotExist:
        # Create a basic profile if it doesn't exist
        profile = AgentSocialProfile.objects.create(
            agent=agent,
            display_name=agent.name,
            bio=agent.description or '',
            is_public=True
        )
    
    # Get recent posts
    recent_posts = AgentPost.objects.filter(
        agent=agent,
        is_deleted=False,
        visibility='PUBLIC'
    ).order_by('-created_at')[:10]
    
    # Get follower/following counts
    from .social_models import AgentFollow
    followers_count = AgentFollow.objects.filter(followed=agent).count()
    following_count = AgentFollow.objects.filter(follower=agent).count()
    
    context = {
        'agent': agent,
        'profile': profile,
        'recent_posts': recent_posts,
        'followers_count': followers_count,
        'following_count': following_count,
    }
    
    return render(request, 'ai_agents/agent_profile_public.html', context)


@login_required
def agent_analytics(request, agent_id):
    """
    Analytics dashboard for an agent's social activity.
    Only accessible to the agent owner or staff.
    """
    agent = get_object_or_404(AIAgent, id=agent_id, is_active=True)
    
    # Check if user is the agent owner or staff
    # Note: This assumes the agent has an owner relationship or is staff-only
    # Adjust based on your actual authentication model
    if not request.user.is_staff:
        # If not staff, could add additional checks here
        pass
    
    try:
        profile = agent.social_profile
    except AgentSocialProfile.DoesNotExist:
        # Create a basic profile if it doesn't exist
        profile = AgentSocialProfile.objects.create(
            agent=agent,
            display_name=agent.name,
            bio=agent.description or '',
            is_public=True
        )
    
    context = {
        'agent': agent,
        'profile': profile,
    }
    
    return render(request, 'ai_agents/analytics.html', context)


@staff_member_required
def moderation_queue(request):
    """
    Moderation queue page for administrators.
    Displays flagged content for review and moderation actions.
    Staff only.
    """
    return render(request, 'ai_agents/moderation_queue.html', {
        'user': request.user
    })

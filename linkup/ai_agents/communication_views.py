"""
Views for AI Agent Communication UI
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


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

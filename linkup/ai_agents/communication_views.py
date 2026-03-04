"""
Views for AI Agent Communication UI
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def agent_communication(request):
    """
    Main page for AI agent communication interface.
    Allows users to register agents, send messages, and view conversations.
    """
    return render(request, 'ai_agents/agent_communication.html', {
        'user': request.user
    })

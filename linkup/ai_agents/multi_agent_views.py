"""
Views for multi-agent interactions on the social media platform.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from .agent_integrations import MultiAgentOrchestrator, ChatGPTIntegration, GeminiIntegration, ClaudeIntegration
from .services import AgentCommunicationService


# Global orchestrator instance (in production, use proper state management)
_orchestrator = None


def get_orchestrator():
    """Get or create the multi-agent orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


@login_required
def multi_agent_chat(request):
    """
    Main page for multi-agent chat interface.
    """
    context = {
        'page_title': 'Multi-Agent AI Chat',
        'available_agents': ['ChatGPT-4', 'Gemini-Pro', 'Claude-3']
    }
    return render(request, 'ai_agents/multi_agent_chat.html', context)


@require_http_methods(["POST"])
@csrf_exempt
def ask_multiple_agents(request):
    """
    API endpoint to ask multiple AI agents a question.
    """
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
        selected_agents = data.get('agents', ['ChatGPT-4', 'Gemini-Pro', 'Claude-3'])
        
        if not question:
            return JsonResponse({
                'status': 'error',
                'message': 'Question is required'
            }, status=400)
        
        orchestrator = get_orchestrator()
        
        # Get responses from selected agents
        responses = orchestrator.collaborative_response(question, selected_agents)
        
        return JsonResponse({
            'status': 'success',
            'question': question,
            'responses': responses
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def agent_discussion(request):
    """
    API endpoint to facilitate a discussion between agents.
    """
    try:
        data = json.loads(request.body)
        topic = data.get('topic', '')
        selected_agents = data.get('agents', ['ChatGPT-4', 'Gemini-Pro'])
        rounds = data.get('rounds', 2)
        
        if not topic:
            return JsonResponse({
                'status': 'error',
                'message': 'Topic is required'
            }, status=400)
        
        orchestrator = get_orchestrator()
        
        # Facilitate discussion
        discussion = orchestrator.agent_to_agent_discussion(
            topic=topic,
            agent_names=selected_agents,
            rounds=rounds
        )
        
        return JsonResponse({
            'status': 'success',
            'topic': topic,
            'discussion': discussion
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def build_consensus(request):
    """
    API endpoint to build consensus among multiple agents.
    """
    try:
        data = json.loads(request.body)
        question = data.get('question', '')
        selected_agents = data.get('agents', ['ChatGPT-4', 'Gemini-Pro', 'Claude-3'])
        
        if not question:
            return JsonResponse({
                'status': 'error',
                'message': 'Question is required'
            }, status=400)
        
        orchestrator = get_orchestrator()
        
        # Build consensus
        result = orchestrator.consensus_building(
            question=question,
            agent_names=selected_agents
        )
        
        return JsonResponse({
            'status': 'success',
            'result': result
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def agent_interactions_feed(request):
    """
    Display a feed of agent-to-agent interactions (like a social media feed).
    """
    # Get recent agent interactions
    from .models import AgentInteraction, AgentMessage
    
    interactions = AgentInteraction.objects.select_related(
        'agent_1', 'agent_2'
    ).order_by('-started_at')[:50]
    
    context = {
        'page_title': 'AI Agent Interactions Feed',
        'interactions': interactions
    }
    return render(request, 'ai_agents/interactions_feed.html', context)


@require_http_methods(["GET"])
def get_agent_capabilities(request):
    """
    Get capabilities of all registered agents.
    """
    from .models import AIAgent
    
    agents = AIAgent.objects.filter(is_active=True, is_suspended=False)
    
    agents_data = []
    for agent in agents:
        agents_data.append({
            'id': str(agent.id),
            'name': agent.name,
            'type': agent.agent_type,
            'description': agent.description,
            'capabilities': agent.capabilities,
            'version': agent.version
        })
    
    return JsonResponse({
        'status': 'success',
        'agents': agents_data,
        'count': len(agents_data)
    })

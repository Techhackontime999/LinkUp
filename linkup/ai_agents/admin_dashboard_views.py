"""
Admin dashboard views for AI Agent platform.

This module provides dashboard views for researchers to monitor:
- System overview with key metrics
- Recent agent interactions
- Agent activity charts

Requirements: 7.1, 20.1, 20.2
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from typing import Dict, List, Any
import logging

from .models import AIAgent, AgentMessage, AgentInteraction, ResearchMetric
from .metrics_tracker import SystemMetricsTracker
from .analytics_engine import ResearchAnalyticsEngine

logger = logging.getLogger('ai_agents.admin_dashboard')


@staff_member_required
def agent_dashboard(request):
    """
    Main dashboard view for AI agent platform monitoring.
    
    Displays:
    - System overview with key metrics
    - Recent interactions
    - Agent activity summary
    
    Requirements: 7.1, 20.1, 20.2
    """
    try:
        # Get system metrics
        system_metrics = SystemMetricsTracker.get_all_metrics()
        
        # Get agent statistics
        agent_stats = _get_agent_statistics()
        
        # Get recent interactions (last 10)
        recent_interactions = _get_recent_interactions(limit=10)
        
        # Get activity summary for last 24 hours
        activity_summary = _get_activity_summary()
        
        context = {
            'title': 'AI Agent Dashboard',
            'system_metrics': system_metrics.get('metrics', {}),
            'agent_stats': agent_stats,
            'recent_interactions': recent_interactions,
            'activity_summary': activity_summary,
        }
        
        return render(request, 'admin/ai_agents/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading agent dashboard: {str(e)}", exc_info=True)
        context = {
            'title': 'AI Agent Dashboard',
            'error': str(e),
        }
        return render(request, 'admin/ai_agents/dashboard.html', context)


@staff_member_required
def agent_activity_chart_data(request):
    """
    API endpoint for agent activity chart data.
    
    Returns time-series data for:
    - Message counts per hour (last 24 hours)
    - Active agents per hour
    - Average response times
    
    Requirements: 7.1, 20.2
    """
    try:
        # Get time range from query params (default: last 24 hours)
        hours = int(request.GET.get('hours', 24))
        
        # Calculate time range
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Generate hourly buckets
        chart_data = _generate_hourly_chart_data(start_time, end_time)
        
        return JsonResponse({
            'success': True,
            'data': chart_data,
        })
        
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@staff_member_required
def agent_metrics_summary(request):
    """
    API endpoint for real-time agent metrics summary.
    
    Returns current system health metrics and agent statistics.
    
    Requirements: 20.1, 20.2
    """
    try:
        # Get current system metrics
        system_metrics = SystemMetricsTracker.get_all_metrics()
        
        # Get agent statistics
        agent_stats = _get_agent_statistics()
        
        # Get top active agents (last 24 hours)
        top_agents = _get_top_active_agents(limit=5)
        
        return JsonResponse({
            'success': True,
            'system_metrics': system_metrics.get('metrics', {}),
            'agent_stats': agent_stats,
            'top_agents': top_agents,
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@staff_member_required
def interaction_details(request, interaction_id):
    """
    API endpoint for detailed interaction information.
    
    Returns full details of a specific interaction including:
    - Participants
    - Message history
    - Metrics and analytics
    
    Requirements: 7.1
    """
    try:
        interaction = AgentInteraction.objects.select_related(
            'agent_1', 'agent_2'
        ).get(id=interaction_id)
        
        # Get messages in this interaction
        messages = AgentMessage.objects.filter(
            Q(sender=interaction.agent_1, recipient=interaction.agent_2) |
            Q(sender=interaction.agent_2, recipient=interaction.agent_1)
        ).filter(
            created_at__gte=interaction.started_at,
            created_at__lte=interaction.ended_at if interaction.ended_at else timezone.now()
        ).order_by('created_at')
        
        # Format interaction data
        interaction_data = {
            'id': str(interaction.id),
            'session_id': str(interaction.session_id),
            'agent_1': {
                'id': str(interaction.agent_1.id),
                'name': interaction.agent_1.name,
                'type': interaction.agent_1.agent_type,
            },
            'agent_2': {
                'id': str(interaction.agent_2.id),
                'name': interaction.agent_2.name,
                'type': interaction.agent_2.agent_type,
            },
            'interaction_type': interaction.interaction_type,
            'started_at': interaction.started_at.isoformat(),
            'ended_at': interaction.ended_at.isoformat() if interaction.ended_at else None,
            'message_count': interaction.message_count,
            'duration_seconds': interaction.total_duration_seconds,
            'outcome': interaction.outcome,
            'tags': interaction.tags,
            'metrics': interaction.metrics,
            'messages': [
                {
                    'id': str(msg.id),
                    'sender': msg.sender.name,
                    'recipient': msg.recipient.name,
                    'content_preview': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'status': msg.status,
                    'latency_ms': msg.latency_ms,
                }
                for msg in messages[:50]  # Limit to 50 messages
            ],
        }
        
        return JsonResponse({
            'success': True,
            'interaction': interaction_data,
        })
        
    except AgentInteraction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Interaction not found',
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting interaction details: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


# Helper functions

def _get_agent_statistics() -> Dict[str, Any]:
    """
    Calculate agent statistics.
    
    Returns:
        Dictionary with agent counts and status breakdown
    
    Requirements: 20.1
    """
    total_agents = AIAgent.objects.count()
    active_agents = AIAgent.objects.filter(is_active=True, is_suspended=False).count()
    suspended_agents = AIAgent.objects.filter(is_suspended=True).count()
    inactive_agents = AIAgent.objects.filter(is_active=False).count()
    
    # Get agent type breakdown
    agent_types = AIAgent.objects.values('agent_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get recently registered agents (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    new_agents = AIAgent.objects.filter(created_at__gte=seven_days_ago).count()
    
    return {
        'total': total_agents,
        'active': active_agents,
        'suspended': suspended_agents,
        'inactive': inactive_agents,
        'new_last_7_days': new_agents,
        'by_type': list(agent_types),
    }


def _get_recent_interactions(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent agent interactions.
    
    Args:
        limit: Maximum number of interactions to return
    
    Returns:
        List of interaction dictionaries
    
    Requirements: 7.1
    """
    interactions = AgentInteraction.objects.select_related(
        'agent_1', 'agent_2'
    ).order_by('-started_at')[:limit]
    
    return [
        {
            'id': str(interaction.id),
            'agent_1_name': interaction.agent_1.name,
            'agent_2_name': interaction.agent_2.name,
            'interaction_type': interaction.interaction_type,
            'started_at': interaction.started_at,
            'message_count': interaction.message_count,
            'duration_seconds': interaction.total_duration_seconds,
        }
        for interaction in interactions
    ]


def _get_activity_summary() -> Dict[str, Any]:
    """
    Get activity summary for the last 24 hours.
    
    Returns:
        Dictionary with activity metrics
    
    Requirements: 7.1, 20.2
    """
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    
    # Count messages in last 24 hours
    total_messages = AgentMessage.objects.filter(
        created_at__gte=twenty_four_hours_ago
    ).count()
    
    # Count interactions in last 24 hours
    total_interactions = AgentInteraction.objects.filter(
        started_at__gte=twenty_four_hours_ago
    ).count()
    
    # Calculate average response time
    avg_response_time = AgentMessage.objects.filter(
        created_at__gte=twenty_four_hours_ago,
        latency_ms__isnull=False
    ).aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
    
    # Count unique active agents (sent or received messages)
    active_agent_ids = set()
    messages = AgentMessage.objects.filter(
        created_at__gte=twenty_four_hours_ago
    ).values_list('sender_id', 'recipient_id')
    
    for sender_id, recipient_id in messages:
        active_agent_ids.add(sender_id)
        active_agent_ids.add(recipient_id)
    
    return {
        'total_messages': total_messages,
        'total_interactions': total_interactions,
        'avg_response_time_ms': round(avg_response_time, 2),
        'unique_active_agents': len(active_agent_ids),
        'time_range': '24 hours',
    }


def _generate_hourly_chart_data(start_time, end_time) -> Dict[str, List]:
    """
    Generate hourly chart data for the specified time range.
    
    Args:
        start_time: Start of time range
        end_time: End of time range
    
    Returns:
        Dictionary with chart data arrays
    
    Requirements: 7.1, 20.2
    """
    hours = []
    message_counts = []
    active_agent_counts = []
    avg_latencies = []
    
    current_time = start_time
    
    while current_time < end_time:
        next_hour = current_time + timedelta(hours=1)
        
        # Format hour label
        hours.append(current_time.strftime('%m/%d %H:%M'))
        
        # Count messages in this hour
        message_count = AgentMessage.objects.filter(
            created_at__gte=current_time,
            created_at__lt=next_hour
        ).count()
        message_counts.append(message_count)
        
        # Count unique active agents in this hour
        messages = AgentMessage.objects.filter(
            created_at__gte=current_time,
            created_at__lt=next_hour
        ).values_list('sender_id', 'recipient_id')
        
        active_agents = set()
        for sender_id, recipient_id in messages:
            active_agents.add(sender_id)
            active_agents.add(recipient_id)
        
        active_agent_counts.append(len(active_agents))
        
        # Calculate average latency for this hour
        avg_latency = AgentMessage.objects.filter(
            created_at__gte=current_time,
            created_at__lt=next_hour,
            latency_ms__isnull=False
        ).aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
        
        avg_latencies.append(round(avg_latency, 2))
        
        current_time = next_hour
    
    return {
        'labels': hours,
        'message_counts': message_counts,
        'active_agent_counts': active_agent_counts,
        'avg_latencies': avg_latencies,
    }


def _get_top_active_agents(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get top active agents by message count in last 24 hours.
    
    Args:
        limit: Maximum number of agents to return
    
    Returns:
        List of agent dictionaries with activity metrics
    
    Requirements: 7.1
    """
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    
    # Get agents with message counts
    agents = AIAgent.objects.filter(
        is_active=True,
        is_suspended=False
    ).annotate(
        sent_count=Count(
            'sent_messages',
            filter=Q(sent_messages__created_at__gte=twenty_four_hours_ago)
        ),
        received_count=Count(
            'received_messages',
            filter=Q(received_messages__created_at__gte=twenty_four_hours_ago)
        )
    ).order_by('-sent_count')[:limit]
    
    return [
        {
            'id': str(agent.id),
            'name': agent.name,
            'type': agent.agent_type,
            'messages_sent': agent.sent_count,
            'messages_received': agent.received_count,
            'total_messages': agent.sent_count + agent.received_count,
        }
        for agent in agents
    ]

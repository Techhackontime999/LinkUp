"""
Extensions to the InteractionLogger service for additional functionality.
These methods will be added to the InteractionLogger class in services.py.
"""
from typing import Dict, List, Optional, Any
from django.db import models
from django.utils import timezone
from .models import AIAgent, AgentInteraction, ResearchMetric


def log_agent_action(
    agent_id: str,
    action_type: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Log an agent action for research analysis.
    
    Args:
        agent_id: UUID of the agent performing the action
        action_type: Type of action (e.g., 'message_sent', 'profile_updated')
        details: Dictionary containing action details
    
    Returns:
        Dictionary containing:
            - status: 'SUCCESS' or 'FAILED'
            - metric_id: UUID of created metric record
            - error: Error message (on failure)
    
    Requirements: 6.1, 6.2
    """
    try:
        # Get agent
        try:
            agent = AIAgent.objects.get(id=agent_id)
        except AIAgent.DoesNotExist:
            return {
                'status': 'FAILED',
                'error': 'Agent not found'
            }
        
        # Create metric record for the action
        metric = ResearchMetric.objects.create(
            metric_name=f'agent_action_{action_type}',
            metric_type='COUNTER',
            agent=agent,
            value=1.0,
            unit='count',
            dimensions={
                'action_type': action_type,
                'details': details
            },
            timestamp=timezone.now()
        )
        
        return {
            'status': 'SUCCESS',
            'metric_id': str(metric.id)
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger('ai_agents.interaction_logger')
        logger.error(f'Failed to log agent action: {str(e)}')
        
        return {
            'status': 'FAILED',
            'error': str(e)
        }


def query_interactions(
    filters: Optional[Dict[str, Any]] = None,
    time_range: Optional[Dict[str, Any]] = None,
    pagination: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Query interactions with filters and time range.
    
    Args:
        filters: Optional filters:
            - agent_id: Filter by specific agent (either agent_1 or agent_2)
            - interaction_type: Filter by interaction type
            - tags: Filter by tags (list)
            - session_id: Filter by session ID
        time_range: Optional time range:
            - start_time: Start timestamp
            - end_time: End timestamp
        pagination: Optional pagination:
            - page: Page number (default: 1)
            - page_size: Items per page (default: 50)
    
    Returns:
        Dictionary containing:
            - status: 'SUCCESS' or 'FAILED'
            - interactions: List of interaction objects
            - count: Total number of interactions
            - page: Current page number
            - total_pages: Total number of pages
            - error: Error message (on failure)
    
    Requirements: 11.1, 11.2
    """
    try:
        # Start with all interactions
        queryset = AgentInteraction.objects.all()
        
        # Apply filters if provided
        if filters:
            # Filter by agent (either agent_1 or agent_2)
            if 'agent_id' in filters:
                queryset = queryset.filter(
                    models.Q(agent_1_id=filters['agent_id']) | 
                    models.Q(agent_2_id=filters['agent_id'])
                )
            
            # Filter by interaction type
            if 'interaction_type' in filters:
                queryset = queryset.filter(interaction_type=filters['interaction_type'])
            
            # Filter by tags
            if 'tags' in filters:
                for tag in filters['tags']:
                    queryset = queryset.filter(tags__contains=[tag])
            
            # Filter by session ID
            if 'session_id' in filters:
                queryset = queryset.filter(session_id=filters['session_id'])
        
        # Apply time range if provided
        if time_range:
            if 'start_time' in time_range:
                queryset = queryset.filter(started_at__gte=time_range['start_time'])
            
            if 'end_time' in time_range:
                queryset = queryset.filter(started_at__lte=time_range['end_time'])
        
        # Order by start time (newest first)
        queryset = queryset.order_by('-started_at')
        
        # Apply pagination
        page = 1
        page_size = 50
        
        if pagination:
            page = pagination.get('page', 1)
            page_size = pagination.get('page_size', 50)
        
        # Calculate pagination
        total_count = queryset.count()
        total_pages = (total_count + page_size - 1) // page_size
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        # Get paginated results
        interactions_page = queryset[start_index:end_index]
        
        # Build interaction list
        interactions = []
        for interaction in interactions_page:
            interactions.append({
                'id': str(interaction.id),
                'session_id': str(interaction.session_id),
                'agent_1': {
                    'id': str(interaction.agent_1.id),
                    'name': interaction.agent_1.name
                },
                'agent_2': {
                    'id': str(interaction.agent_2.id),
                    'name': interaction.agent_2.name
                },
                'interaction_type': interaction.interaction_type,
                'started_at': interaction.started_at.isoformat(),
                'ended_at': interaction.ended_at.isoformat() if interaction.ended_at else None,
                'message_count': interaction.message_count,
                'total_duration_seconds': interaction.total_duration_seconds,
                'outcome': interaction.outcome,
                'tags': interaction.tags,
                'metrics': interaction.metrics,
                'is_archived': interaction.is_archived
            })
        
        return {
            'status': 'SUCCESS',
            'interactions': interactions,
            'count': len(interactions),
            'page': page,
            'total_pages': total_pages,
            'total_count': total_count
        }
    except Exception as e:
        import logging
        logger = logging.getLogger('ai_agents.interaction_logger')
        logger.error(f'Failed to query interactions: {str(e)}')
        
        return {
            'status': 'FAILED',
            'error': str(e)
        }


# This class will be used to extend InteractionLogger in services.py
class InteractionLogger:
    """Extension methods for InteractionLogger"""
    log_agent_action = staticmethod(log_agent_action)
    query_interactions = staticmethod(query_interactions)

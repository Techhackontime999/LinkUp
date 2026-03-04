"""
Social Platform - Agent Discovery Views

This module provides API endpoints for agent discovery and recommendations.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import DiscoveryService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def discover_agents(request):
    """
    Discover and recommend agents based on similarity.
    
    GET /api/social/agents/discover?limit=50&agent_type=<type>&min_reputation=<score>
    
    Query parameters:
        limit: Maximum number of recommendations (default: 50, max: 50)
        agent_type: Filter by agent type (optional)
        min_reputation: Minimum reputation score (optional)
    
    Returns:
        200: List of recommended agents with similarity scores
        400: Invalid parameters
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        # Get parameters
        try:
            limit = int(request.GET.get('limit', 50))
        except ValueError:
            return JsonResponse({'error': 'Invalid limit'}, status=400)
        
        # Validate limit
        if limit < 1 or limit > 50:
            return JsonResponse({'error': 'Limit must be between 1 and 50'}, status=400)
        
        # Build filters
        filters = {}
        
        if request.GET.get('agent_type'):
            filters['agent_type'] = request.GET.get('agent_type')
        
        if request.GET.get('min_reputation'):
            try:
                filters['min_reputation'] = float(request.GET.get('min_reputation'))
            except ValueError:
                return JsonResponse({'error': 'Invalid min_reputation'}, status=400)
        
        # Discover agents
        recommendations = DiscoveryService.discover_agents(
            agent_id=agent_id,
            filters=filters,
            limit=limit
        )
        
        return JsonResponse({
            'recommendations': recommendations,
            'count': len(recommendations),
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error discovering agents: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

"""
Social Platform - Reputation Views

This module provides API endpoints for reputation management.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import ReputationService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def get_reputation(request, agent_id):
    """
    Get reputation scores for an agent.
    
    GET /api/social/agents/{agent_id}/reputation
    
    Returns:
        200: Reputation scores and metrics
        404: Agent not found
        500: Server error
    """
    try:
        reputation = ReputationService.get_reputation(agent_id)
        
        if reputation:
            return JsonResponse(reputation)
        else:
            return JsonResponse({'error': 'Reputation not found'}, status=404)
            
    except Exception as e:
        logger.error(f"Error getting reputation: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)



@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def calculate_reputation(request, agent_id):
    """
    Trigger reputation calculation for an agent.
    
    POST /api/social/agents/{agent_id}/reputation/calculate
    
    Returns:
        200: Calculated reputation scores
        403: Not authorized
        500: Server error
    """
    try:
        # Only allow agents to calculate their own reputation or admins
        requesting_agent_id = str(request.agent.id)
        if requesting_agent_id != agent_id and not request.agent.is_staff:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        scores = ReputationService.calculate_reputation(agent_id)
        
        return JsonResponse({
            'message': 'Reputation calculated successfully',
            'scores': scores
        })
        
    except Exception as e:
        logger.error(f"Error calculating reputation: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

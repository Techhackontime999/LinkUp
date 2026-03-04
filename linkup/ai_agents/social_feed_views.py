"""
Social Platform - Feed Views

This module provides API endpoints for personalized feed generation.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import FeedService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def get_feed(request):
    """
    Get personalized feed for the authenticated agent.
    
    GET /api/social/agents/feed?page_size=20&cursor=<cursor>
    
    Query parameters:
        page_size: Number of items per page (default: 20, max: 100)
        cursor: Pagination cursor for next page
    
    Returns:
        200: Feed items with relevance scores and pagination cursor
        400: Invalid parameters
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        # Get pagination parameters
        try:
            page_size = int(request.GET.get('page_size', 20))
        except ValueError:
            return JsonResponse({'error': 'Invalid page_size'}, status=400)
        
        # Validate page_size
        if page_size < 1 or page_size > 100:
            return JsonResponse({'error': 'page_size must be between 1 and 100'}, status=400)
        
        cursor = request.GET.get('cursor')
        
        # Generate feed
        result = FeedService.generate_feed(
            agent_id=agent_id,
            page_size=page_size,
            cursor=cursor
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error generating feed: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

"""
Social Platform - Notification Views

This module provides API endpoints for notification management.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .social_middleware import jwt_required
from .social_services import NotificationService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def get_notifications(request):
    """
    Get notifications for the authenticated agent.
    
    GET /api/social/notifications?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number of notifications (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of notifications
        400: Invalid parameters
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        # Get pagination parameters
        try:
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            return JsonResponse({'error': 'Invalid limit or offset'}, status=400)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return JsonResponse({'error': 'Limit must be between 1 and 100'}, status=400)
        
        if offset < 0:
            return JsonResponse({'error': 'Offset must be non-negative'}, status=400)
        
        # Get notifications
        notifications = NotificationService.get_notifications(
            agent_id=agent_id,
            unread_only=False,
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'notifications': notifications,
            'count': len(notifications),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def get_unread_notifications(request):
    """
    Get unread notifications for the authenticated agent.
    
    GET /api/social/notifications/unread?limit=50&offset=0
    
    Query parameters:
        limit: Maximum number of notifications (default: 50, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        200: List of unread notifications with count
        400: Invalid parameters
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        # Get pagination parameters
        try:
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            return JsonResponse({'error': 'Invalid limit or offset'}, status=400)
        
        # Validate limit
        if limit < 1 or limit > 100:
            return JsonResponse({'error': 'Limit must be between 1 and 100'}, status=400)
        
        if offset < 0:
            return JsonResponse({'error': 'Offset must be non-negative'}, status=400)
        
        # Get unread notifications
        notifications = NotificationService.get_notifications(
            agent_id=agent_id,
            unread_only=True,
            limit=limit,
            offset=offset
        )
        
        # Get total unread count
        unread_count = NotificationService.get_unread_count(agent_id)
        
        return JsonResponse({
            'notifications': notifications,
            'count': len(notifications),
            'unread_count': unread_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error getting unread notifications: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
@jwt_required
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read.
    
    PUT /api/social/notifications/{notification_id}/read
    
    Returns:
        200: Notification marked as read
        403: Not authorized
        404: Notification not found
        500: Server error
    """
    try:
        agent_id = str(request.agent.id)
        
        result = NotificationService.mark_as_read(
            notification_id=str(notification_id),
            agent_id=agent_id
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            status_code = 404 if 'not found' in result.get('error', '').lower() else 403
            return JsonResponse(result, status=status_code)
            
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

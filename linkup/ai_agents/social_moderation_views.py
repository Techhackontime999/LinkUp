"""
Content Moderation API Views for AI Agent Social Platform.

Provides REST API endpoints for content moderation including:
- Flagging content
- Viewing moderation queue
- Removing content
- Suspending/unsuspending agents
- Viewing audit logs
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .social_moderation import ModerationService
from .social_middleware import jwt_required, admin_required


@api_view(['POST'])
@jwt_required
def flag_post(request, post_id):
    """
    Flag a post for moderation review.
    
    POST /api/social/admin/posts/{post_id}/flag
    
    Request body:
    {
        "reason": "spam|harassment|inappropriate|other",
        "details": "Optional additional details"
    }
    """
    reason = request.data.get('reason')
    details = request.data.get('details')
    
    if not reason:
        return Response(
            {'error': 'Reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = ModerationService.flag_content(
        content_type='post',
        content_id=str(post_id),
        flagger_id=str(request.agent.id),
        reason=reason,
        details=details
    )
    
    if result['success']:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Failed to flag post')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@jwt_required
def flag_comment(request, comment_id):
    """
    Flag a comment for moderation review.
    
    POST /api/social/admin/comments/{comment_id}/flag
    
    Request body:
    {
        "reason": "spam|harassment|inappropriate|other",
        "details": "Optional additional details"
    }
    """
    reason = request.data.get('reason')
    details = request.data.get('details')
    
    if not reason:
        return Response(
            {'error': 'Reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = ModerationService.flag_content(
        content_type='comment',
        content_id=str(comment_id),
        flagger_id=str(request.agent.id),
        reason=reason,
        details=details
    )
    
    if result['success']:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Failed to flag comment')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@jwt_required
@admin_required
def get_moderation_queue(request):
    """
    Get flagged content for moderation review.
    
    GET /api/social/admin/moderation/queue
    
    Query parameters:
    - content_type: Filter by 'post' or 'comment' (optional)
    - limit: Maximum items to return (default: 50, max: 100)
    - offset: Pagination offset (default: 0)
    """
    content_type = request.GET.get('content_type')
    limit = min(int(request.GET.get('limit', 50)), 100)
    offset = int(request.GET.get('offset', 0))
    
    queue = ModerationService.get_moderation_queue(
        content_type=content_type,
        limit=limit,
        offset=offset
    )
    
    return Response({
        'queue': queue,
        'count': len(queue),
        'limit': limit,
        'offset': offset
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@jwt_required
@admin_required
def remove_post(request, post_id):
    """
    Remove a post (soft delete).
    
    DELETE /api/social/admin/posts/{post_id}
    
    Request body:
    {
        "reason": "Reason for removal"
    }
    """
    reason = request.data.get('reason')
    
    if not reason:
        return Response(
            {'error': 'Reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = ModerationService.remove_content(
        content_type='post',
        content_id=str(post_id),
        moderator_id=str(request.agent.id),
        reason=reason
    )
    
    if result['success']:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Failed to remove post')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@jwt_required
@admin_required
def remove_comment(request, comment_id):
    """
    Remove a comment (soft delete).
    
    DELETE /api/social/admin/comments/{comment_id}
    
    Request body:
    {
        "reason": "Reason for removal"
    }
    """
    reason = request.data.get('reason')
    
    if not reason:
        return Response(
            {'error': 'Reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = ModerationService.remove_content(
        content_type='comment',
        content_id=str(comment_id),
        moderator_id=str(request.agent.id),
        reason=reason
    )
    
    if result['success']:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Failed to remove comment')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@jwt_required
@admin_required
def suspend_agent(request, agent_id):
    """
    Suspend an agent.
    
    POST /api/social/admin/agents/{agent_id}/suspend
    
    Request body:
    {
        "reason": "Reason for suspension",
        "duration_days": 7  // Optional, null for permanent
    }
    """
    reason = request.data.get('reason')
    duration_days = request.data.get('duration_days')
    
    if not reason:
        return Response(
            {'error': 'Reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = ModerationService.suspend_agent(
        agent_id=str(agent_id),
        moderator_id=str(request.agent.id),
        reason=reason,
        duration_days=duration_days
    )
    
    if result['success']:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Failed to suspend agent')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@jwt_required
@admin_required
def unsuspend_agent(request, agent_id):
    """
    Unsuspend an agent.
    
    POST /api/social/admin/agents/{agent_id}/unsuspend
    
    Request body:
    {
        "reason": "Reason for unsuspension"
    }
    """
    reason = request.data.get('reason')
    
    if not reason:
        return Response(
            {'error': 'Reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = ModerationService.unsuspend_agent(
        agent_id=str(agent_id),
        moderator_id=str(request.agent.id),
        reason=reason
    )
    
    if result['success']:
        return Response(result, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Failed to unsuspend agent')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@jwt_required
@admin_required
def get_moderation_logs(request):
    """
    Get moderation audit logs.
    
    GET /api/social/admin/moderation/logs
    
    Query parameters:
    - target_type: Filter by 'post', 'comment', or 'agent' (optional)
    - target_id: Filter by specific target ID (optional)
    - limit: Maximum logs to return (default: 100, max: 500)
    """
    target_type = request.GET.get('target_type')
    target_id = request.GET.get('target_id')
    limit = min(int(request.GET.get('limit', 100)), 500)
    
    logs = ModerationService.get_moderation_logs(
        target_type=target_type,
        target_id=target_id,
        limit=limit
    )
    
    return Response({
        'logs': logs,
        'count': len(logs)
    }, status=status.HTTP_200_OK)

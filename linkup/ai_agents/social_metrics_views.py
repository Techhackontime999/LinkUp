"""
Metrics Consistency API Views for AI Agent Social Platform.

Provides REST API endpoints for:
- Metrics reconciliation
- Consistency verification
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .social_metrics_consistency import MetricsReconciliationService
from .social_middleware import jwt_required, admin_required


@api_view(['POST'])
@jwt_required
@admin_required
def reconcile_post_metrics(request, post_id):
    """
    Reconcile metrics for a specific post.
    
    POST /api/social/metrics/posts/{post_id}/reconcile
    """
    result = MetricsReconciliationService.reconcile_post_metrics(str(post_id))
    
    if 'error' in result:
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@jwt_required
@admin_required
def reconcile_profile_metrics(request, agent_id):
    """
    Reconcile metrics for a specific agent profile.
    
    POST /api/social/metrics/profiles/{agent_id}/reconcile
    """
    result = MetricsReconciliationService.reconcile_profile_metrics(str(agent_id))
    
    if 'error' in result:
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@jwt_required
@admin_required
def reconcile_all_posts(request):
    """
    Reconcile metrics for all posts.
    
    POST /api/social/metrics/posts/reconcile-all
    
    Query parameters:
    - limit: Maximum posts to reconcile (default: 100, max: 1000)
    """
    limit = min(int(request.GET.get('limit', 100)), 1000)
    
    result = MetricsReconciliationService.reconcile_all_posts(limit=limit)
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@jwt_required
@admin_required
def reconcile_all_profiles(request):
    """
    Reconcile metrics for all profiles.
    
    POST /api/social/metrics/profiles/reconcile-all
    
    Query parameters:
    - limit: Maximum profiles to reconcile (default: 100, max: 1000)
    """
    limit = min(int(request.GET.get('limit', 100)), 1000)
    
    result = MetricsReconciliationService.reconcile_all_profiles(limit=limit)
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@jwt_required
@admin_required
def run_full_reconciliation(request):
    """
    Run full reconciliation for all posts and profiles.
    
    POST /api/social/metrics/reconcile-all
    
    This is a heavy operation and should be run during off-peak hours.
    """
    result = MetricsReconciliationService.run_full_reconciliation()
    
    return Response(result, status=status.HTTP_200_OK)

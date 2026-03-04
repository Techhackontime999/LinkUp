"""
Analytics and Monitoring API Views for AI Agent Social Platform.

Provides REST API endpoints for:
- Metrics export (Prometheus format)
- Platform analytics
- Error tracking
- Alert management
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from .social_analytics import (
    MetricsCollector, ErrorTracker, AnalyticsService, AlertManager
)
from .social_middleware import jwt_required, admin_required


@api_view(['GET'])
def metrics_export(request):
    """
    Export metrics in Prometheus format.
    
    GET /api/social/metrics
    
    Returns metrics in Prometheus text format for scraping.
    """
    metrics_text = MetricsCollector.export_prometheus_metrics()
    return HttpResponse(metrics_text, content_type='text/plain')


@api_view(['GET'])
@jwt_required
@admin_required
def platform_metrics(request):
    """
    Get platform-wide metrics.
    
    GET /api/social/analytics/metrics
    """
    api_metrics = MetricsCollector.collect_api_metrics()
    platform_metrics = MetricsCollector.collect_platform_metrics()
    
    return Response({
        'api_metrics': api_metrics,
        'platform_metrics': platform_metrics,
        'timestamp': request.META.get('HTTP_DATE')
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_required
@admin_required
def recent_errors(request):
    """
    Get recent errors.
    
    GET /api/social/analytics/errors
    
    Query parameters:
    - limit: Maximum errors to return (default: 50, max: 100)
    """
    limit = min(int(request.GET.get('limit', 50)), 100)
    
    errors = ErrorTracker.get_recent_errors(limit=limit)
    error_counts = ErrorTracker.get_error_counts()
    
    return Response({
        'recent_errors': errors,
        'error_counts': error_counts,
        'count': len(errors)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_required
def agent_activity_report(request, agent_id):
    """
    Get activity report for a specific agent.
    
    GET /api/social/analytics/agents/{agent_id}/activity
    
    Query parameters:
    - days: Number of days to analyze (default: 30, max: 365)
    """
    days = min(int(request.GET.get('days', 30)), 365)
    
    # Check if requesting own data or is admin
    if str(request.agent.id) != agent_id and not request.agent.is_staff:
        return Response({
            'error': 'Permission denied',
            'detail': 'You can only view your own activity report'
        }, status=status.HTTP_403_FORBIDDEN)
    
    metrics = AnalyticsService.get_agent_activity_metrics(agent_id, days=days)
    
    if 'error' in metrics:
        return Response(metrics, status=status.HTTP_404_NOT_FOUND)
    
    return Response(metrics, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_required
def platform_summary(request):
    """
    Get platform summary statistics.
    
    GET /api/social/analytics/summary
    
    Query parameters:
    - days: Number of days to analyze (default: 7, max: 90)
    """
    days = min(int(request.GET.get('days', 7)), 90)
    
    summary = AnalyticsService.get_platform_summary(days=days)
    
    return Response(summary, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_required
def trending_content(request):
    """
    Get trending content.
    
    GET /api/social/analytics/trending
    
    Query parameters:
    - limit: Maximum posts to return (default: 10, max: 50)
    """
    limit = min(int(request.GET.get('limit', 10)), 50)
    
    trending = AnalyticsService.get_trending_content(limit=limit)
    
    return Response({
        'trending_posts': trending,
        'count': len(trending)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_required
@admin_required
def check_thresholds(request):
    """
    Check alert thresholds and return any violations.
    
    GET /api/social/analytics/alerts/check
    """
    alerts = AlertManager.check_thresholds()
    
    return Response({
        'alerts': alerts,
        'count': len(alerts),
        'has_alerts': len(alerts) > 0
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_required
@admin_required
def get_alerts(request):
    """
    Get currently active alerts.
    
    GET /api/social/analytics/alerts
    """
    alerts = AlertManager.get_active_alerts()
    
    return Response({
        'alerts': alerts,
        'count': len(alerts)
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@jwt_required
@admin_required
def acknowledge_alert(request, alert_timestamp):
    """
    Acknowledge an alert.
    
    POST /api/social/analytics/alerts/{alert_timestamp}/acknowledge
    """
    success = AlertManager.acknowledge_alert(alert_timestamp)
    
    if success:
        return Response({
            'success': True,
            'message': 'Alert acknowledged'
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Alert not found'
        }, status=status.HTTP_404_NOT_FOUND)

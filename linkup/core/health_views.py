"""
Health check views for monitoring and deployment orchestration.
"""

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Basic health check endpoint.
    Returns 200 OK when the application is running.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'linkup'
    }, status=200)


def health_check_db(request):
    """
    Database connectivity health check.
    Verifies that the database connection is working.
    """
    try:
        connection.ensure_connection()
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        }, status=200)
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': 'Database connection failed'
        }, status=503)


def health_check_redis(request):
    """
    Redis connectivity health check.
    Verifies that Redis/cache connection is working.
    """
    try:
        # Try to set and get a test value
        cache.set('health_check', 'ok', 10)
        value = cache.get('health_check')
        
        if value == 'ok':
            return JsonResponse({
                'status': 'healthy',
                'redis': 'connected'
            }, status=200)
        else:
            return JsonResponse({
                'status': 'unhealthy',
                'redis': 'disconnected',
                'error': 'Cache verification failed'
            }, status=503)
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'redis': 'disconnected',
            'error': 'Redis connection failed'
        }, status=503)


def readiness_check(request):
    """
    Readiness probe for deployment orchestration.
    Checks all critical dependencies (database and Redis).
    Returns 200 only when all dependencies are ready.
    """
    checks = {
        'database': False,
        'redis': False,
    }
    errors = []
    
    # Check database
    try:
        connection.ensure_connection()
        checks['database'] = True
    except Exception as e:
        logger.error(f"Readiness check - Database failed: {str(e)}")
        errors.append('database')
    
    # Check Redis/cache
    try:
        cache.set('readiness_check', 'ok', 10)
        if cache.get('readiness_check') == 'ok':
            checks['redis'] = True
        else:
            errors.append('redis')
    except Exception as e:
        logger.error(f"Readiness check - Redis failed: {str(e)}")
        errors.append('redis')
    
    # Determine overall status
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503
    
    response_data = {
        'status': 'ready' if all_ready else 'not_ready',
        'checks': checks
    }
    
    if errors:
        response_data['failed_checks'] = errors
    
    return JsonResponse(response_data, status=status_code)

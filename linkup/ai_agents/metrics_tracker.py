"""
System metrics tracking service for AI Agents platform.

This module provides comprehensive system health monitoring including:
- Active agent tracking
- Message throughput monitoring
- Message delivery latency tracking
- WebSocket connection counting
- API request rate tracking per endpoint
- Threshold-based alerting

Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.7
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Avg, Count
from django.conf import settings
from .models import AIAgent, AgentMessage

logger = logging.getLogger('ai_agents.metrics')


class SystemMetricsTracker:
    """
    Service for tracking and monitoring system health metrics.
    
    This service provides:
    - Real-time metric collection
    - Metric aggregation and storage
    - Threshold monitoring and alerting
    - Historical metric tracking
    """
    
    # Cache keys for metrics
    CACHE_KEY_WEBSOCKET_CONNECTIONS = 'metrics:websocket_connections'
    CACHE_KEY_API_REQUEST_RATE = 'metrics:api_request_rate'
    CACHE_KEY_MESSAGES_PER_MINUTE = 'metrics:messages_per_minute'
    CACHE_KEY_ACTIVE_AGENTS = 'metrics:active_agents'
    CACHE_KEY_AVG_LATENCY = 'metrics:avg_latency'
    
    # Cache TTL (time to live) in seconds
    CACHE_TTL_SHORT = 60  # 1 minute
    CACHE_TTL_MEDIUM = 300  # 5 minutes
    CACHE_TTL_LONG = 3600  # 1 hour
    
    @classmethod
    def get_thresholds(cls) -> Dict[str, Any]:
        """
        Get threshold configuration from Django settings.
        
        Returns:
            Dictionary of threshold values
        
        Requirements: 20.7
        """
        # Get thresholds from settings, fall back to defaults if not configured
        return getattr(settings, 'AI_AGENT_HEALTH_THRESHOLDS', {
            'max_active_agents': 10000,
            'max_messages_per_minute': 10000,
            'max_avg_latency_ms': 5000,
            'max_websocket_connections': 10000,
            'max_api_requests_per_minute': 50000
        })
    
    @classmethod
    def track_websocket_connection(cls, agent_id: str, connected: bool) -> Dict[str, Any]:
        """
        Track WebSocket connection state changes.
        
        Args:
            agent_id: UUID of the agent
            connected: True if connecting, False if disconnecting
        
        Returns:
            Dictionary with tracking result
        
        Requirements: 20.4
        """
        try:
            # Get current connection count
            current_count = cache.get(cls.CACHE_KEY_WEBSOCKET_CONNECTIONS, 0)
            
            # Update count
            if connected:
                new_count = current_count + 1
            else:
                new_count = max(0, current_count - 1)
            
            # Store updated count
            cache.set(cls.CACHE_KEY_WEBSOCKET_CONNECTIONS, new_count, cls.CACHE_TTL_MEDIUM)
            
            # Also track individual agent connection status
            agent_key = f'metrics:websocket:agent:{agent_id}'
            if connected:
                cache.set(agent_key, True, cls.CACHE_TTL_MEDIUM)
            else:
                cache.delete(agent_key)
            
            logger.debug(
                f"WebSocket connection tracked: agent={agent_id}, "
                f"connected={connected}, total_connections={new_count}"
            )
            
            return {
                'status': 'SUCCESS',
                'connection_count': new_count,
                'agent_id': agent_id,
                'connected': connected
            }
            
        except Exception as e:
            logger.error(f"Error tracking WebSocket connection: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @classmethod
    def track_api_request(cls, endpoint: str, method: str, status_code: int) -> Dict[str, Any]:
        """
        Track API request for rate monitoring.
        
        Args:
            endpoint: API endpoint path (e.g., '/api/messages')
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP response status code
        
        Returns:
            Dictionary with tracking result
        
        Requirements: 20.5
        """
        try:
            # Get current minute window
            current_minute = timezone.now().replace(second=0, microsecond=0)
            minute_key = current_minute.strftime('%Y%m%d%H%M')
            
            # Get or initialize request rate data
            rate_data = cache.get(cls.CACHE_KEY_API_REQUEST_RATE, {})
            
            # Normalize endpoint (remove IDs and query params)
            normalized_endpoint = cls._normalize_endpoint(endpoint)
            
            # Create key for this endpoint
            endpoint_key = f"{method}:{normalized_endpoint}"
            
            # Initialize endpoint data if not exists
            if endpoint_key not in rate_data:
                rate_data[endpoint_key] = {
                    'total': 0,
                    'success': 0,
                    'error': 0,
                    'last_minute': minute_key,
                    'per_minute': 0
                }
            
            # Check if we're in a new minute window
            if rate_data[endpoint_key]['last_minute'] != minute_key:
                # Reset per-minute counter for new window
                rate_data[endpoint_key]['per_minute'] = 0
                rate_data[endpoint_key]['last_minute'] = minute_key
            
            # Increment counters
            rate_data[endpoint_key]['total'] += 1
            rate_data[endpoint_key]['per_minute'] += 1
            
            if 200 <= status_code < 400:
                rate_data[endpoint_key]['success'] += 1
            else:
                rate_data[endpoint_key]['error'] += 1
            
            # Store updated rate data
            cache.set(cls.CACHE_KEY_API_REQUEST_RATE, rate_data, cls.CACHE_TTL_SHORT)
            
            logger.debug(
                f"API request tracked: {endpoint_key}, "
                f"status={status_code}, per_minute={rate_data[endpoint_key]['per_minute']}"
            )
            
            return {
                'status': 'SUCCESS',
                'endpoint': endpoint_key,
                'per_minute': rate_data[endpoint_key]['per_minute']
            }
            
        except Exception as e:
            logger.error(f"Error tracking API request: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @classmethod
    def get_all_metrics(cls) -> Dict[str, Any]:
        """
        Get all current system metrics.
        
        Returns:
            Dictionary containing all system health metrics
        
        Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6
        """
        try:
            # Get total active agents
            total_active_agents = AIAgent.objects.filter(
                is_active=True,
                is_suspended=False
            ).count()
            
            # Get messages per minute (last minute)
            one_minute_ago = timezone.now() - timedelta(minutes=1)
            messages_last_minute = AgentMessage.objects.filter(
                created_at__gte=one_minute_ago
            ).count()
            
            # Get average message latency (last hour)
            one_hour_ago = timezone.now() - timedelta(hours=1)
            avg_latency = AgentMessage.objects.filter(
                latency_ms__isnull=False,
                created_at__gte=one_hour_ago
            ).aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
            
            # Get WebSocket connection count
            websocket_connections = cache.get(cls.CACHE_KEY_WEBSOCKET_CONNECTIONS, 0)
            
            # Get API request rate
            api_request_rate = cache.get(cls.CACHE_KEY_API_REQUEST_RATE, {})
            
            # Calculate total API requests per minute
            total_api_requests = sum(
                endpoint_data.get('per_minute', 0)
                for endpoint_data in api_request_rate.values()
            )
            
            metrics = {
                'total_active_agents': total_active_agents,
                'messages_per_minute': float(messages_last_minute),
                'average_message_latency_ms': float(avg_latency),
                'websocket_connections': websocket_connections,
                'api_request_rate': api_request_rate,
                'total_api_requests_per_minute': total_api_requests,
                'timestamp': timezone.now().isoformat()
            }
            
            return {
                'status': 'SUCCESS',
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'error': str(e),
                'metrics': {}
            }
    
    @classmethod
    def check_thresholds(cls, metrics: Optional[Dict[str, Any]] = None, 
                        custom_thresholds: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Check metrics against defined thresholds and identify violations.
        
        Args:
            metrics: Optional metrics dictionary (will fetch if not provided)
            custom_thresholds: Optional custom threshold values
        
        Returns:
            Dictionary with threshold check results and violations
        
        Requirements: 20.7
        """
        try:
            # Get metrics if not provided
            if metrics is None:
                result = cls.get_all_metrics()
                if result['status'] != 'SUCCESS':
                    return result
                metrics = result['metrics']
            
            # Use custom thresholds or get from settings
            thresholds = custom_thresholds or cls.get_thresholds()
            
            # Check each metric against thresholds
            violations = []
            
            # Check active agents
            if metrics['total_active_agents'] > thresholds.get('max_active_agents', float('inf')):
                violations.append({
                    'metric': 'total_active_agents',
                    'current_value': metrics['total_active_agents'],
                    'threshold': thresholds['max_active_agents'],
                    'severity': 'warning',
                    'message': f"Active agents ({metrics['total_active_agents']}) exceeds threshold ({thresholds['max_active_agents']})"
                })
            
            # Check messages per minute
            if metrics['messages_per_minute'] > thresholds.get('max_messages_per_minute', float('inf')):
                violations.append({
                    'metric': 'messages_per_minute',
                    'current_value': metrics['messages_per_minute'],
                    'threshold': thresholds['max_messages_per_minute'],
                    'severity': 'warning',
                    'message': f"Messages per minute ({metrics['messages_per_minute']}) exceeds threshold ({thresholds['max_messages_per_minute']})"
                })
            
            # Check average latency
            if metrics['average_message_latency_ms'] > thresholds.get('max_avg_latency_ms', float('inf')):
                violations.append({
                    'metric': 'average_message_latency_ms',
                    'current_value': metrics['average_message_latency_ms'],
                    'threshold': thresholds['max_avg_latency_ms'],
                    'severity': 'critical',
                    'message': f"Average latency ({metrics['average_message_latency_ms']}ms) exceeds threshold ({thresholds['max_avg_latency_ms']}ms)"
                })
            
            # Check WebSocket connections
            if metrics['websocket_connections'] > thresholds.get('max_websocket_connections', float('inf')):
                violations.append({
                    'metric': 'websocket_connections',
                    'current_value': metrics['websocket_connections'],
                    'threshold': thresholds['max_websocket_connections'],
                    'severity': 'warning',
                    'message': f"WebSocket connections ({metrics['websocket_connections']}) exceeds threshold ({thresholds['max_websocket_connections']})"
                })
            
            # Check API request rate
            if metrics['total_api_requests_per_minute'] > thresholds.get('max_api_requests_per_minute', float('inf')):
                violations.append({
                    'metric': 'total_api_requests_per_minute',
                    'current_value': metrics['total_api_requests_per_minute'],
                    'threshold': thresholds['max_api_requests_per_minute'],
                    'severity': 'critical',
                    'message': f"API requests per minute ({metrics['total_api_requests_per_minute']}) exceeds threshold ({thresholds['max_api_requests_per_minute']})"
                })
            
            # Trigger alerts if violations found
            if violations:
                cls._trigger_alerts(violations)
            
            return {
                'status': 'SUCCESS',
                'has_violations': len(violations) > 0,
                'violation_count': len(violations),
                'violations': violations,
                'metrics': metrics,
                'thresholds': thresholds,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking thresholds: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @classmethod
    def trigger_alert(cls, violations: list) -> Dict[str, Any]:
        """
        Trigger alerts for threshold violations.
        
        This method is deprecated. Use _trigger_alerts instead.
        
        Args:
            violations: List of violation dictionaries
        
        Returns:
            Dictionary with alert result
        
        Requirements: 20.7
        """
        return cls._trigger_alerts(violations)
    
    @classmethod
    def _trigger_alerts(cls, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Internal method to trigger alerts for threshold violations.
        
        Args:
            violations: List of violation dictionaries
        
        Returns:
            Dictionary with alert result
        
        Requirements: 20.7
        """
        try:
            if not violations:
                return {
                    'status': 'SUCCESS',
                    'alerts_sent': 0,
                    'message': 'No violations to alert'
                }
            
            # Import alerting service
            from .alerting_service import AlertingService
            
            # Trigger alerts through the alerting service
            result = AlertingService.trigger_alerts(violations)
            
            # Store alert in cache for admin dashboard
            alert_key = f"metrics:alerts:{timezone.now().strftime('%Y%m%d%H%M')}"
            cache.set(alert_key, {
                'violations': violations,
                'timestamp': timezone.now().isoformat(),
                'acknowledged': False,
                'alert_result': result
            }, cls.CACHE_TTL_LONG)
            
            return result
            
        except Exception as e:
            logger.error(f"Error triggering alerts: {str(e)}", exc_info=True)
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @classmethod
    def _normalize_endpoint(cls, endpoint: str) -> str:
        """
        Normalize endpoint path by removing IDs and query parameters.
        
        Args:
            endpoint: Raw endpoint path
        
        Returns:
            Normalized endpoint path
        """
        import re
        
        # Remove query parameters
        endpoint = endpoint.split('?')[0]
        
        # Replace UUIDs with placeholder
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        endpoint = re.sub(uuid_pattern, '{id}', endpoint, flags=re.IGNORECASE)
        
        # Replace numeric IDs with placeholder
        endpoint = re.sub(r'/\d+/', '/{id}/', endpoint)
        endpoint = re.sub(r'/\d+$', '/{id}', endpoint)
        
        return endpoint

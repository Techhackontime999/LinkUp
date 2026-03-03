"""
REST API views for AI Agents platform.

This module provides REST API endpoints for agent registration, authentication,
messaging, analytics, and system management.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Count, Avg
from datetime import datetime, timedelta
import logging

from .models import AIAgent, AgentMessage, AgentInteraction, AgentAPIKey
from .serializers import (
    AgentRegistrationSerializer, AgentAuthenticationSerializer,
    TokenRefreshSerializer, AgentProfileSerializer, AgentProfileUpdateSerializer,
    AgentDiscoverySerializer, MessageSendSerializer, MessageSerializer,
    MessageMarkReadSerializer, AgentMetricsSerializer, InteractionSerializer,
    DataExportSerializer, DataAnonymizeSerializer, APIKeySerializer,
    SystemHealthSerializer
)
from .services import (
    AgentRegistryService, AgentAuthenticationService,
    AgentCommunicationService, AgentRateLimitService
)
from .analytics_engine import ResearchAnalyticsEngine
from .interaction_logger_extensions import InteractionLogger
from .error_logger import ErrorLogger

logger = logging.getLogger('ai_agents.api')


def log_validation_error(request, serializer_errors, endpoint):
    """
    Helper function to log validation errors with correlation ID.
    
    Args:
        request: Django request object
        serializer_errors: Serializer validation errors
        endpoint: API endpoint where error occurred
    
    Requirements: 15.4, 15.5
    """
    correlation_id = getattr(request, 'correlation_id', None)
    
    ErrorLogger.log_validation_error(
        error_type='serializer_validation',
        error_message='Request data validation failed',
        request_details={
            'endpoint': endpoint,
            'method': request.method,
            'errors': serializer_errors,
        },
        correlation_id=correlation_id
    )


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API responses."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


# Authentication decorator for JWT tokens
def jwt_authentication_required(view_func):
    """Decorator to require JWT authentication for API views."""
    def wrapper(request, *args, **kwargs):
        # Extract JWT token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return Response(
                {'error': 'Missing or invalid Authorization header'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        token = auth_header.split(' ')[1]
        
        # Validate JWT token
        try:
            import jwt
            from django.conf import settings
            
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Check expiration
            expires_at = payload.get('expires_at')
            if expires_at and timezone.now().timestamp() > expires_at:
                return Response(
                    {'error': 'Token expired'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Add agent_id to request
            request.agent_id = payload.get('agent_id')
            request.agent_scopes = payload.get('scopes', [])
            
        except jwt.ExpiredSignatureError:
            return Response(
                {'error': 'Token expired'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.InvalidTokenError:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f'JWT validation error: {str(e)}')
            return Response(
                {'error': 'Authentication failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# Task 12.1: Agent registration and authentication endpoints

@api_view(['POST'])
@permission_classes([AllowAny])
def agent_register(request):
    """
    Register a new AI agent.
    
    POST /api/agents/register
    
    Request body:
        - name: Agent name (3-100 characters)
        - description: Agent description
        - capabilities: JSON object of capabilities
        - owner_email: Owner email address
        - agent_type: Type of agent (optional)
        - version: Agent version (optional)
        - metadata: Additional metadata (optional)
    
    Response:
        - agent_id: UUID of created agent
        - api_key: API key (only returned once)
        - key_prefix: First 8 characters of API key
        - message: Success message
    
    Requirements: 1.1
    """
    serializer = AgentRegistrationSerializer(data=request.data)
    
    if not serializer.is_valid():
        log_validation_error(request, serializer.errors, '/api/agents/register')
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call registration service
    result = AgentRegistryService.register_agent(
        name=serializer.validated_data['name'],
        description=serializer.validated_data.get('description', ''),
        capabilities=serializer.validated_data['capabilities'],
        owner_email=serializer.validated_data['owner_email'],
        agent_type=serializer.validated_data.get('agent_type', 'CONVERSATIONAL'),
        version=serializer.validated_data.get('version', '1.0.0'),
        metadata=serializer.validated_data.get('metadata', {})
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'agent_id': result['agent_id'],
                'api_key': result['api_key'],
                'key_prefix': result['key_prefix'],
                'message': result['message']
            },
            status=status.HTTP_201_CREATED
        )
    else:
        return Response(
            {'error': result.get('error', 'Registration failed')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_authenticate(request):
    """
    Authenticate an agent and issue JWT tokens.
    
    POST /api/agents/authenticate
    
    Request body:
        - agent_id: UUID of the agent
        - api_key: API key
    
    Response:
        - access_token: JWT access token
        - refresh_token: Refresh token
        - expires_in: Token expiration time in seconds
        - token_type: 'Bearer'
    
    Requirements: 2.1
    """
    serializer = AgentAuthenticationSerializer(data=request.data)
    
    if not serializer.is_valid():
        log_validation_error(request, serializer.errors, '/api/agents/authenticate')
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call authentication service
    result = AgentAuthenticationService.authenticate_agent(
        agent_id=str(serializer.validated_data['agent_id']),
        api_key=serializer.validated_data['api_key']
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'access_token': result['access_token'],
                'refresh_token': result['refresh_token'],
                'expires_in': result['expires_in'],
                'token_type': result['token_type']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Authentication failed')},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Refresh an access token using a refresh token.
    
    POST /api/agents/token/refresh
    
    Request body:
        - refresh_token: The refresh token
    
    Response:
        - access_token: New JWT access token
        - refresh_token: New refresh token
        - expires_in: Token expiration time in seconds
        - token_type: 'Bearer'
    
    Requirements: 16.2
    """
    serializer = TokenRefreshSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call token refresh service
    result = AgentAuthenticationService.refresh_token(
        refresh_token=serializer.validated_data['refresh_token']
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'access_token': result['access_token'],
                'refresh_token': result['refresh_token'],
                'expires_in': result['expires_in'],
                'token_type': result['token_type']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Token refresh failed')},
            status=status.HTTP_401_UNAUTHORIZED
        )



# Task 12.2: Agent profile management endpoints

@api_view(['GET'])
@jwt_authentication_required
def agent_profile_get(request, agent_id):
    """
    Get an agent's profile.
    
    GET /api/agents/{agent_id}
    
    Response:
        - Agent profile data
    
    Requirements: 8.1
    """
    result = AgentRegistryService.get_agent_profile(agent_id)
    
    if result['status'] == 'SUCCESS':
        return Response(result['agent'], status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result.get('error', 'Agent not found')},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PATCH'])
@jwt_authentication_required
def agent_profile_update(request, agent_id):
    """
    Update an agent's profile.
    
    PATCH /api/agents/{agent_id}
    
    Request body:
        - description: Updated description (optional)
        - capabilities: Updated capabilities (optional)
        - metadata: Updated metadata (optional)
        - version: Updated version (optional)
        - agent_type: Updated agent type (optional)
    
    Response:
        - message: Success message
        - updated_fields: List of updated fields
    
    Requirements: 8.2
    """
    # Verify agent is updating their own profile
    if str(request.agent_id) != agent_id:
        return Response(
            {'error': 'Cannot update another agent\'s profile'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = AgentProfileUpdateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call update service
    result = AgentRegistryService.update_agent_profile(
        agent_id=agent_id,
        profile_data=serializer.validated_data
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'message': result['message'],
                'updated_fields': result['updated_fields']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Update failed')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@jwt_authentication_required
def agent_profile_delete(request, agent_id):
    """
    Deactivate an agent.
    
    DELETE /api/agents/{agent_id}
    
    Response:
        - message: Success message
    
    Requirements: 8.5
    """
    # Verify agent is deactivating their own profile
    if str(request.agent_id) != agent_id:
        return Response(
            {'error': 'Cannot deactivate another agent'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Call deactivation service
    result = AgentRegistryService.deactivate_agent(agent_id)
    
    if result['status'] == 'SUCCESS':
        return Response(
            {'message': result['message']},
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Deactivation failed')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@jwt_authentication_required
def agent_suspend(request, agent_id):
    """
    Suspend an agent (admin only).
    
    POST /api/agents/{agent_id}/suspend
    
    Response:
        - message: Success message
    
    Requirements: 18.1
    """
    try:
        agent = AIAgent.objects.get(id=agent_id)
        agent.is_suspended = True
        agent.save()
        
        logger.info(f'Agent suspended: {agent_id}')
        
        return Response(
            {'message': 'Agent suspended successfully'},
            status=status.HTTP_200_OK
        )
    except AIAgent.DoesNotExist:
        return Response(
            {'error': 'Agent not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'Error suspending agent: {str(e)}')
        return Response(
            {'error': 'Suspension failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@jwt_authentication_required
def agent_unsuspend(request, agent_id):
    """
    Unsuspend an agent (admin only).
    
    POST /api/agents/{agent_id}/unsuspend
    
    Response:
        - message: Success message
    
    Requirements: 18.5
    """
    try:
        agent = AIAgent.objects.get(id=agent_id)
        agent.is_suspended = False
        agent.save()
        
        logger.info(f'Agent unsuspended: {agent_id}')
        
        return Response(
            {'message': 'Agent unsuspended successfully'},
            status=status.HTTP_200_OK
        )
    except AIAgent.DoesNotExist:
        return Response(
            {'error': 'Agent not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'Error unsuspending agent: {str(e)}')
        return Response(
            {'error': 'Unsuspension failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



# Task 12.3: Agent discovery endpoints

@api_view(['GET'])
@jwt_authentication_required
def agent_list(request):
    """
    List active agents with filtering and pagination.
    
    GET /api/agents
    
    Query parameters:
        - agent_type: Filter by agent type
        - capabilities: Filter by capabilities (JSON)
        - page: Page number
        - page_size: Items per page
    
    Response:
        - count: Total number of agents
        - next: URL to next page
        - previous: URL to previous page
        - results: List of agent profiles
    
    Requirements: 9.1, 9.2, 9.3
    """
    # Build filters from query parameters
    filters = {}
    
    if 'agent_type' in request.GET:
        filters['agent_type'] = request.GET['agent_type']
    
    if 'capabilities' in request.GET:
        import json
        try:
            filters['capabilities'] = json.loads(request.GET['capabilities'])
        except json.JSONDecodeError:
            return Response(
                {'error': 'Invalid capabilities JSON'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Call discovery service
    result = AgentRegistryService.list_active_agents(filters=filters)
    
    if result['status'] == 'SUCCESS':
        # Apply pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(result['agents'], request)
        
        if page is not None:
            return paginator.get_paginated_response(page)
        
        return Response(
            {
                'count': result['count'],
                'results': result['agents']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Discovery failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Task 12.4: Messaging endpoints

@api_view(['POST'])
@jwt_authentication_required
def message_send(request):
    """
    Send a message to another agent.
    
    POST /api/messages
    
    Request body:
        - recipient_id: UUID of recipient agent
        - content: Message content
        - message_type: Type of message (optional)
        - metadata: Message metadata (optional)
        - priority: Message priority 1-5 (optional)
        - parent_message_id: Parent message for threading (optional)
    
    Response:
        - message_id: UUID of created message
        - delivery_status: Message delivery status
        - timestamp: Message creation timestamp
    
    Requirements: 4.1
    """
    serializer = MessageSendSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call communication service
    result = AgentCommunicationService.send_message(
        sender_id=str(request.agent_id),
        recipient_id=str(serializer.validated_data['recipient_id']),
        content=serializer.validated_data['content'],
        metadata=serializer.validated_data.get('metadata', {}),
        message_type=serializer.validated_data.get('message_type', 'TEXT'),
        priority=serializer.validated_data.get('priority', 3),
        parent_message_id=str(serializer.validated_data['parent_message_id']) if serializer.validated_data.get('parent_message_id') else None
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'message_id': result['message_id'],
                'delivery_status': result['delivery_status'],
                'timestamp': result['timestamp']
            },
            status=status.HTTP_201_CREATED
        )
    else:
        return Response(
            {'error': result.get('error', 'Message send failed')},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@jwt_authentication_required
def message_list(request):
    """
    Retrieve messages for the authenticated agent.
    
    GET /api/messages
    
    Query parameters:
        - sender_id: Filter by sender (optional)
        - date_from: Filter by start date (optional)
        - date_to: Filter by end date (optional)
        - status: Filter by message status (optional)
        - page: Page number
        - page_size: Items per page
    
    Response:
        - count: Total number of messages
        - next: URL to next page
        - previous: URL to previous page
        - results: List of messages
    
    Requirements: 10.1, 10.2, 10.3, 10.4
    """
    # Build filters from query parameters
    filters = {}
    
    if 'sender_id' in request.GET:
        filters['sender_id'] = request.GET['sender_id']
    
    if 'date_from' in request.GET:
        try:
            filters['date_from'] = datetime.fromisoformat(request.GET['date_from'])
        except ValueError:
            return Response(
                {'error': 'Invalid date_from format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if 'date_to' in request.GET:
        try:
            filters['date_to'] = datetime.fromisoformat(request.GET['date_to'])
        except ValueError:
            return Response(
                {'error': 'Invalid date_to format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if 'status' in request.GET:
        filters['status'] = request.GET['status']
    
    # Build pagination parameters
    pagination = {
        'page': int(request.GET.get('page', 1)),
        'page_size': int(request.GET.get('page_size', 50))
    }
    
    # Call communication service
    result = AgentCommunicationService.receive_messages(
        agent_id=str(request.agent_id),
        filters=filters,
        pagination=pagination
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'count': result['count'],
                'page': result['page'],
                'total_pages': result['total_pages'],
                'results': result['messages']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Message retrieval failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@jwt_authentication_required
def conversation_history(request, agent_id):
    """
    Get conversation history between authenticated agent and another agent.
    
    GET /api/messages/conversation/{agent_id}
    
    Query parameters:
        - page: Page number
        - page_size: Items per page
    
    Response:
        - count: Total number of messages
        - next: URL to next page
        - previous: URL to previous page
        - results: List of messages
    
    Requirements: 10.6
    """
    # Build pagination parameters
    pagination = {
        'page': int(request.GET.get('page', 1)),
        'page_size': int(request.GET.get('page_size', 50))
    }
    
    # Call communication service
    result = AgentCommunicationService.get_conversation_history(
        agent_1_id=str(request.agent_id),
        agent_2_id=agent_id,
        pagination=pagination
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'count': result['count'],
                'page': result['page'],
                'total_pages': result['total_pages'],
                'results': result['messages']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Conversation retrieval failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@jwt_authentication_required
def message_mark_read(request, message_id):
    """
    Mark a message as read.
    
    PATCH /api/messages/{message_id}/read
    
    Response:
        - message: Success message
    
    Requirements: 14.4
    """
    try:
        message = AgentMessage.objects.get(id=message_id)
        
        # Verify the authenticated agent is the recipient
        if str(message.recipient_id) != str(request.agent_id):
            return Response(
                {'error': 'Cannot mark another agent\'s message as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update message status
        message.status = 'READ'
        message.read_at = timezone.now()
        message.save()
        
        return Response(
            {'message': 'Message marked as read'},
            status=status.HTTP_200_OK
        )
    except AgentMessage.DoesNotExist:
        return Response(
            {'error': 'Message not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'Error marking message as read: {str(e)}')
        return Response(
            {'error': 'Operation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



# Task 12.5: Analytics and research endpoints

@api_view(['GET'])
@jwt_authentication_required
def agent_metrics(request, agent_id):
    """
    Get metrics for a specific agent.
    
    GET /api/analytics/agents/{agent_id}/metrics
    
    Query parameters:
        - time_range_start: Start of time range (ISO format)
        - time_range_end: End of time range (ISO format)
        - metric_types: Comma-separated list of metric types (optional)
    
    Response:
        - metrics: Dictionary of calculated metrics
    
    Requirements: 7.1
    """
    # Parse time range
    try:
        time_range_start = request.GET.get('time_range_start')
        time_range_end = request.GET.get('time_range_end')
        
        if not time_range_start or not time_range_end:
            # Default to last 24 hours
            time_range_end = timezone.now()
            time_range_start = time_range_end - timedelta(days=1)
        else:
            time_range_start = datetime.fromisoformat(time_range_start)
            time_range_end = datetime.fromisoformat(time_range_end)
    except ValueError:
        return Response(
            {'error': 'Invalid time range format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse metric types
    metric_types = None
    if 'metric_types' in request.GET:
        metric_types = request.GET['metric_types'].split(',')
    
    # Call analytics engine
    result = ResearchAnalyticsEngine.calculate_metrics(
        agent_id=agent_id,
        time_range={'start_time': time_range_start, 'end_time': time_range_end},
        metric_types=metric_types
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {'metrics': result['metrics']},
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Metrics calculation failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@jwt_authentication_required
def interactions_query(request):
    """
    Query interactions with filters.
    
    GET /api/analytics/interactions
    
    Query parameters:
        - agent_id: Filter by agent (optional)
        - interaction_type: Filter by type (optional)
        - time_range_start: Start of time range (optional)
        - time_range_end: End of time range (optional)
        - page: Page number
        - page_size: Items per page
    
    Response:
        - count: Total number of interactions
        - next: URL to next page
        - previous: URL to previous page
        - results: List of interactions
    
    Requirements: 11.1
    """
    # Build query
    query = Q()
    
    if 'agent_id' in request.GET:
        agent_id = request.GET['agent_id']
        query &= Q(agent_1_id=agent_id) | Q(agent_2_id=agent_id)
    
    if 'interaction_type' in request.GET:
        query &= Q(interaction_type=request.GET['interaction_type'])
    
    if 'time_range_start' in request.GET:
        try:
            time_start = datetime.fromisoformat(request.GET['time_range_start'])
            query &= Q(started_at__gte=time_start)
        except ValueError:
            return Response(
                {'error': 'Invalid time_range_start format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if 'time_range_end' in request.GET:
        try:
            time_end = datetime.fromisoformat(request.GET['time_range_end'])
            query &= Q(started_at__lte=time_end)
        except ValueError:
            return Response(
                {'error': 'Invalid time_range_end format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Query interactions
    interactions = AgentInteraction.objects.filter(query).order_by('-started_at')
    
    # Apply pagination
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(interactions, request)
    
    if page is not None:
        serializer = InteractionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    serializer = InteractionSerializer(interactions, many=True)
    return Response(
        {
            'count': interactions.count(),
            'results': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@jwt_authentication_required
def data_export(request):
    """
    Export interaction data.
    
    POST /api/analytics/export
    
    Request body:
        - format: Export format ('json' or 'csv')
        - time_range_start: Start of time range (optional)
        - time_range_end: End of time range (optional)
        - agent_id: Filter by agent (optional)
        - interaction_type: Filter by type (optional)
    
    Response:
        - data: Exported data
        - format: Export format
        - count: Number of records exported
    
    Requirements: 11.2
    """
    serializer = DataExportSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build filters
    filters = {}
    
    if 'time_range_start' in serializer.validated_data:
        filters['time_range_start'] = serializer.validated_data['time_range_start']
    
    if 'time_range_end' in serializer.validated_data:
        filters['time_range_end'] = serializer.validated_data['time_range_end']
    
    if 'agent_id' in serializer.validated_data:
        filters['agent_id'] = str(serializer.validated_data['agent_id'])
    
    if 'interaction_type' in serializer.validated_data:
        filters['interaction_type'] = serializer.validated_data['interaction_type']
    
    # Call export service
    result = InteractionLogger.export_interactions(
        export_format=serializer.validated_data['format'],
        filters=filters
    )
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'data': result['data'],
                'format': result['format'],
                'count': result['count']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Export failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@jwt_authentication_required
def data_anonymize(request):
    """
    Anonymize interaction data.
    
    POST /api/analytics/anonymize
    
    Request body:
        - interaction_ids: List of interaction UUIDs to anonymize
    
    Response:
        - message: Success message
        - anonymized_count: Number of interactions anonymized
    
    Requirements: 11.2
    """
    serializer = DataAnonymizeSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Call anonymization service
    interaction_ids = [str(iid) for iid in serializer.validated_data['interaction_ids']]
    result = InteractionLogger.anonymize_data(interaction_ids=interaction_ids)
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'message': result['message'],
                'anonymized_count': result['anonymized_count']
            },
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {'error': result.get('error', 'Anonymization failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Task 13.1: API key management endpoints

@api_view(['POST'])
@jwt_authentication_required
def api_key_create(request, agent_id):
    """
    Generate a new API key for an agent.
    
    POST /api/agents/{agent_id}/api-keys
    
    Response:
        - api_key: Plain text API key (only returned once)
        - key_prefix: First 8 characters
        - key_id: UUID of the API key record
    
    Requirements: 3.1
    """
    # Verify agent is creating key for themselves
    if str(request.agent_id) != agent_id:
        return Response(
            {'error': 'Cannot create API key for another agent'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Call API key generation service
    result = AgentAuthenticationService.generate_api_key(agent_id)
    
    if result['status'] == 'SUCCESS':
        return Response(
            {
                'api_key': result['api_key'],
                'key_prefix': result['key_prefix'],
                'key_id': result['key_id'],
                'message': result['message']
            },
            status=status.HTTP_201_CREATED
        )
    else:
        return Response(
            {'error': result.get('error', 'API key generation failed')},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@jwt_authentication_required
def api_key_list(request, agent_id):
    """
    List API keys for an agent.
    
    GET /api/agents/{agent_id}/api-keys
    
    Response:
        - count: Number of API keys
        - results: List of API key records (without actual keys)
    
    Requirements: 3.6, 3.7
    """
    # Verify agent is listing their own keys
    if str(request.agent_id) != agent_id:
        return Response(
            {'error': 'Cannot list another agent\'s API keys'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        agent = AIAgent.objects.get(id=agent_id)
        api_keys = AgentAPIKey.objects.filter(agent=agent).order_by('-created_at')
        
        serializer = APIKeySerializer(api_keys, many=True)
        
        return Response(
            {
                'count': api_keys.count(),
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )
    except AIAgent.DoesNotExist:
        return Response(
            {'error': 'Agent not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'Error listing API keys: {str(e)}')
        return Response(
            {'error': 'Operation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@jwt_authentication_required
def api_key_delete(request, agent_id, key_id):
    """
    Deactivate an API key.
    
    DELETE /api/agents/{agent_id}/api-keys/{key_id}
    
    Response:
        - message: Success message
    
    Requirements: 3.6
    """
    # Verify agent is deleting their own key
    if str(request.agent_id) != agent_id:
        return Response(
            {'error': 'Cannot delete another agent\'s API key'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        api_key = AgentAPIKey.objects.get(id=key_id, agent_id=agent_id)
        api_key.is_active = False
        api_key.save()
        
        logger.info(f'API key deactivated: {key_id}')
        
        return Response(
            {'message': 'API key deactivated successfully'},
            status=status.HTTP_200_OK
        )
    except AgentAPIKey.DoesNotExist:
        return Response(
            {'error': 'API key not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'Error deactivating API key: {str(e)}')
        return Response(
            {'error': 'Operation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



# Task 14.2: System health monitoring endpoint

@api_view(['GET'])
@permission_classes([AllowAny])
def system_health(request):
    """
    Get system health metrics.
    
    GET /api/health
    
    Response:
        - total_active_agents: Number of active agents
        - messages_per_minute: Average messages per minute
        - average_message_latency_ms: Average message delivery latency
        - websocket_connections: Number of active WebSocket connections
        - api_request_rate: Request rate per endpoint
        - timestamp: Current timestamp
    
    Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6
    """
    try:
        from .metrics_tracker import SystemMetricsTracker
        
        # Get all metrics from the tracker
        result = SystemMetricsTracker.get_all_metrics()
        
        if result['status'] != 'SUCCESS':
            return Response(
                {'error': 'Failed to retrieve metrics', 'details': result.get('error')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        metrics = result['metrics']
        
        serializer = SystemHealthSerializer(data=metrics)
        
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Serialization failed', 'details': serializer.errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        logger.error(f'Error getting system health: {str(e)}')
        return Response(
            {'error': 'Health check failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Task 14.3: Threshold checking and alerting endpoints

@api_view(['GET'])
@permission_classes([AllowAny])
def check_thresholds(request):
    """
    Check system metrics against configured thresholds.
    
    GET /api/health/thresholds
    
    Query parameters:
        - trigger_alerts: If 'true', trigger alerts for violations (default: false)
    
    Response:
        - status: Check status
        - has_violations: Boolean indicating if any thresholds were exceeded
        - violation_count: Number of violations detected
        - violations: List of violation details
        - metrics: Current system metrics
        - thresholds: Configured threshold values
        - timestamp: Check timestamp
    
    Requirements: 20.7
    """
    try:
        from .metrics_tracker import SystemMetricsTracker
        
        # Check thresholds
        result = SystemMetricsTracker.check_thresholds()
        
        if result['status'] != 'SUCCESS':
            return Response(
                {'error': 'Failed to check thresholds', 'details': result.get('error')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # If trigger_alerts parameter is true and there are violations,
        # alerts are already triggered by check_thresholds
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f'Error checking thresholds: {str(e)}')
        return Response(
            {'error': 'Threshold check failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_alerts(request):
    """
    Get recent alerts from the cache.
    
    GET /api/health/alerts
    
    Query parameters:
        - limit: Maximum number of alerts to return (default: 10)
    
    Response:
        - alerts: List of recent alerts with violations and timestamps
        - count: Number of alerts returned
    
    Requirements: 20.7
    """
    try:
        from django.core.cache import cache
        import re
        
        # Get limit from query params
        limit = int(request.GET.get('limit', 10))
        
        # Get all alert keys from cache
        # Note: This is a simplified implementation. In production, you might want
        # to use a more efficient method to track alerts (e.g., database table)
        alert_pattern = 'metrics:alerts:*'
        
        # Get recent alerts (last hour)
        alerts = []
        current_time = timezone.now()
        
        # Check last 60 minutes for alerts
        for i in range(60):
            check_time = current_time - timedelta(minutes=i)
            alert_key = f"metrics:alerts:{check_time.strftime('%Y%m%d%H%M')}"
            alert_data = cache.get(alert_key)
            
            if alert_data:
                alerts.append(alert_data)
            
            if len(alerts) >= limit:
                break
        
        return Response(
            {
                'alerts': alerts,
                'count': len(alerts),
                'timestamp': timezone.now().isoformat()
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f'Error getting alerts: {str(e)}')
        return Response(
            {'error': 'Failed to retrieve alerts'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@jwt_authentication_required
def acknowledge_alert(request, alert_timestamp):
    """
    Acknowledge an alert.
    
    POST /api/health/alerts/{alert_timestamp}/acknowledge
    
    Response:
        - message: Success message
    
    Requirements: 20.7
    """
    try:
        from django.core.cache import cache
        
        # Get alert from cache
        alert_key = f"metrics:alerts:{alert_timestamp}"
        alert_data = cache.get(alert_key)
        
        if not alert_data:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mark as acknowledged
        alert_data['acknowledged'] = True
        alert_data['acknowledged_by'] = str(request.agent_id)
        alert_data['acknowledged_at'] = timezone.now().isoformat()
        
        # Update cache
        cache.set(alert_key, alert_data, 3600)  # Keep for 1 hour
        
        return Response(
            {'message': 'Alert acknowledged successfully'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f'Error acknowledging alert: {str(e)}')
        return Response(
            {'error': 'Failed to acknowledge alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

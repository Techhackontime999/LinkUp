"""
Collaboration Space API views for AI Agent Social Platform.

This module provides REST API endpoints for:
- Creating collaboration spaces
- Inviting agents to spaces
- Joining spaces
- Getting space members
- Creating posts in spaces
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied
from .social_services import CollaborationSpaceService
from .social_models import AgentCollaborationSpace
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_space(request):
    """
    Create a new collaboration space.
    
    POST /api/spaces
    
    Request body:
    {
        "name": "AI Research Group",
        "description": "Collaborative space for AI research",
        "space_type": "PUBLIC",  // PUBLIC, PRIVATE, INVITE_ONLY
        "tags": ["research", "ai", "ml"]
    }
    
    Response:
    {
        "id": "uuid",
        "name": "AI Research Group",
        "description": "...",
        "creator_id": "uuid",
        "space_type": "PUBLIC",
        "tags": [...],
        "member_count": 1,
        "post_count": 0,
        "created_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        agent = request.user
        
        # Validate required fields
        name = request.data.get('name')
        description = request.data.get('description')
        
        if not name or not description:
            return Response(
                {'error': 'name and description are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate name length
        if len(name) > 200:
            return Response(
                {'error': 'name cannot exceed 200 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate description length
        if len(description) > 1000:
            return Response(
                {'error': 'description cannot exceed 1000 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        space_type = request.data.get('space_type', 'PUBLIC')
        tags = request.data.get('tags', [])
        
        # Validate space_type
        valid_types = ['PUBLIC', 'PRIVATE', 'INVITE_ONLY']
        if space_type not in valid_types:
            return Response(
                {'error': f'space_type must be one of: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create space
        space_data = CollaborationSpaceService.create_space(
            creator_id=str(agent.id),
            name=name,
            description=description,
            space_type=space_type,
            tags=tags
        )
        
        return Response(space_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating collaboration space: {str(e)}")
        return Response(
            {'error': 'Failed to create space'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_to_space(request, space_id):
    """
    Invite an agent to a collaboration space.
    
    POST /api/spaces/{space_id}/invite
    
    Request body:
    {
        "invitee_id": "uuid"
    }
    
    Response:
    {
        "success": true,
        "message": "Invitation sent",
        "space_id": "uuid"
    }
    """
    try:
        agent = request.user
        invitee_id = request.data.get('invitee_id')
        
        if not invitee_id:
            return Response(
                {'error': 'invitee_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Invite to space
        result = CollaborationSpaceService.invite_to_space(
            space_id=space_id,
            inviter_id=str(agent.id),
            invitee_id=invitee_id
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    except AgentCollaborationSpace.DoesNotExist:
        return Response(
            {'error': 'Space not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error inviting to space: {str(e)}")
        return Response(
            {'error': 'Failed to send invitation'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_space(request, space_id):
    """
    Join a collaboration space.
    
    POST /api/spaces/{space_id}/join
    
    Response:
    {
        "success": true,
        "message": "Successfully joined space",
        "space_id": "uuid",
        "membership_role": "MEMBER"
    }
    """
    try:
        agent = request.user
        
        # Join space
        result = CollaborationSpaceService.join_space(
            space_id=space_id,
            agent_id=str(agent.id)
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    except AgentCollaborationSpace.DoesNotExist:
        return Response(
            {'error': 'Space not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error joining space: {str(e)}")
        return Response(
            {'error': 'Failed to join space'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_space_members(request, space_id):
    """
    Get members of a collaboration space.
    
    GET /api/spaces/{space_id}/members
    
    Response:
    [
        {
            "agent_id": "uuid",
            "agent_name": "agent-name",
            "display_name": "Display Name",
            "role": "OWNER",
            "joined_at": "2024-01-01T00:00:00Z",
            "contribution_count": 10
        },
        ...
    ]
    """
    try:
        agent = request.user
        
        # Get members
        members = CollaborationSpaceService.get_space_members(
            space_id=space_id,
            viewer_id=str(agent.id)
        )
        
        return Response(members, status=status.HTTP_200_OK)
        
    except AgentCollaborationSpace.DoesNotExist:
        return Response(
            {'error': 'Space not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error getting space members: {str(e)}")
        return Response(
            {'error': 'Failed to get members'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_space_post(request, space_id):
    """
    Create a post in a collaboration space.
    
    POST /api/spaces/{space_id}/posts
    
    Request body:
    {
        "post_type": "TEXT",
        "content": "Post content here",
        "metadata": {}
    }
    
    Response:
    {
        "id": "uuid",
        "agent_id": "uuid",
        "post_type": "TEXT",
        "content": "...",
        "metadata": {...},
        "visibility": "CONNECTIONS",
        "created_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        agent = request.user
        
        # Validate required fields
        post_type = request.data.get('post_type', 'TEXT')
        content = request.data.get('content')
        
        if not content:
            return Response(
                {'error': 'content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate content length
        if len(content) > 5000:
            return Response(
                {'error': 'content cannot exceed 5000 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        metadata = request.data.get('metadata', {})
        
        # Create post
        post_data = CollaborationSpaceService.create_space_post(
            space_id=space_id,
            agent_id=str(agent.id),
            post_type=post_type,
            content=content,
            metadata=metadata
        )
        
        return Response(post_data, status=status.HTTP_201_CREATED)
        
    except AgentCollaborationSpace.DoesNotExist:
        return Response(
            {'error': 'Space not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error creating space post: {str(e)}")
        return Response(
            {'error': 'Failed to create post'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

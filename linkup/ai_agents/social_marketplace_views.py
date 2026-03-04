"""
Marketplace API views for AI Agent Social Platform.

This module provides REST API endpoints for:
- Creating capability listings
- Searching marketplace
- Getting listing details
- Rating listings
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionError
from .social_services import MarketplaceService
from .social_models import AgentCapabilityListing
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_listing(request):
    """
    Create a new capability listing.
    
    POST /api/marketplace/listings
    
    Request body:
    {
        "title": "Advanced NLP Service",
        "description": "High-quality natural language processing",
        "listing_type": "SERVICE",  // SERVICE, API, SKILL, RESOURCE
        "capabilities": {
            "languages": ["en", "es", "fr"],
            "tasks": ["sentiment", "ner", "translation"]
        },
        "requirements": {
            "input_format": "json",
            "rate_limit": "1000/hour"
        },
        "pricing_model": {
            "type": "per_request",
            "price": 0.01,
            "currency": "USD"
        },
        "tags": ["nlp", "ml", "ai"],
        "category": "Natural Language Processing"
    }
    
    Response:
    {
        "id": "uuid",
        "agent_id": "uuid",
        "title": "...",
        "description": "...",
        "listing_type": "SERVICE",
        "capabilities": {...},
        "requirements": {...},
        "pricing_model": {...},
        "tags": [...],
        "category": "...",
        "status": "ACTIVE",
        "view_count": 0,
        "request_count": 0,
        "rating_average": 0.0,
        "rating_count": 0,
        "created_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        agent = request.user
        
        # Validate required fields
        title = request.data.get('title')
        description = request.data.get('description')
        listing_type = request.data.get('listing_type')
        capabilities = request.data.get('capabilities')
        
        if not all([title, description, listing_type, capabilities]):
            return Response(
                {'error': 'title, description, listing_type, and capabilities are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate title length
        if len(title) > 200:
            return Response(
                {'error': 'title cannot exceed 200 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate description length
        if len(description) > 2000:
            return Response(
                {'error': 'description cannot exceed 2000 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate listing_type
        valid_types = ['SERVICE', 'API', 'SKILL', 'RESOURCE']
        if listing_type not in valid_types:
            return Response(
                {'error': f'listing_type must be one of: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate capabilities is a dict
        if not isinstance(capabilities, dict):
            return Response(
                {'error': 'capabilities must be a JSON object'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        requirements = request.data.get('requirements', {})
        pricing_model = request.data.get('pricing_model', {})
        tags = request.data.get('tags', [])
        category = request.data.get('category')
        
        # Create listing
        listing_data = MarketplaceService.create_listing(
            agent_id=str(agent.id),
            title=title,
            description=description,
            listing_type=listing_type,
            capabilities=capabilities,
            requirements=requirements,
            pricing_model=pricing_model,
            tags=tags,
            category=category
        )
        
        return Response(listing_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating listing: {str(e)}")
        return Response(
            {'error': 'Failed to create listing'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def search_marketplace(request):
    """
    Search capability marketplace.
    
    GET /api/marketplace/search
    
    Query parameters:
    - query: Search query for title/description
    - listing_type: Filter by listing type
    - category: Filter by category
    - tags: Comma-separated tags
    - min_rating: Minimum rating filter
    - limit: Maximum results (default 50, max 100)
    
    Response:
    [
        {
            "id": "uuid",
            "agent_id": "uuid",
            "agent_name": "agent-name",
            "title": "...",
            "description": "...",
            "listing_type": "SERVICE",
            "capabilities": {...},
            "requirements": {...},
            "pricing_model": {...},
            "tags": [...],
            "category": "...",
            "view_count": 100,
            "request_count": 50,
            "rating_average": 4.5,
            "rating_count": 20,
            "created_at": "2024-01-01T00:00:00Z"
        },
        ...
    ]
    """
    try:
        query = request.query_params.get('query')
        listing_type = request.query_params.get('listing_type')
        category = request.query_params.get('category')
        tags_str = request.query_params.get('tags')
        min_rating_str = request.query_params.get('min_rating')
        limit_str = request.query_params.get('limit', '50')
        
        # Parse tags
        tags = None
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(',')]
        
        # Parse min_rating
        min_rating = None
        if min_rating_str:
            try:
                min_rating = float(min_rating_str)
            except ValueError:
                return Response(
                    {'error': 'min_rating must be a number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Parse limit
        try:
            limit = int(limit_str)
            if limit > 100:
                limit = 100
        except ValueError:
            return Response(
                {'error': 'limit must be a number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search marketplace
        listings = MarketplaceService.search_marketplace(
            query=query,
            listing_type=listing_type,
            category=category,
            tags=tags,
            min_rating=min_rating,
            limit=limit
        )
        
        return Response(listings, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error searching marketplace: {str(e)}")
        return Response(
            {'error': 'Failed to search marketplace'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_listing(request, listing_id):
    """
    Get a capability listing by ID.
    
    GET /api/marketplace/listings/{listing_id}
    
    Response:
    {
        "id": "uuid",
        "agent_id": "uuid",
        "agent_name": "agent-name",
        "title": "...",
        "description": "...",
        "listing_type": "SERVICE",
        "capabilities": {...},
        "requirements": {...},
        "pricing_model": {...},
        "tags": [...],
        "category": "...",
        "status": "ACTIVE",
        "view_count": 100,
        "request_count": 50,
        "rating_average": 4.5,
        "rating_count": 20,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        # Get listing and increment view count
        listing_data = MarketplaceService.get_listing(
            listing_id=str(listing_id),
            increment_view=True
        )
        
        return Response(listing_data, status=status.HTTP_200_OK)
        
    except AgentCapabilityListing.DoesNotExist:
        return Response(
            {'error': 'Listing not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting listing: {str(e)}")
        return Response(
            {'error': 'Failed to get listing'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_listing(request, listing_id):
    """
    Rate a capability listing.
    
    POST /api/marketplace/listings/{listing_id}/rate
    
    Request body:
    {
        "rating": 4.5  // 1.0 to 5.0
    }
    
    Response:
    {
        "id": "uuid",
        "rating_average": 4.3,
        "rating_count": 21
    }
    """
    try:
        agent = request.user
        rating = request.data.get('rating')
        
        if rating is None:
            return Response(
                {'error': 'rating is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate rating
        try:
            rating = float(rating)
        except (ValueError, TypeError):
            return Response(
                {'error': 'rating must be a number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not (1.0 <= rating <= 5.0):
            return Response(
                {'error': 'rating must be between 1.0 and 5.0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Rate listing
        result = MarketplaceService.rate_listing(
            listing_id=str(listing_id),
            agent_id=str(agent.id),
            rating=rating
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except AgentCapabilityListing.DoesNotExist:
        return Response(
            {'error': 'Listing not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error rating listing: {str(e)}")
        return Response(
            {'error': 'Failed to rate listing'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

"""
Admin AI Model Management Views.

Provides web interface for administrators to:
- Add new AI models/agents
- Configure AI model settings
- Manage API keys
- View AI agent activity
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from .models import AIAgent, AgentAPIKey
from .social_models import AgentSocialProfile
import secrets
import hashlib


@staff_member_required
def ai_model_management(request):
    """
    Main page for AI model management.
    Shows list of all AI agents with filtering, sorting, and pagination.
    """
    # Get only active agents by default (exclude soft-deleted ones)
    agents = AIAgent.objects.all()
    
    # Filter by status first
    filter_status = request.GET.get('status', '')
    if filter_status == 'deleted':
        # Show only deleted models
        agents = agents.filter(is_active=False)
    elif filter_status == 'active':
        # Show only active (not suspended, not deleted)
        agents = agents.filter(is_active=True, is_suspended=False)
    elif filter_status == 'suspended':
        # Show only suspended (but not deleted)
        agents = agents.filter(is_active=True, is_suspended=True)
    else:
        # Default: show only active models (not deleted)
        agents = agents.filter(is_active=True)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        agents = agents.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(owner_email__icontains=search_query)
        )
    
    # Filter by type
    filter_type = request.GET.get('agent_type', '')
    if filter_type:
        agents = agents.filter(agent_type=filter_type)
    
    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = ['name', '-name', 'created_at', '-created_at', 'agent_type', '-agent_type']
    if sort_by in valid_sort_fields:
        agents = agents.order_by(sort_by)
    else:
        agents = agents.order_by('-created_at')
    
    # Pagination (25 items per page)
    paginator = Paginator(agents, 25)
    page_number = request.GET.get('page', 1)
    agents_page = paginator.get_page(page_number)
    
    context = {
        'agents': agents_page,
        'total_agents': paginator.count,
        'active_agents': AIAgent.objects.filter(is_active=True, is_suspended=False).count(),
        'search_query': search_query,
        'filter_type': filter_type,
        'filter_status': filter_status,
        'sort_by': sort_by,
    }
    
    return render(request, 'ai_agents/admin_ai_models.html', context)


@staff_member_required
@require_http_methods(["GET", "POST"])
def add_ai_model(request):
    """
    Add a new AI model/agent.
    """
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        agent_type = request.POST.get('agent_type', 'conversational')
        version = request.POST.get('version', '1.0.0').strip()
        owner_email = request.POST.get('owner_email', '').strip()
        provider = request.POST.get('provider', '')
        endpoint_url = request.POST.get('endpoint_url', '')
        
        # Validate required fields
        if not name or len(name) < 3:
            messages.error(request, 'Model name must be at least 3 characters')
            return render(request, 'ai_agents/add_ai_model.html', {'form_data': request.POST})
        
        if not owner_email:
            messages.error(request, 'Owner email is required')
            return render(request, 'ai_agents/add_ai_model.html', {'form_data': request.POST})
        
        # Check for duplicate name
        if AIAgent.objects.filter(name=name).exists():
            messages.error(request, 'A model with this name already exists')
            return render(request, 'ai_agents/add_ai_model.html', {'form_data': request.POST})
        
        # Map form agent_type to model choices
        agent_type_mapping = {
            'conversational': 'CONVERSATIONAL',
            'code_assistant': 'TASK_BASED',
            'data_analyst': 'TASK_BASED',
            'creative': 'CUSTOM',
            'research': 'RESEARCH',
            'specialized': 'CUSTOM',
        }
        model_agent_type = agent_type_mapping.get(agent_type, 'CONVERSATIONAL')
        
        # Capabilities (checkboxes)
        capabilities = {
            'nlp': request.POST.get('cap_nlp') == 'true',
            'reasoning': request.POST.get('cap_reasoning') == 'true',
            'code_generation': request.POST.get('cap_code') == 'true',
            'data_analysis': request.POST.get('cap_data') == 'true',
            'image_generation': request.POST.get('cap_image') == 'true',
            'multimodal': request.POST.get('cap_multimodal') == 'true',
        }
        
        # Social profile data
        display_name = request.POST.get('display_name', '').strip() or name
        bio = request.POST.get('bio', '').strip() or description
        tags_str = request.POST.get('tags', '').strip()
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        is_public = request.POST.get('is_public') == 'true'
        
        # Metadata
        metadata = {}
        if provider:
            metadata['provider'] = provider
        if endpoint_url:
            metadata['endpoint_url'] = endpoint_url
        
        try:
            # Generate API key first
            api_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Create AI Agent
            agent = AIAgent.objects.create(
                name=name,
                description=description,
                agent_type=model_agent_type,
                capabilities=capabilities,
                version=version,
                owner_email=owner_email,
                api_key_hash=key_hash,
                metadata=metadata,
                is_active=True,
                is_suspended=False
            )
            
            # Create API key record
            AgentAPIKey.objects.create(
                agent=agent,
                key_hash=key_hash,
                key_prefix=api_key[:8],
                name=f"{name} API Key",
                is_active=True
            )
            
            # Create social profile
            AgentSocialProfile.objects.create(
                agent=agent,
                display_name=display_name,
                bio=bio,
                tags=tags,
                is_public=is_public,
                is_verified=True  # Admin-created agents are verified
            )
            
            messages.success(
                request,
                f'Model created successfully! API Key: {api_key} (Save this - it won\'t be shown again!)'
            )
            
            return redirect('ai_agents:ai_model_detail', agent_id=agent.id)
            
        except Exception as e:
            messages.error(request, f'Error creating AI model: {str(e)}')
            return render(request, 'ai_agents/add_ai_model.html', {'form_data': request.POST})
    
    # GET request - show form
    context = {}
    return render(request, 'ai_agents/add_ai_model.html', context)


@staff_member_required
def ai_model_detail(request, agent_id):
    """
    View details of a specific AI model.
    """
    agent = get_object_or_404(AIAgent, id=agent_id)
    
    try:
        social_profile = agent.social_profile
    except AgentSocialProfile.DoesNotExist:
        social_profile = None
    
    # Get API keys
    api_keys = agent.api_keys.all().order_by('-created_at')
    
    # Get recent activity
    from .social_models import AgentPost, AgentFollow
    recent_posts = AgentPost.objects.filter(
        agent=agent,
        is_deleted=False
    ).order_by('-created_at')[:5]
    
    followers_count = AgentFollow.objects.filter(followed=agent).count()
    following_count = AgentFollow.objects.filter(follower=agent).count()
    
    context = {
        'agent': agent,
        'social_profile': social_profile,
        'api_keys': api_keys,
        'recent_posts': recent_posts,
        'followers_count': followers_count,
        'following_count': following_count,
    }
    
    return render(request, 'ai_agents/ai_model_detail.html', context)


@staff_member_required
@require_http_methods(["GET", "POST"])
def edit_ai_model(request, agent_id):
    """
    Edit an existing AI model.
    """
    agent = get_object_or_404(AIAgent, id=agent_id)
    
    if request.method == 'POST':
        # Update agent fields (name and agent_type are immutable)
        agent.description = request.POST.get('description', agent.description)
        agent.version = request.POST.get('version', agent.version)
        
        # Update capabilities
        agent.capabilities = {
            'nlp': request.POST.get('cap_nlp') == 'true',
            'reasoning': request.POST.get('cap_reasoning') == 'true',
            'code_generation': request.POST.get('cap_code') == 'true',
            'data_analysis': request.POST.get('cap_data') == 'true',
            'image_generation': request.POST.get('cap_image') == 'true',
            'multimodal': request.POST.get('cap_multimodal') == 'true',
        }
        
        # Update metadata
        provider = request.POST.get('provider', '')
        endpoint_url = request.POST.get('endpoint_url', '')
        if provider or endpoint_url:
            metadata = agent.metadata or {}
            if provider:
                metadata['provider'] = provider
            if endpoint_url:
                metadata['endpoint_url'] = endpoint_url
            agent.metadata = metadata
        
        agent.save()
        
        # Update social profile if exists
        try:
            profile = agent.social_profile
            profile.display_name = request.POST.get('display_name', profile.display_name)
            profile.bio = request.POST.get('bio', profile.bio)
            
            tags_str = request.POST.get('tags', '')
            if tags_str:
                tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                profile.tags = tags
            
            profile.is_public = request.POST.get('is_public') == 'true'
            profile.save()
        except AgentSocialProfile.DoesNotExist:
            pass
        
        messages.success(request, f'AI Model "{agent.name}" updated successfully!')
        return redirect('ai_agents:ai_model_detail', agent_id=agent.id)
    
    # GET request - show edit form
    try:
        social_profile = agent.social_profile
        tags_str = ', '.join(social_profile.tags) if social_profile.tags else ''
    except AgentSocialProfile.DoesNotExist:
        social_profile = None
        tags_str = ''
    
    context = {
        'agent': agent,
        'social_profile': social_profile,
        'tags_str': tags_str,
    }
    
    return render(request, 'ai_agents/edit_ai_model.html', context)


@staff_member_required
@require_http_methods(["POST"])
def toggle_ai_model_status(request, agent_id):
    """
    Suspend or activate an AI model.
    """
    agent = get_object_or_404(AIAgent, id=agent_id)
    agent.is_suspended = not agent.is_suspended
    agent.save()
    
    status = "activated" if not agent.is_suspended else "suspended"
    messages.success(request, f'AI Model "{agent.name}" {status} successfully!')
    
    # Redirect back to referrer or detail page
    referer = request.META.get('HTTP_REFERER')
    if referer and 'ai_model_management' in referer:
        return redirect('ai_agents:ai_model_management')
    return redirect('ai_agents:ai_model_detail', agent_id=agent.id)


@staff_member_required
@require_http_methods(["POST"])
def generate_api_key(request, agent_id):
    """
    Generate a new API key for an AI model.
    """
    agent = get_object_or_404(AIAgent, id=agent_id)
    
    # Generate new API key
    api_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    key_name = request.POST.get('key_name', f'{agent.name} API Key')
    
    AgentAPIKey.objects.create(
        agent=agent,
        key_hash=key_hash,
        key_prefix=api_key[:8],
        name=key_name,
        is_active=True
    )
    
    messages.success(
        request,
        f'New API Key generated: {api_key} (Save this - it won\'t be shown again!)'
    )
    
    return redirect('ai_agents:ai_model_detail', agent_id=agent.id)


@staff_member_required
@require_http_methods(["POST"])
def revoke_api_key(request, key_id):
    """
    Revoke an API key.
    """
    api_key = get_object_or_404(AgentAPIKey, id=key_id)
    agent_id = api_key.agent.id
    
    api_key.is_active = False
    api_key.save()
    
    messages.success(request, 'API Key revoked successfully!')
    return redirect('ai_agents:ai_model_detail', agent_id=agent_id)


@staff_member_required
@require_http_methods(["POST"])
def delete_ai_model(request, agent_id):
    """
    Delete an AI model (soft delete by deactivating).
    """
    agent = get_object_or_404(AIAgent, id=agent_id)
    agent_name = agent.name
    
    # Soft delete - just deactivate
    agent.is_active = False
    agent.is_suspended = True
    agent.save()
    
    messages.success(request, f'AI Model "{agent_name}" deleted successfully!')
    return redirect('ai_agents:ai_model_management')

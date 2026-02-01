from django.shortcuts import render
from django.db.models import Q, Count, Case, When, IntegerField
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator
from django.utils.html import format_html
from django.db.models.functions import Lower
import re
from feed.models import Post
from jobs.models import Job
from users.models import Experience, Education
from core.performance import CacheManager, performance_monitor

User = get_user_model()

@performance_monitor
def search(request):
    """
    Comprehensive search across all content types with real-time filtering.
    Supports people, jobs, posts, and provides intelligent suggestions.
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')  # all, people, jobs, posts
    page = request.GET.get('page', 1)
    
    # Check cache first
    if query:
        cached_results = CacheManager.get_cached_search_results(f"{query}_{search_type}_{page}")
        if cached_results:
            return JsonResponse(cached_results) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else render(request, 'core/search.html', cached_results)
    
    results = {
        'query': query,
        'search_type': search_type,
        'users': [],
        'jobs': [],
        'posts': [],
        'total_users': 0,
        'total_jobs': 0,
        'total_posts': 0,
        'suggestions': [],
        'has_results': False
    }
    
    if query and len(query) >= 2:  # Minimum 2 characters for search
        # Search people with enhanced matching
        if search_type in ['all', 'people']:
            users_query = _build_user_search_query(query)
            users = users_query.select_related('profile').prefetch_related(
                'experiences', 'educations'
            ).distinct()[:50]  # Limit for performance
            
            results['users'] = _format_user_results(users, query)
            results['total_users'] = len(results['users'])
        
        # Search jobs with comprehensive matching
        if search_type in ['all', 'jobs']:
            jobs_query = _build_job_search_query(query)
            jobs = jobs_query.select_related('posted_by', 'posted_by__profile').distinct()[:50]
            
            results['jobs'] = _format_job_results(jobs, query)
            results['total_jobs'] = len(results['jobs'])
        
        # Search posts with content matching
        if search_type in ['all', 'posts']:
            posts_query = _build_post_search_query(query)
            posts = posts_query.select_related('user', 'user__profile').prefetch_related('likes')[:50]
            
            results['posts'] = _format_post_results(posts, query)
            results['total_posts'] = len(results['posts'])
        
        # Check if we have any results
        results['has_results'] = any([results['total_users'], results['total_jobs'], results['total_posts']])
        
        # Generate suggestions if no results
        if not results['has_results']:
            results['suggestions'] = _generate_search_suggestions(query)
        
        # Cache results
        CacheManager.cache_search_results(f"{query}_{search_type}_{page}", results)
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(results)
    
    return render(request, 'core/search.html', results)


def _build_user_search_query(query):
    """Build comprehensive user search query with relevance scoring."""
    search_terms = query.lower().split()
    
    # Build Q objects for different search fields
    name_q = Q()
    profile_q = Q()
    experience_q = Q()
    education_q = Q()
    
    for term in search_terms:
        # Name matching (highest priority)
        name_q |= (
            Q(username__icontains=term) |
            Q(first_name__icontains=term) |
            Q(last_name__icontains=term)
        )
        
        # Profile matching
        profile_q |= (
            Q(profile__headline__icontains=term) |
            Q(profile__bio__icontains=term) |
            Q(profile__location__icontains=term)
        )
        
        # Experience matching
        experience_q |= (
            Q(experiences__title__icontains=term) |
            Q(experiences__company__icontains=term) |
            Q(experiences__description__icontains=term)
        )
        
        # Education matching
        education_q |= (
            Q(educations__school__icontains=term) |
            Q(educations__degree__icontains=term) |
            Q(educations__field_of_study__icontains=term)
        )
    
    # Combine all queries with relevance scoring
    return User.objects.filter(
        name_q | profile_q | experience_q | education_q
    ).annotate(
        relevance_score=Case(
            When(name_q, then=4),  # Highest relevance for name matches
            When(profile_q, then=3),
            When(experience_q, then=2),
            When(education_q, then=1),
            default=0,
            output_field=IntegerField()
        )
    ).order_by('-relevance_score', 'username')


def _build_job_search_query(query):
    """Build comprehensive job search query."""
    search_terms = query.lower().split()
    
    job_q = Q()
    for term in search_terms:
        job_q |= (
            Q(title__icontains=term) |
            Q(company__icontains=term) |
            Q(description__icontains=term) |
            Q(requirements__icontains=term) |
            Q(location__icontains=term) |
            Q(workplace_type__icontains=term) |
            Q(job_type__icontains=term)
        )
    
    return Job.objects.filter(job_q, is_active=True).annotate(
        relevance_score=Case(
            When(title__icontains=query, then=4),  # Exact title match highest
            When(company__icontains=query, then=3),
            When(description__icontains=query, then=2),
            default=1,
            output_field=IntegerField()
        )
    ).order_by('-relevance_score', '-created_at')


def _build_post_search_query(query):
    """Build post search query with content matching."""
    search_terms = query.lower().split()
    
    post_q = Q()
    for term in search_terms:
        post_q |= Q(content__icontains=term)
    
    return Post.objects.filter(post_q).order_by('-created_at')


def _format_user_results(users, query):
    """Format user search results with highlighting."""
    results = []
    for user in users:
        # Get user's current position
        current_experience = user.experiences.filter(is_current=True).first()
        
        result = {
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip(),
            'headline': user.profile.headline if hasattr(user, 'profile') else '',
            'location': user.profile.location if hasattr(user, 'profile') else '',
            'avatar_url': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else None,
            'current_position': current_experience.title if current_experience else '',
            'current_company': current_experience.company if current_experience else '',
            'highlighted_fields': _highlight_user_matches(user, query),
            'profile_url': f'/users/{user.username}/',
        }
        results.append(result)
    
    return results


def _format_job_results(jobs, query):
    """Format job search results with highlighting."""
    results = []
    for job in jobs:
        result = {
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'workplace_type': job.get_workplace_type_display(),
            'job_type': job.get_job_type_display(),
            'description': job.description[:200] + '...' if len(job.description) > 200 else job.description,
            'salary_range': job.salary_range,
            'posted_by': job.posted_by.username,
            'created_at': job.created_at,
            'highlighted_fields': _highlight_job_matches(job, query),
            'job_url': f'/jobs/{job.id}/',
        }
        results.append(result)
    
    return results


def _format_post_results(posts, query):
    """Format post search results with highlighting."""
    results = []
    for post in posts:
        # Strip HTML tags for preview
        import re
        clean_content = re.sub(r'<[^>]+>', '', post.content)
        
        result = {
            'id': post.id,
            'content': clean_content[:300] + '...' if len(clean_content) > 300 else clean_content,
            'author': post.user.username,
            'author_name': f"{post.user.first_name} {post.user.last_name}".strip(),
            'created_at': post.created_at,
            'likes_count': post.likes.count(),
            'highlighted_content': _highlight_text(clean_content, query),
            'author_avatar': post.user.profile.avatar.url if hasattr(post.user, 'profile') and post.user.profile.avatar else None,
            'post_url': f'/feed/#post-{post.id}',
        }
        results.append(result)
    
    return results


def _highlight_user_matches(user, query):
    """Highlight matching terms in user fields."""
    highlighted = {}
    query_terms = query.lower().split()
    
    # Check username
    if any(term in user.username.lower() for term in query_terms):
        highlighted['username'] = _highlight_text(user.username, query)
    
    # Check full name
    full_name = f"{user.first_name} {user.last_name}".strip()
    if any(term in full_name.lower() for term in query_terms):
        highlighted['full_name'] = _highlight_text(full_name, query)
    
    # Check profile fields
    if hasattr(user, 'profile'):
        if user.profile.headline and any(term in user.profile.headline.lower() for term in query_terms):
            highlighted['headline'] = _highlight_text(user.profile.headline, query)
        
        if user.profile.location and any(term in user.profile.location.lower() for term in query_terms):
            highlighted['location'] = _highlight_text(user.profile.location, query)
    
    # Check experiences
    for exp in user.experiences.all()[:3]:  # Limit to recent experiences
        if any(term in exp.title.lower() or term in exp.company.lower() for term in query_terms):
            highlighted['experience'] = f"{_highlight_text(exp.title, query)} at {_highlight_text(exp.company, query)}"
            break
    
    return highlighted


def _highlight_job_matches(job, query):
    """Highlight matching terms in job fields."""
    highlighted = {}
    query_terms = query.lower().split()
    
    if any(term in job.title.lower() for term in query_terms):
        highlighted['title'] = _highlight_text(job.title, query)
    
    if any(term in job.company.lower() for term in query_terms):
        highlighted['company'] = _highlight_text(job.company, query)
    
    if any(term in job.description.lower() for term in query_terms):
        highlighted['description'] = _highlight_text(job.description[:200], query)
    
    return highlighted


def _highlight_text(text, query):
    """Highlight search terms in text."""
    if not text or not query:
        return text
    
    query_terms = query.split()
    highlighted_text = text
    
    for term in query_terms:
        if len(term) >= 2:  # Only highlight terms with 2+ characters
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted_text = pattern.sub(f'<mark class="bg-yellow-200 px-1 rounded">{term}</mark>', highlighted_text)
    
    return highlighted_text


def _generate_search_suggestions(query):
    """Generate search suggestions when no results are found."""
    suggestions = []
    
    # Common search terms and suggestions
    common_terms = {
        'developer': ['software developer', 'web developer', 'python developer'],
        'manager': ['project manager', 'product manager', 'engineering manager'],
        'designer': ['ui designer', 'ux designer', 'graphic designer'],
        'engineer': ['software engineer', 'data engineer', 'devops engineer'],
        'analyst': ['data analyst', 'business analyst', 'financial analyst'],
    }
    
    query_lower = query.lower()
    
    # Find similar terms
    for key, values in common_terms.items():
        if key in query_lower or any(word in query_lower for word in key.split()):
            suggestions.extend(values)
    
    # Get popular search terms from database (simplified)
    popular_titles = Job.objects.values_list('title', flat=True).distinct()[:10]
    popular_companies = Job.objects.values_list('company', flat=True).distinct()[:10]
    
    # Add some popular terms as suggestions
    suggestions.extend([title for title in popular_titles if query_lower not in title.lower()])
    suggestions.extend([company for company in popular_companies if query_lower not in company.lower()])
    
    # Remove duplicates and limit
    return list(set(suggestions))[:5]


@require_GET
def search_suggestions(request):
    """
    API endpoint for real-time search suggestions.
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    # Get user suggestions
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(profile__headline__icontains=query)
    ).select_related('profile')[:5]
    
    for user in users:
        suggestions.append({
            'type': 'person',
            'text': f"{user.first_name} {user.last_name}".strip() or user.username,
            'subtitle': user.profile.headline if hasattr(user, 'profile') else '',
            'url': f'/users/{user.username}/'
        })
    
    # Get job suggestions
    jobs = Job.objects.filter(
        Q(title__icontains=query) |
        Q(company__icontains=query),
        is_active=True
    )[:5]
    
    for job in jobs:
        suggestions.append({
            'type': 'job',
            'text': job.title,
            'subtitle': f"at {job.company}",
            'url': f'/jobs/{job.id}/'
        })
    
    # Get company suggestions
    companies = Job.objects.filter(
        company__icontains=query,
        is_active=True
    ).values_list('company', flat=True).distinct()[:3]
    
    for company in companies:
        suggestions.append({
            'type': 'company',
            'text': company,
            'subtitle': 'Company',
            'url': f'/search/?q={company}&type=jobs'
        })
    
    return JsonResponse({'suggestions': suggestions[:10]})


@require_GET
def csrf_token_refresh(request):
    """
    Endpoint to refresh CSRF token for long-lived pages
    """
    token = get_token(request)
    return JsonResponse({
        'csrf_token': token,
        'status': 'success'
    })

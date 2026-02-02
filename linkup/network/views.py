from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from .models import Connection, Follow

User = get_user_model()

@login_required
def send_request(request, user_id):
    friend = get_object_or_404(User, id=user_id)
    if friend != request.user:
        Connection.objects.get_or_create(user=request.user, friend=friend, status='pending')
    return redirect('network')

@login_required
def accept_request(request, request_id):
    connection = get_object_or_404(Connection, id=request_id, friend=request.user)
    connection.status = 'accepted'
    connection.save()
    return redirect('network')

@login_required
def reject_request(request, request_id):
    connection = get_object_or_404(Connection, id=request_id, friend=request.user)
    connection.delete()
    return redirect('network')

@login_required
def follow_user(request, user_id):
    followed_user = get_object_or_404(User, id=user_id)
    if followed_user != request.user:
        follow, created = Follow.objects.get_or_create(follower=request.user, followed=followed_user)
        if not created:
            follow.delete()
            is_following = False
        else:
            is_following = True
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'is_following': is_following})
            
    return redirect(request.META.get('HTTP_REFERER', 'network'))

@login_required
def toggle_connection(request, user_id):
    friend = get_object_or_404(User, id=user_id)
    if friend == request.user:
        return JsonResponse({'error': 'Cannot connect to yourself'}, status=400)
    
    connection = Connection.objects.filter(
        (Q(user=request.user) & Q(friend=friend)) | (Q(user=friend) & Q(friend=request.user))
    ).first()

    status = 'none'
    if connection:
        if connection.status == 'pending' and connection.user == request.user:
            connection.delete()
            status = 'none'
        elif connection.status == 'accepted':
            # Optionally handle disconnect, but let's keep it simple for now
            pass
    else:
        Connection.objects.create(user=request.user, friend=friend, status='pending')
        status = 'pending'

    return JsonResponse({'status': status})

@login_required
def network_view(request):
    from django.core.paginator import Paginator
    
    sent_requests = Connection.objects.filter(user=request.user, status='pending').select_related('friend').order_by('-created_at')
    received_requests = Connection.objects.filter(friend=request.user, status='pending').select_related('user').order_by('-created_at')
    connections = Connection.objects.filter(
        (Q(user=request.user) | Q(friend=request.user)) & Q(status='accepted')
    ).select_related('user', 'friend').order_by('-created_at')
    
    # Simple clear way to see who we can connect with (all users not me, not already connected)
    # This logic is a bit simplistic for scalability but works for MVP
    connected_users_ids = [c.friend.id for c in Connection.objects.filter(user=request.user)] + \
                          [c.user.id for c in Connection.objects.filter(friend=request.user)] + \
                          [request.user.id]

    suggestions = User.objects.exclude(id__in=connected_users_ids).select_related('profile')[:10]
    
    # Implement pagination for connections
    connections_paginator = Paginator(connections, 20)  # 20 connections per page
    page_number = request.GET.get('page')
    connections_page_obj = connections_paginator.get_page(page_number)
    
    # Check who the current user is following
    following_ids = set(Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True))
    for user in suggestions:
        user.is_followed = user.id in following_ids

    return render(request, 'network/index.html', {
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'connections_page_obj': connections_page_obj,
        'suggestions': suggestions,
        'total_connections': connections.count()
    })

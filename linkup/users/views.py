from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .forms import CustomUserCreationForm, UserUpdateForm, ProfileUpdateForm
from .models import User


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully. Welcome!')
            return redirect('feed')
        else:
            # Add ARIA attributes to fields that have errors for better screen reader support
            for field_name in form.errors:
                if field_name in form.fields:
                    widget = form.fields[field_name].widget
                    widget.attrs.update({
                        'aria-invalid': 'true',
                        'aria-describedby': f'id_{field_name}-error'
                    })
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'u_form': u_form, 'p_form': p_form})

@login_required
def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username)

    # Mutual connections: users who have accepted connections with both the viewer and profile_user
    from network.models import Connection

    def accepted_friends(u):
        qs1 = Connection.objects.filter(user=u, status='accepted').values_list('friend', flat=True)
        qs2 = Connection.objects.filter(friend=u, status='accepted').values_list('user', flat=True)
        ids = set(list(qs1) + list(qs2))
        return ids

    mutual_ids = set()
    try:
        viewer = request.user
        mutual_ids = accepted_friends(viewer) & accepted_friends(profile_user)
        # Exclude the viewer and profile_user themselves
        mutual_ids.discard(viewer.id)
        mutual_ids.discard(profile_user.id)
    except Exception:
        mutual_ids = set()

    from django.contrib.auth import get_user_model
    UserModel = get_user_model()
    mutual_connections = UserModel.objects.filter(id__in=list(mutual_ids))

    # Followers as Users (for avatars & tooltips)
    follower_users = [f.follower for f in profile_user.followers.all()[:20]]

    # Profile connections (other side of accepted connections)
    connections_qs = Connection.objects.filter((Q(user=profile_user) | Q(friend=profile_user)) & Q(status='accepted')).order_by('-created_at')
    profile_connections = []
    for conn in connections_qs:
        other = conn.friend if conn.user == profile_user else conn.user
        profile_connections.append({'user': other, 'created_at': conn.created_at})

    # Suggestions for the viewer (people you may know)
    connected_users_ids = [c.friend.id for c in Connection.objects.filter(user=request.user)] + [c.user.id for c in Connection.objects.filter(friend=request.user)] + [request.user.id]
    suggestions = UserModel.objects.exclude(id__in=connected_users_ids)[:5]

    # Check follow status
    from network.models import Follow
    following_ids = set(Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True))
    
    is_following_profile_user = profile_user.id in following_ids
    for user in suggestions:
        user.is_followed = user.id in following_ids

    return render(request, 'users/public_profile.html', {
        'profile_user': profile_user,
        'mutual_connections': mutual_connections,
        'follower_users': follower_users,
        'profile_connections': profile_connections,
        'suggestions': suggestions,
        'is_following_profile_user': is_following_profile_user,
    })


@login_required
def message_user(request, username):
    """Redirect to the messaging chat view"""
    target = get_object_or_404(User, username=username)
    if request.user == target:
        messages.warning(request, "You cannot message yourself.")
        return redirect('profile')
    return redirect('messaging:chat_view', username=target.username)


@login_required
def report_user(request, username):
    target = get_object_or_404(User, username=username)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        from .models import Report
        Report.objects.create(reporter=request.user, reported=target, reason=reason)
        messages.success(request, 'Thank you. The user has been reported and will be reviewed.')
        return redirect('public_profile', username=target.username)
    return render(request, 'users/report_user.html', {'target': target})


@login_required
def block_user(request, username):
    target = get_object_or_404(User, username=username)
    from .models import Block
    if request.method == 'POST':
        Block.objects.get_or_create(blocker=request.user, blocked=target)
        messages.success(request, f'User {target.username} has been blocked.')
        return redirect('public_profile', username=target.username)
    return render(request, 'users/block_user.html', {'target': target})

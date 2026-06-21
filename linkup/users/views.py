from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.forms import inlineformset_factory
from .forms import CustomUserCreationForm, UserUpdateForm, ProfileUpdateForm, ExperienceForm, EducationForm, SocialLinkForm
from .models import User, Experience, Education, SocialLink


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully. Welcome!')
            return redirect('feed:feed')
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
    ExperienceFormSet = inlineformset_factory(
        User, Experience,
        form=ExperienceForm,
        extra=1, can_delete=True,
        fields=['title', 'company', 'location', 'start_date', 'end_date', 'is_current', 'description']
    )
    EducationFormSet = inlineformset_factory(
        User, Education,
        form=EducationForm,
        extra=1, can_delete=True,
        fields=['school', 'degree', 'field_of_study', 'start_date', 'end_date', 'description']
    )
    SocialLinkFormSet = inlineformset_factory(
        User, SocialLink,
        form=SocialLinkForm,
        extra=1, can_delete=True,
        fields=['label', 'url', 'sort_order']
    )

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        exp_formset = ExperienceFormSet(request.POST, request.FILES, instance=request.user, prefix='exp')
        edu_formset = EducationFormSet(request.POST, request.FILES, instance=request.user, prefix='edu')
        social_formset = SocialLinkFormSet(request.POST, request.FILES, instance=request.user, prefix='social')
        if u_form.is_valid() and p_form.is_valid() and exp_formset.is_valid() and edu_formset.is_valid() and social_formset.is_valid():
            u_form.save()
            p_form.save()
            exp_formset.save()
            edu_formset.save()
            social_formset.save()
            messages.success(request, 'Profile saved successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
        exp_formset = ExperienceFormSet(instance=request.user, prefix='exp')
        edu_formset = EducationFormSet(instance=request.user, prefix='edu')
        social_formset = SocialLinkFormSet(instance=request.user, prefix='social')

    return render(request, 'users/profile.html', {
        'u_form': u_form,
        'p_form': p_form,
        'exp_formset': exp_formset,
        'edu_formset': edu_formset,
        'social_formset': social_formset,
    })

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

    # Connection status between viewer and profile_user
    connection_status = 'none'
    if request.user.is_authenticated and request.user != profile_user:
        conn = Connection.objects.filter(
            (Q(user=request.user) & Q(friend=profile_user)) |
            (Q(user=profile_user) & Q(friend=request.user))
        ).first()
        if conn:
            connection_status = conn.status

    # Profile strength percentage
    fields_filled = sum([
        bool(profile_user.profile.bio),
        bool(profile_user.profile.headline),
        profile_user.experiences.count() > 0,
        profile_user.educations.count() > 0,
    ])
    profile_strength = fields_filled * 25

    return render(request, 'users/public_profile.html', {
        'profile_user': profile_user,
        'mutual_connections': mutual_connections,
        'follower_users': follower_users,
        'profile_connections': profile_connections,
        'suggestions': suggestions,
        'profile_strength': profile_strength,
        'connection_status': connection_status,
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

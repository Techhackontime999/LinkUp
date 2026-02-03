from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from .models import Post, Comment
from .forms import PostForm, CommentForm

@login_required
def feed(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            return redirect('feed')
    else:
        form = PostForm()
    
    # Get all posts with pagination
    posts = Post.objects.select_related('user').prefetch_related('likes', 'comments').order_by('-created_at')
    
    # Implement pagination
    paginator = Paginator(posts, 10)  # Show 10 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'feed/index.html', {
        'page_obj': page_obj,
        'form': form,
        'total_posts': posts.count()
    })

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        is_liked = False
    else:
        post.likes.add(request.user)
        is_liked = True
    return JsonResponse({'likes_count': post.likes.count(), 'is_liked': is_liked})

@login_required
def add_comment(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get('content', '').strip()
        
        if content:
            comment = Comment.objects.create(
                post=post,
                user=request.user,
                content=content
            )
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'user': comment.user.username,
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
                    'is_owner': comment.user == request.user
                },
                'comments_count': post.total_comments()
            })
        else:
            return JsonResponse({'success': False, 'error': 'Comment cannot be empty'}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def get_comments(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.select_related('user').all()
    
    comments_data = [{
        'id': comment.id,
        'user': comment.user.username,
        'content': comment.content,
        'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
        'is_owner': comment.user == request.user
    } for comment in comments]
    
    return JsonResponse({
        'success': True,
        'comments': comments_data,
        'comments_count': len(comments_data)
    })

@login_required
def get_post_link(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post_url = request.build_absolute_uri(reverse('post_detail', args=[post_id]))
    return JsonResponse({'success': True, 'url': post_url})

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post.objects.select_related('user').prefetch_related('likes', 'comments'), id=post_id)
    comments = post.comments.select_related('user').all()
    
    return render(request, 'feed/post_detail.html', {
        'post': post,
        'comments': comments
    })

@login_required
def delete_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        
        # Check if the user owns the post
        if post.user != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to delete this post'}, status=403)
        
        # Delete the post
        post.delete()
        
        return JsonResponse({'success': True, 'message': 'Post deleted successfully'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def get_post_for_edit(request, post_id):
    """Get post data for editing"""
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the user owns the post
    if post.user != request.user:
        return JsonResponse({'success': False, 'error': 'You do not have permission to edit this post'}, status=403)
    
    return JsonResponse({
        'success': True,
        'post': {
            'id': post.id,
            'content': post.content,
            'image': post.image.url if post.image else None,
            'video': post.video.url if post.video else None,
            'audio': post.audio.url if post.audio else None,
            'pdf': post.pdf.url if post.pdf else None
        }
    })

@login_required
def update_post(request, post_id):
    """Update post content and/or image"""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        
        # Check if the user owns the post
        if post.user != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to edit this post'}, status=403)
        
        # Update content
        content = request.POST.get('content', '').strip()
        if content:
            # Wrap plain text in paragraph tags for consistency
            if not content.startswith('<'):
                content = f'<p>{content}</p>'
            post.content = content
        
        # Handle multimedia removals
        if request.POST.get('remove_image') == 'true':
            if post.image:
                post.image.delete()
                post.image = None
        if request.POST.get('remove_video') == 'true':
            if post.video:
                post.video.delete()
                post.video = None
        if request.POST.get('remove_audio') == 'true':
            if post.audio:
                post.audio.delete()
                post.audio = None
        if request.POST.get('remove_pdf') == 'true':
            if post.pdf:
                post.pdf.delete()
                post.pdf = None
        
        # Handle new multimedia uploads
        if 'image' in request.FILES:
            if post.image:
                post.image.delete()
            post.image = request.FILES['image']
        
        if 'video' in request.FILES:
            if post.video:
                post.video.delete()
            post.video = request.FILES['video']

        if 'audio' in request.FILES:
            if post.audio:
                post.audio.delete()
            post.audio = request.FILES['audio']

        if 'pdf' in request.FILES:
            if post.pdf:
                post.pdf.delete()
            post.pdf = request.FILES['pdf']
        
        post.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Post updated successfully',
            'post': {
                'id': post.id,
                'content': post.content,
                'image': post.image.url if post.image else None,
                'video': post.video.url if post.video else None,
                'audio': post.audio.url if post.audio else None,
                'pdf': post.pdf.url if post.pdf else None
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

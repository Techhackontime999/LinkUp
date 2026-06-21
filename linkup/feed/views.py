import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.conf import settings
from django.db.models import Prefetch
from .models import DocumentPage
from .models import Post, Comment, PostAttachment
from .forms import PostForm, CommentForm
from core.validators import AttachmentUploadValidator
from .document_processor import extract_pdf_pages

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt', '.csv'}


def _get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    if ext in AUDIO_EXTENSIONS:
        return 'audio'
    if ext in DOCUMENT_EXTENSIONS:
        return 'document'
    return 'document'


def _handle_post_attachments(post, files):
    if not files:
        return
    validator = AttachmentUploadValidator()
    sort_order = 0
    for f in files:
        try:
            validator(f)
        except ValidationError as e:
            raise ValidationError(f"{f.name}: {'; '.join(e.messages)}")
        file_type = _get_file_type(f.name)
        attachment = PostAttachment(post=post, file=f, file_type=file_type, sort_order=sort_order)
        attachment.save()
        sort_order += 1
        if file_type == 'document':
            extract_pdf_pages(attachment)


@login_required
def feed(request):
    form = PostForm()
    error_message = None
    posts = Post.objects.select_related('user').prefetch_related(
        'likes', 'comments',
        Prefetch('attachments', queryset=PostAttachment.objects.prefetch_related('pages'))
    ).order_by('-created_at')
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_count = posts.count()

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()

            multiple_files = request.FILES.getlist('attachments')
            if multiple_files:
                try:
                    _handle_post_attachments(post, multiple_files)
                except ValidationError as e:
                    post.delete()
                    error_message = '; '.join(e.messages)
                    form.add_error(None, error_message)
                    return render(request, 'feed/index.html', {
                        'page_obj': page_obj,
                        'form': form,
                        'total_posts': total_count,
                        'error_message': error_message
                    })
            return redirect('feed:feed')
    
    return render(request, 'feed/index.html', {
        'page_obj': page_obj,
        'form': form,
        'total_posts': total_count,
        'error_message': error_message
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
    post_url = request.build_absolute_uri(reverse('feed:post_detail', args=[post_id]))
    return JsonResponse({'success': True, 'url': post_url})

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('user').prefetch_related(
            'likes', 'comments',
            Prefetch('attachments', queryset=PostAttachment.objects.prefetch_related('pages'))
        ),
        id=post_id
    )
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
        
        # Delete attachment files from disk
        for att in post.attachments.all():
            if att.file:
                try:
                    att.file.delete(save=False)
                except Exception:
                    pass
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
    
    attachments = [{
        'id': att.id,
        'url': att.file.url,
        'type': att.file_type,
        'name': att.filename(),
        'size': att.file_size(),
        'sort_order': att.sort_order
    } for att in post.attachments.all()]

    return JsonResponse({
        'success': True,
        'post': {
            'id': post.id,
            'content': post.content,
            'image': post.image.url if post.image else None,
            'attachments': attachments
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
        
        # Handle image removal
        if request.POST.get('remove_image') == 'true':
            if post.image:
                post.image.delete()
                post.image = None
        
        # Handle new image upload
        if 'image' in request.FILES:
            # Delete old image if exists
            if post.image:
                post.image.delete()
            post.image = request.FILES['image']
        
        # Handle attachment removal
        remove_ids = request.POST.get('remove_attachment_ids', '')
        if remove_ids:
            ids = []
            for x in remove_ids.split(','):
                x = x.strip()
                if x.isdigit():
                    ids.append(int(x))
            if ids:
                PostAttachment.objects.filter(id__in=ids, post=post).delete()

        # Handle new attachment uploads
        multiple_files = request.FILES.getlist('attachments')
        if multiple_files:
            try:
                _handle_post_attachments(post, multiple_files)
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'error': '; '.join(e.messages)
                }, status=400)

        post.save()
        
        attachments = [{
            'id': att.id,
            'url': att.file.url,
            'type': att.file_type,
            'name': att.filename(),
            'size': att.file_size(),
            'sort_order': att.sort_order
        } for att in post.attachments.all()]

        return JsonResponse({
            'success': True,
            'message': 'Post updated successfully',
            'post': {
                'id': post.id,
                'content': post.content,
                'image': post.image.url if post.image else None,
                'attachments': attachments
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

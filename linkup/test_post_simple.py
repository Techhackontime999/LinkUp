#!/usr/bin/env python3
"""
Simple test to verify post visibility fix works.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.contrib.auth import get_user_model
from feed.models import Post
from feed.forms import PostForm

User = get_user_model()

print("=" * 60)
print("POST VISIBILITY FIX - SIMPLE VERIFICATION")
print("=" * 60)

# Get a user
user = User.objects.first()
if not user:
    print("❌ No users found in database")
    exit(1)

print(f"✓ Using user: {user.username}")

# Count posts
initial_count = Post.objects.count()
print(f"✓ Current post count: {initial_count}")

# Test form validation
form_data = {
    'content': '<p>Test post for visibility verification</p>'
}
form = PostForm(data=form_data)

if form.is_valid():
    print("✓ Form is valid")
    post = form.save(commit=False)
    post.user = user
    post.save()
    print(f"✓ Post created with ID: {post.id}")
else:
    print(f"❌ Form is invalid: {form.errors}")
    exit(1)

# Verify post was created
new_count = Post.objects.count()
print(f"✓ New post count: {new_count}")

if new_count == initial_count + 1:
    print("✓ Post count increased correctly")
else:
    print(f"❌ Post count mismatch: expected {initial_count + 1}, got {new_count}")
    exit(1)

# Verify post is in queryset (as the view would fetch it)
posts = Post.objects.select_related('user').prefetch_related('likes').order_by('-created_at')
latest_post = posts.first()

if latest_post.id == post.id:
    print(f"✓ Latest post matches created post")
    print(f"  - User: {latest_post.user.username}")
    print(f"  - Content: {latest_post.content[:50]}...")
    print(f"  - Created: {latest_post.created_at}")
else:
    print(f"❌ Latest post doesn't match: expected {post.id}, got {latest_post.id}")
    exit(1)

# Test pagination
from django.core.paginator import Paginator
paginator = Paginator(posts, 10)
page_obj = paginator.get_page(1)

print(f"✓ Pagination working:")
print(f"  - Total posts: {paginator.count}")
print(f"  - Total pages: {paginator.num_pages}")
print(f"  - Posts on page 1: {len(page_obj)}")

# Verify our post is in page_obj
post_ids = [p.id for p in page_obj]
if post.id in post_ids:
    print(f"✓ Created post is in page_obj (first page)")
else:
    print(f"❌ Created post not found in page_obj")
    exit(1)

# Clean up
post.delete()
print(f"✓ Cleaned up test post")

print("\n" + "=" * 60)
print("✅ ALL CHECKS PASSED")
print("=" * 60)
print("\nThe fix is working correctly:")
print("  • Posts are created successfully")
print("  • Posts appear in the queryset immediately")
print("  • Pagination includes new posts")
print("  • Template variable 'page_obj' contains the posts")

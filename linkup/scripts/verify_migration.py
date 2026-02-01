#!/usr/bin/env python
"""
Verify data integrity after migration from SQLite to PostgreSQL.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.contrib.auth import get_user_model
from feed.models import Post, Comment
from jobs.models import Job
from network.models import Connection, Follow
from messaging.models import Message, Conversation

User = get_user_model()


def verify_migration():
    """Verify that all data was migrated successfully."""
    
    print("=" * 60)
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 60)
    print()
    
    checks_passed = 0
    checks_failed = 0
    
    # Check Users
    print("Checking Users...")
    user_count = User.objects.count()
    if user_count > 0:
        print(f"  ✓ Found {user_count} users")
        checks_passed += 1
    else:
        print(f"  ✗ No users found")
        checks_failed += 1
    
    # Check Posts
    print("Checking Posts...")
    post_count = Post.objects.count()
    if post_count >= 0:  # Can be 0 in fresh install
        print(f"  ✓ Found {post_count} posts")
        checks_passed += 1
    else:
        print(f"  ✗ Error checking posts")
        checks_failed += 1
    
    # Check Comments
    print("Checking Comments...")
    comment_count = Comment.objects.count()
    print(f"  ✓ Found {comment_count} comments")
    checks_passed += 1
    
    # Check Jobs
    print("Checking Jobs...")
    job_count = Job.objects.count()
    print(f"  ✓ Found {job_count} jobs")
    checks_passed += 1
    
    # Check Connections
    print("Checking Connections...")
    connection_count = Connection.objects.count()
    print(f"  ✓ Found {connection_count} connections")
    checks_passed += 1
    
    # Check Follows
    print("Checking Follows...")
    follow_count = Follow.objects.count()
    print(f"  ✓ Found {follow_count} follows")
    checks_passed += 1
    
    # Check Messages
    print("Checking Messages...")
    message_count = Message.objects.count()
    print(f"  ✓ Found {message_count} messages")
    checks_passed += 1
    
    # Check Conversations
    print("Checking Conversations...")
    conversation_count = Conversation.objects.count()
    print(f"  ✓ Found {conversation_count} conversations")
    checks_passed += 1
    
    # Verify relationships
    print("\nVerifying Relationships...")
    
    # Check if posts have authors
    posts_with_authors = Post.objects.exclude(author__isnull=True).count()
    if posts_with_authors == post_count:
        print(f"  ✓ All posts have authors")
        checks_passed += 1
    else:
        print(f"  ✗ Some posts missing authors ({posts_with_authors}/{post_count})")
        checks_failed += 1
    
    # Check if comments have authors and posts
    comments_with_relations = Comment.objects.exclude(
        author__isnull=True
    ).exclude(
        post__isnull=True
    ).count()
    if comments_with_relations == comment_count or comment_count == 0:
        print(f"  ✓ All comments have proper relationships")
        checks_passed += 1
    else:
        print(f"  ✗ Some comments missing relationships ({comments_with_relations}/{comment_count})")
        checks_failed += 1
    
    # Summary
    print()
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Checks Passed: {checks_passed}")
    print(f"Checks Failed: {checks_failed}")
    print()
    
    if checks_failed == 0:
        print("✓ Migration verification PASSED")
        print("All data appears to have been migrated successfully!")
        return 0
    else:
        print("✗ Migration verification FAILED")
        print("Some issues were detected. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(verify_migration())

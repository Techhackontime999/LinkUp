#!/usr/bin/env python3
"""
Generate and apply database migrations for AI Agent Social Platform models
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

def generate_migrations():
    """Generate migrations for social models"""
    try:
        print("🔄 Generating migrations for AI Agent Social Platform...")
        
        # Generate migrations
        execute_from_command_line(['manage.py', 'makemigrations', 'ai_agents'])
        
        print("✅ Migrations generated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def apply_migrations():
    """Apply the generated migrations"""
    try:
        print("🔄 Applying migrations...")
        
        # Apply migrations
        execute_from_command_line(['manage.py', 'migrate', 'ai_agents'])
        
        print("✅ Migrations applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration application failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AI Agent Social Platform - Database Migration")
    print("=" * 60)
    
    # Step 1: Generate migrations
    if not generate_migrations():
        print("\n⚠️  Migration generation failed. Please check the errors above.")
        sys.exit(1)
    
    print()
    
    # Step 2: Apply migrations
    if not apply_migrations():
        print("\n⚠️  Migration application failed. Please check the errors above.")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ All migrations completed successfully!")
    print("=" * 60)
    print("\nThe following models have been added to the database:")
    print("  • AgentSocialProfile - Social profiles for agents")
    print("  • AgentPost - Posts created by agents")
    print("  • AgentFollow - Follow relationships")
    print("  • AgentReaction - Reactions to posts and comments")
    print("  • AgentComment - Comments on posts")
    print("  • AgentCollaborationSpace - Group collaboration spaces")
    print("  • SpaceMembership - Space membership tracking")
    print("  • AgentCapabilityListing - Marketplace listings")
    print("  • AgentNotification - Notification system")
    print("  • AgentReputation - Reputation tracking")
    print()
    
    sys.exit(0)

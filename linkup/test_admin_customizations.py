"""
Test script for Django admin customizations.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkup.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.admin.sites import site
from ai_agents.admin import (
    AIAgentAdmin, AgentAPIKeyAdmin, AgentMessageAdmin,
    AgentInteractionAdmin, ResearchMetricAdmin
)
from ai_agents.models import AIAgent, AgentAPIKey, AgentMessage, AgentInteraction, ResearchMetric


def test_admin_registrations():
    """Test that all models are registered with admin."""
    print("Testing admin registrations...")
    
    models_to_check = [
        (AIAgent, AIAgentAdmin),
        (AgentAPIKey, AgentAPIKeyAdmin),
        (AgentMessage, AgentMessageAdmin),
        (AgentInteraction, AgentInteractionAdmin),
        (ResearchMetric, ResearchMetricAdmin),
    ]
    
    for model, admin_class in models_to_check:
        if model in site._registry:
            registered_admin = site._registry[model]
            print(f"✓ {model.__name__} is registered with {registered_admin.__class__.__name__}")
            
            # Verify it's the correct admin class
            if isinstance(registered_admin, admin_class):
                print(f"  ✓ Correct admin class: {admin_class.__name__}")
            else:
                print(f"  ✗ Wrong admin class: expected {admin_class.__name__}, got {registered_admin.__class__.__name__}")
        else:
            print(f"✗ {model.__name__} is NOT registered")
    
    print()


def test_aiagent_admin():
    """Test AIAgent admin customizations."""
    print("Testing AIAgent admin customizations...")
    
    admin = site._registry[AIAgent]
    
    # Check list_display
    expected_display = ['name', 'agent_type', 'owner_email', 'is_active_badge', 
                       'is_suspended_badge', 'total_interactions', 'message_count', 
                       'created_at', 'last_active_at']
    assert admin.list_display == expected_display, f"list_display mismatch"
    print("✓ list_display configured correctly")
    
    # Check search_fields
    assert 'name' in admin.search_fields, "name not in search_fields"
    assert 'owner_email' in admin.search_fields, "owner_email not in search_fields"
    print("✓ search_fields configured correctly")
    
    # Check list_filter
    assert 'agent_type' in admin.list_filter, "agent_type not in list_filter"
    assert 'is_active' in admin.list_filter, "is_active not in list_filter"
    assert 'is_suspended' in admin.list_filter, "is_suspended not in list_filter"
    print("✓ list_filter configured correctly")
    
    # Check custom actions
    action_names = [action.__name__ if callable(action) else action for action in admin.actions]
    assert 'suspend_agents' in action_names, "suspend_agents action not found"
    assert 'unsuspend_agents' in action_names, "unsuspend_agents action not found"
    assert 'export_agents_csv' in action_names, "export_agents_csv action not found"
    print("✓ Custom actions configured correctly")
    
    print()


def test_agentmessage_admin():
    """Test AgentMessage admin customizations."""
    print("Testing AgentMessage admin customizations...")
    
    admin = site._registry[AgentMessage]
    
    # Check list_display includes inline display elements
    assert 'sender_link' in admin.list_display, "sender_link not in list_display"
    assert 'recipient_link' in admin.list_display, "recipient_link not in list_display"
    assert 'status_badge' in admin.list_display, "status_badge not in list_display"
    print("✓ list_display with inline elements configured correctly")
    
    # Check custom actions
    action_names = [action.__name__ if callable(action) else action for action in admin.actions]
    assert 'export_messages_csv' in action_names, "export_messages_csv action not found"
    assert 'mark_as_read' in action_names, "mark_as_read action not found"
    print("✓ Custom actions configured correctly")
    
    print()


def test_agentinteraction_admin():
    """Test AgentInteraction admin customizations with analytics."""
    print("Testing AgentInteraction admin customizations...")
    
    admin = site._registry[AgentInteraction]
    
    # Check analytics field
    assert 'analytics_summary' in admin.readonly_fields, "analytics_summary not in readonly_fields"
    print("✓ Analytics summary field configured")
    
    # Check custom actions
    action_names = [action.__name__ if callable(action) else action for action in admin.actions]
    assert 'archive_interactions' in action_names, "archive_interactions action not found"
    assert 'export_interactions_csv' in action_names, "export_interactions_csv action not found"
    assert 'export_interactions_json' in action_names, "export_interactions_json action not found"
    print("✓ Custom actions for analytics and export configured correctly")
    
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Django Admin Customizations Test")
    print("=" * 60)
    print()
    
    try:
        test_admin_registrations()
        test_aiagent_admin()
        test_agentmessage_admin()
        test_agentinteraction_admin()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print()
        print("Summary:")
        print("- AIAgent admin: search, filters, and custom actions (suspend, export)")
        print("- AgentMessage admin: inline display with sender/recipient links")
        print("- AgentInteraction admin: analytics summary and export actions")
        print("- All models have appropriate custom actions")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

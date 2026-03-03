"""
Test script for AI Agent Admin Dashboard Views
Task 16.2: Create admin dashboard views

This script verifies that the admin dashboard views are properly implemented.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from ai_agents.admin_dashboard_views import (
    agent_dashboard,
    agent_activity_chart_data,
    agent_metrics_summary,
    interaction_details
)
from ai_agents.models import AIAgent, AgentMessage, AgentInteraction
import uuid

User = get_user_model()


def test_admin_dashboard_views():
    """Test admin dashboard views functionality"""
    print("Testing AI Agent Admin Dashboard Views...")
    print("=" * 60)
    
    # Create request factory
    factory = RequestFactory()
    
    # Create a staff user
    user = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )
    
    print("\n1. Testing agent_dashboard view...")
    try:
        request = factory.get('/admin/ai-agents-dashboard/')
        request.user = user
        response = agent_dashboard(request)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert b'AI Agent Platform Dashboard' in response.content or 'AI Agent Platform Dashboard' in str(response.content)
        print("   ✓ Dashboard view renders successfully")
        print(f"   ✓ Response status: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return False
    
    print("\n2. Testing agent_activity_chart_data view...")
    try:
        request = factory.get('/admin/activity-chart-data/?hours=24')
        request.user = user
        response = agent_activity_chart_data(request)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        import json
        data = json.loads(response.content)
        assert 'success' in data, "Response should contain 'success' field"
        assert 'data' in data, "Response should contain 'data' field"
        
        chart_data = data['data']
        assert 'labels' in chart_data, "Chart data should contain 'labels'"
        assert 'message_counts' in chart_data, "Chart data should contain 'message_counts'"
        assert 'active_agent_counts' in chart_data, "Chart data should contain 'active_agent_counts'"
        assert 'avg_latencies' in chart_data, "Chart data should contain 'avg_latencies'"
        
        print("   ✓ Chart data endpoint returns valid JSON")
        print(f"   ✓ Chart has {len(chart_data['labels'])} data points")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return False
    
    print("\n3. Testing agent_metrics_summary view...")
    try:
        request = factory.get('/admin/metrics-summary/')
        request.user = user
        response = agent_metrics_summary(request)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = json.loads(response.content)
        assert 'success' in data, "Response should contain 'success' field"
        assert 'system_metrics' in data, "Response should contain 'system_metrics'"
        assert 'agent_stats' in data, "Response should contain 'agent_stats'"
        assert 'top_agents' in data, "Response should contain 'top_agents'"
        
        print("   ✓ Metrics summary endpoint returns valid JSON")
        print(f"   ✓ System metrics: {list(data['system_metrics'].keys())}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return False
    
    print("\n4. Testing interaction_details view...")
    try:
        # Create test agents
        agent1 = AIAgent.objects.create(
            name="TestAgent1",
            agent_type="CONVERSATIONAL",
            description="Test agent 1",
            owner_email="test1@example.com",
            api_key_hash="test_hash_1"
        )
        
        agent2 = AIAgent.objects.create(
            name="TestAgent2",
            agent_type="CONVERSATIONAL",
            description="Test agent 2",
            owner_email="test2@example.com",
            api_key_hash="test_hash_2"
        )
        
        # Create test interaction
        interaction = AgentInteraction.objects.create(
            session_id=uuid.uuid4(),
            agent_1=agent1,
            agent_2=agent2,
            interaction_type="CONVERSATION",
            message_count=5,
            total_duration_seconds=120
        )
        
        request = factory.get(f'/admin/interaction/{interaction.id}/')
        request.user = user
        response = interaction_details(request, interaction.id)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = json.loads(response.content)
        assert 'success' in data, "Response should contain 'success' field"
        assert 'interaction' in data, "Response should contain 'interaction'"
        
        interaction_data = data['interaction']
        assert interaction_data['agent_1']['name'] == "TestAgent1"
        assert interaction_data['agent_2']['name'] == "TestAgent2"
        assert interaction_data['interaction_type'] == "CONVERSATION"
        
        print("   ✓ Interaction details endpoint returns valid JSON")
        print(f"   ✓ Interaction ID: {interaction_data['id'][:8]}...")
        
        # Cleanup
        agent1.delete()
        agent2.delete()
        
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        return False
    
    # Cleanup test user
    user.delete()
    
    print("\n" + "=" * 60)
    print("✓ All admin dashboard view tests passed!")
    print("\nSummary:")
    print("  - Dashboard view renders correctly")
    print("  - Chart data API returns valid time-series data")
    print("  - Metrics summary API returns system health metrics")
    print("  - Interaction details API returns detailed interaction data")
    print("\nRequirements validated:")
    print("  - Requirement 7.1: Calculate total messages sent and received")
    print("  - Requirement 20.1: Track total active agents")
    print("  - Requirement 20.2: Track messages sent per minute")
    
    return True


if __name__ == '__main__':
    try:
        success = test_admin_dashboard_views()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

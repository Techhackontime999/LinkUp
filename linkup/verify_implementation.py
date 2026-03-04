"""
Verification script to check which AI Agent platform features are implemented and in use.

This script checks:
1. REST API endpoints
2. WebSocket support
3. Rate limiting middleware
4. Security features
5. Analytics engine
6. Health monitoring
7. Admin dashboard
8. Documentation
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.urls import get_resolver
from django.conf import settings
from ai_agents.models import AIAgent, AgentMessage, AgentInteraction, AgentAPIKey
from ai_agents.services import AgentRegistryService, AgentAuthenticationService, AgentCommunicationService
from ai_agents.analytics_engine import ResearchAnalyticsEngine
from ai_agents.middleware import AgentRateLimitMiddleware, AgentAuthenticationMiddleware, CorrelationIdMiddleware


def check_rest_api_endpoints():
    """Check if REST API endpoints are registered."""
    print("\n" + "="*80)
    print("1. REST API ENDPOINTS")
    print("="*80)
    
    resolver = get_resolver()
    ai_agent_urls = []
    
    for pattern in resolver.url_patterns:
        if hasattr(pattern, 'namespace') and pattern.namespace == 'ai_agents':
            for url_pattern in pattern.url_patterns:
                if hasattr(url_pattern, 'name'):
                    ai_agent_urls.append({
                        'name': url_pattern.name,
                        'pattern': str(url_pattern.pattern)
                    })
    
    print(f"\n✓ Found {len(ai_agent_urls)} AI Agent API endpoints")
    
    # Group by category
    categories = {
        'Authentication': ['register', 'authenticate', 'token_refresh'],
        'Profile Management': ['profile_get', 'profile_update', 'profile_delete', 'suspend', 'unsuspend'],
        'Discovery': ['agent_list'],
        'Messaging': ['message_send', 'message_list', 'conversation_history', 'message_mark_read'],
        'Analytics': ['agent_metrics', 'interactions_query', 'data_export', 'data_anonymize'],
        'API Keys': ['api_key_create', 'api_key_list', 'api_key_delete'],
        'Health Monitoring': ['system_health', 'check_thresholds', 'get_alerts', 'acknowledge_alert'],
        'Admin Dashboard': ['admin_dashboard', 'activity_chart_data', 'metrics_summary', 'interaction_details'],
        'AI Model Management': ['ai_model_management', 'add_ai_model', 'ai_model_detail', 'edit_ai_model', 
                                'toggle_ai_model_status', 'delete_ai_model', 'generate_api_key', 'revoke_api_key'],
        'Multi-Agent': ['multi_agent_chat', 'ask_multiple_agents', 'agent_discussion', 'build_consensus'],
        'Communication UI': ['agent_communication', 'ai_social_demo'],
    }
    
    for category, endpoint_names in categories.items():
        found = [url for url in ai_agent_urls if any(name in url['name'] for name in endpoint_names)]
        status = "✓" if found else "✗"
        print(f"\n{status} {category}: {len(found)} endpoints")
        if found:
            for url in found[:3]:  # Show first 3
                print(f"   - {url['name']}: /api/{url['pattern']}")
            if len(found) > 3:
                print(f"   ... and {len(found) - 3} more")
    
    return len(ai_agent_urls) > 0


def check_websocket_support():
    """Check if WebSocket consumers are configured."""
    print("\n" + "="*80)
    print("2. WEBSOCKET SUPPORT")
    print("="*80)
    
    try:
        from ai_agents.consumers import AgentConsumer
        from ai_agents.routing import websocket_urlpatterns
        
        print(f"\n✓ AgentConsumer class found")
        print(f"✓ WebSocket routing configured with {len(websocket_urlpatterns)} patterns")
        
        for pattern in websocket_urlpatterns:
            print(f"   - {pattern.pattern}")
        
        # Check if channels is installed
        try:
            import channels
            print(f"✓ Django Channels installed (version {channels.__version__})")
        except ImportError:
            print("✗ Django Channels not installed")
            return False
        
        # Check ASGI configuration
        if hasattr(settings, 'ASGI_APPLICATION'):
            print(f"✓ ASGI application configured: {settings.ASGI_APPLICATION}")
        else:
            print("✗ ASGI application not configured")
            return False
        
        # Check channel layers
        if hasattr(settings, 'CHANNEL_LAYERS'):
            print(f"✓ Channel layers configured")
        else:
            print("✗ Channel layers not configured")
            return False
        
        return True
        
    except ImportError as e:
        print(f"✗ WebSocket support not found: {e}")
        return False


def check_middleware():
    """Check if security middleware is configured."""
    print("\n" + "="*80)
    print("3. SECURITY MIDDLEWARE")
    print("="*80)
    
    middleware_classes = settings.MIDDLEWARE
    
    required_middleware = {
        'Rate Limiting': 'ai_agents.middleware.AgentRateLimitMiddleware',
        'Authentication': 'ai_agents.middleware.AgentAuthenticationMiddleware',
        'Correlation ID': 'ai_agents.middleware.CorrelationIdMiddleware',
        'Metrics Tracking': 'ai_agents.middleware.MetricsTrackingMiddleware',
    }
    
    all_found = True
    for name, middleware_path in required_middleware.items():
        if middleware_path in middleware_classes:
            print(f"✓ {name} middleware configured")
        else:
            print(f"✗ {name} middleware NOT configured")
            all_found = False
    
    return all_found


def check_services():
    """Check if core services are implemented."""
    print("\n" + "="*80)
    print("4. CORE SERVICES")
    print("="*80)
    
    services = {
        'Agent Registry': AgentRegistryService,
        'Agent Authentication': AgentAuthenticationService,
        'Agent Communication': AgentCommunicationService,
        'Research Analytics': ResearchAnalyticsEngine,
    }
    
    for name, service_class in services.items():
        try:
            # Check if service has required methods
            methods = [method for method in dir(service_class) if not method.startswith('_')]
            print(f"✓ {name} service: {len(methods)} public methods")
        except Exception as e:
            print(f"✗ {name} service error: {e}")
            return False
    
    return True


def check_models():
    """Check if database models are configured."""
    print("\n" + "="*80)
    print("5. DATABASE MODELS")
    print("="*80)
    
    models = {
        'AIAgent': AIAgent,
        'AgentMessage': AgentMessage,
        'AgentInteraction': AgentInteraction,
        'AgentAPIKey': AgentAPIKey,
    }
    
    for name, model_class in models.items():
        try:
            count = model_class.objects.count()
            print(f"✓ {name} model: {count} records")
        except Exception as e:
            print(f"✗ {name} model error: {e}")
            return False
    
    return True


def check_analytics():
    """Check if analytics engine is functional."""
    print("\n" + "="*80)
    print("6. ANALYTICS ENGINE")
    print("="*80)
    
    try:
        # Check if analytics methods exist
        methods = [
            'calculate_metrics',
            'analyze_interaction_patterns',
            'generate_insights',
            'export_research_data',
        ]
        
        for method in methods:
            if hasattr(ResearchAnalyticsEngine, method):
                print(f"✓ {method} method implemented")
            else:
                print(f"✗ {method} method NOT found")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Analytics engine error: {e}")
        return False


def check_health_monitoring():
    """Check if health monitoring is configured."""
    print("\n" + "="*80)
    print("7. HEALTH MONITORING")
    print("="*80)
    
    try:
        from ai_agents.alerting_service import AlertingService
        from ai_agents.metrics_tracker import SystemMetricsTracker
        
        print("✓ AlertingService found")
        print("✓ SystemMetricsTracker found")
        
        # Check if health endpoint exists
        resolver = get_resolver()
        health_endpoints = []
        
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'namespace') and pattern.namespace == 'ai_agents':
                for url_pattern in pattern.url_patterns:
                    if hasattr(url_pattern, 'name') and 'health' in url_pattern.name:
                        health_endpoints.append(url_pattern.name)
        
        print(f"✓ Found {len(health_endpoints)} health monitoring endpoints")
        for endpoint in health_endpoints:
            print(f"   - {endpoint}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Health monitoring not found: {e}")
        return False


def check_admin_dashboard():
    """Check if admin dashboard is configured."""
    print("\n" + "="*80)
    print("8. ADMIN DASHBOARD")
    print("="*80)
    
    try:
        from ai_agents import admin_dashboard_views, admin_ai_model_views
        
        print("✓ Admin dashboard views found")
        print("✓ AI model management views found")
        
        # Check templates
        template_dir = os.path.join(os.path.dirname(__file__), 'templates', 'ai_agents')
        if os.path.exists(template_dir):
            templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
            print(f"✓ Found {len(templates)} admin templates")
            for template in templates[:5]:
                print(f"   - {template}")
            if len(templates) > 5:
                print(f"   ... and {len(templates) - 5} more")
        else:
            print("✗ Admin templates directory not found")
            return False
        
        return True
        
    except ImportError as e:
        print(f"✗ Admin dashboard not found: {e}")
        return False


def check_documentation():
    """Check if documentation exists."""
    print("\n" + "="*80)
    print("9. DOCUMENTATION")
    print("="*80)
    
    docs = {
        'API Documentation': 'AI_PLATFORM_GUIDE.md',
        'Quick Start': 'AI_QUICK_START.md',
        'API Usage Guide': 'ai_agents/API_USAGE_GUIDE.md',
        'Admin Guide': 'AI_ADMIN_PRODUCTION_GUIDE.md',
        'Deployment Checklist': 'PRODUCTION_DEPLOYMENT_CHECKLIST.md',
    }
    
    base_dir = os.path.dirname(__file__)
    all_found = True
    
    for name, doc_path in docs.items():
        full_path = os.path.join(base_dir, doc_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✓ {name}: {size:,} bytes")
        else:
            print(f"✗ {name} NOT found: {doc_path}")
            all_found = False
    
    return all_found


def generate_summary():
    """Generate implementation summary."""
    print("\n" + "="*80)
    print("IMPLEMENTATION SUMMARY")
    print("="*80)
    
    results = {
        'REST API Endpoints': check_rest_api_endpoints(),
        'WebSocket Support': check_websocket_support(),
        'Security Middleware': check_middleware(),
        'Core Services': check_services(),
        'Database Models': check_models(),
        'Analytics Engine': check_analytics(),
        'Health Monitoring': check_health_monitoring(),
        'Admin Dashboard': check_admin_dashboard(),
        'Documentation': check_documentation(),
    }
    
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    implemented = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (implemented / total) * 100
    
    for feature, status in results.items():
        status_icon = "✓" if status else "✗"
        status_text = "IMPLEMENTED" if status else "NOT CONFIGURED"
        print(f"{status_icon} {feature}: {status_text}")
    
    print(f"\n{'='*80}")
    print(f"OVERALL: {implemented}/{total} features implemented ({percentage:.1f}%)")
    print(f"{'='*80}\n")
    
    if percentage == 100:
        print("🎉 All features are implemented and configured!")
    elif percentage >= 80:
        print("⚠️  Most features are implemented. Review missing items above.")
    else:
        print("❌ Several features need configuration. Review the report above.")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("AI AGENT PLATFORM - IMPLEMENTATION VERIFICATION")
    print("="*80)
    
    try:
        generate_summary()
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()

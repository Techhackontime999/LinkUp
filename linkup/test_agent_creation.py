"""
Test script to manually create an AI agent and diagnose issues.
Run with: python manage.py shell < test_agent_creation.py
"""
import secrets
import hashlib
from ai_agents.models import AIAgent, AgentAPIKey
from ai_agents.social_models import AgentSocialProfile

print("\n=== Testing AI Agent Creation ===\n")

try:
    # Test data
    name = "TestAgent123"
    description = "Test agent for debugging"
    agent_type = "CONVERSATIONAL"
    version = "1.0.0"
    owner_email = "test@example.com"
    
    # Generate API key
    api_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Capabilities
    capabilities = {
        'nlp': True,
        'reasoning': False,
        'code_generation': False,
        'data_analysis': False,
        'image_generation': False,
        'multimodal': False,
    }
    
    # Metadata
    metadata = {
        'provider': 'google',
        'endpoint_url': 'https://api.example.com',
        'api_key': 'test_provider_key_123'
    }
    
    print("Step 1: Creating AI Agent...")
    agent = AIAgent.objects.create(
        name=name,
        description=description,
        agent_type=agent_type,
        capabilities=capabilities,
        version=version,
        owner_email=owner_email,
        api_key_hash=key_hash,
        metadata=metadata,
        is_active=True,
        is_suspended=False
    )
    print(f"✓ Agent created: {agent.id}")
    
    print("\nStep 2: Creating API Key record...")
    api_key_record = AgentAPIKey.objects.create(
        agent=agent,
        key_hash=key_hash,
        key_prefix=api_key[:8],
        name=f"{name} API Key",
        is_active=True
    )
    print(f"✓ API Key record created: {api_key_record.id}")
    
    print("\nStep 3: Creating Social Profile...")
    social_profile = AgentSocialProfile.objects.create(
        agent=agent,
        display_name=name,
        bio=description,
        tags=['test', 'debug'],
        is_public=True,
        is_verified=True
    )
    print(f"✓ Social Profile created: {social_profile.id}")
    
    print("\n=== SUCCESS ===")
    print(f"Agent ID: {agent.id}")
    print(f"Agent Name: {agent.name}")
    print(f"Is Active: {agent.is_active}")
    print(f"Is Suspended: {agent.is_suspended}")
    print(f"Metadata: {agent.metadata}")
    
    print("\n=== Verification ===")
    # Check if agent shows up in queries
    all_agents = AIAgent.objects.all().count()
    active_agents = AIAgent.objects.filter(is_active=True, is_suspended=False).count()
    print(f"Total agents in DB: {all_agents}")
    print(f"Active agents (should show in admin): {active_agents}")
    
except Exception as e:
    import traceback
    print("\n=== ERROR ===")
    print(f"Error: {str(e)}")
    print("\nFull traceback:")
    print(traceback.format_exc())

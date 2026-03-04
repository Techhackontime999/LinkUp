"""
Test script for Gemini AI agent integration

This script tests:
1. Gemini provider loading
2. API key validation
3. Response generation
4. Error handling
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model, GeminiProvider


def test_gemini_direct():
    """Test Gemini provider directly with API key"""
    print("\n" + "="*80)
    print("TEST 1: Direct Gemini Provider Test")
    print("="*80)
    
    # Get API key from environment or prompt
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("\n⚠️  No GEMINI_API_KEY environment variable found")
        api_key = input("Enter your Gemini API key (or press Enter to skip): ").strip()
        
        if not api_key:
            print("❌ Skipping direct test - no API key provided")
            return False
    
    try:
        # Create provider
        provider = GeminiProvider(api_key=api_key, model='gemini-pro')
        print(f"✅ Gemini provider created")
        print(f"   Model: gemini-pro")
        
        # Test generation
        print("\n🤖 Testing Gemini response...")
        response = provider.generate_response(
            prompt="Say 'Hello, I am Gemini!' in one sentence.",
            max_tokens=50,
            temperature=0.7
        )
        
        print(f"\n📝 Gemini Response:")
        print(f"   {response}")
        
        # Check if response is valid
        if response and not response.startswith("I'm having trouble"):
            print("\n✅ Direct test PASSED!")
            return True
        else:
            print("\n❌ Direct test FAILED - Invalid response")
            return False
            
    except Exception as e:
        print(f"\n❌ Direct test FAILED: {str(e)}")
        return False


def test_gemini_agent():
    """Test Gemini agent from database"""
    print("\n" + "="*80)
    print("TEST 2: Gemini Agent Test")
    print("="*80)
    
    try:
        # Try to find a Gemini agent
        agents = AIAgent.objects.filter(
            metadata__provider='gemini',
            is_active=True
        )
        
        if not agents.exists():
            print("\n⚠️  No Gemini agents found in database")
            print("\nTo create a Gemini agent:")
            print("1. Go to http://localhost:8000/api/admin/")
            print("2. Click 'Add New Model'")
            print("3. Fill in the form with Gemini configuration")
            print("\nOr use the API:")
            print("   curl -X POST http://localhost:8000/api/agents/register \\")
            print("     -H 'Content-Type: application/json' \\")
            print("     -d '{")
            print('       "name": "GeminiBot",')
            print('       "description": "AI agent powered by Google Gemini",')
            print('       "capabilities": {"language": "en", "provider": "gemini"},')
            print('       "owner_email": "your-email@example.com",')
            print('       "agent_type": "CONVERSATIONAL",')
            print('       "metadata": {')
            print('         "provider": "gemini",')
            print('         "api_key": "YOUR_GEMINI_API_KEY",')
            print('         "model": "gemini-pro"')
            print("       }")
            print("     }'")
            return False
        
        # Test first Gemini agent
        agent = agents.first()
        print(f"\n✅ Found Gemini agent: {agent.name}")
        print(f"   ID: {agent.id}")
        print(f"   Type: {agent.agent_type}")
        print(f"   Created: {agent.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Check metadata
        metadata = agent.metadata or {}
        print(f"\n📋 Agent Configuration:")
        print(f"   Provider: {metadata.get('provider', 'Not set')}")
        print(f"   Model: {metadata.get('model', 'Not set')}")
        print(f"   API Key: {'Set' if metadata.get('api_key') else 'Not set'}")
        
        if not metadata.get('api_key'):
            print("\n❌ Agent test FAILED - No API key in metadata")
            print("\nUpdate agent metadata to include:")
            print('   "api_key": "YOUR_GEMINI_API_KEY"')
            return False
        
        # Get provider
        print("\n🔌 Loading Gemini provider...")
        provider = get_provider_for_model(agent)
        
        if not provider:
            print("❌ Agent test FAILED - Could not load provider")
            return False
        
        print("✅ Provider loaded successfully")
        
        # Test generation
        print("\n🤖 Testing Gemini response...")
        response = provider.generate_response(
            prompt="Tell me a fun fact about AI in one sentence.",
            max_tokens=100,
            temperature=0.7
        )
        
        print(f"\n📝 Gemini Response:")
        print(f"   {response}")
        
        # Check if response is valid
        if response and not response.startswith("I'm having trouble"):
            print("\n✅ Agent test PASSED!")
            return True
        else:
            print("\n❌ Agent test FAILED - Invalid response")
            return False
            
    except Exception as e:
        print(f"\n❌ Agent test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_requests():
    """Test multiple requests to check rate limiting"""
    print("\n" + "="*80)
    print("TEST 3: Multiple Requests Test")
    print("="*80)
    
    try:
        # Find Gemini agent
        agents = AIAgent.objects.filter(
            metadata__provider='gemini',
            is_active=True
        )
        
        if not agents.exists():
            print("\n⚠️  Skipping - No Gemini agents found")
            return False
        
        agent = agents.first()
        provider = get_provider_for_model(agent)
        
        if not provider:
            print("\n❌ Could not load provider")
            return False
        
        print(f"\n🔄 Sending 3 requests to test rate limiting...")
        
        prompts = [
            "What is 2+2?",
            "Name a color.",
            "Say hello."
        ]
        
        for i, prompt in enumerate(prompts, 1):
            print(f"\n   Request {i}: {prompt}")
            response = provider.generate_response(
                prompt=prompt,
                max_tokens=50,
                temperature=0.5
            )
            print(f"   Response: {response[:100]}...")
        
        print("\n✅ Multiple requests test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Multiple requests test FAILED: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("GEMINI AI AGENT - INTEGRATION TEST")
    print("="*80)
    print("\nThis script will test your Gemini integration:")
    print("1. Direct API test (with API key)")
    print("2. Agent database test")
    print("3. Multiple requests test")
    
    results = {
        'direct': False,
        'agent': False,
        'multiple': False
    }
    
    # Run tests
    results['direct'] = test_gemini_direct()
    results['agent'] = test_gemini_agent()
    
    if results['agent']:
        results['multiple'] = test_multiple_requests()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.upper()}: {status}")
    
    print(f"\n{'='*80}")
    print(f"OVERALL: {passed}/{total} tests passed")
    print(f"{'='*80}")
    
    if passed == total:
        print("\n🎉 All tests passed! Gemini integration is working!")
        print("\nNext steps:")
        print("1. Build your chat application")
        print("2. Create API endpoints")
        print("3. Monitor usage and errors")
    elif results['agent']:
        print("\n✅ Gemini agent is working!")
        print("\nYou can now use it in your application.")
    else:
        print("\n⚠️  Some tests failed. Review the errors above.")
        print("\nCommon issues:")
        print("- Invalid API key")
        print("- No Gemini agent configured")
        print("- Network connectivity issues")
        print("\nCheck GEMINI_INTEGRATION_GUIDE.md for help")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

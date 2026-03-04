"""
Test all AI providers integration

This script tests all 5 AI providers:
1. Google Gemini
2. OpenAI ChatGPT
3. Anthropic Claude
4. Hugging Face
5. Cohere
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from ai_agents.models import AIAgent
from ai_agents.ai_providers import (
    get_provider_for_model,
    GeminiProvider,
    OpenAIProvider,
    AnthropicProvider,
    HuggingFaceProvider,
    CohereProvider
)


def test_provider_direct(provider_class, api_key, provider_name, model=None):
    """Test provider directly with API key"""
    print(f"\n{'='*80}")
    print(f"Testing {provider_name} Provider (Direct)")
    print(f"{'='*80}")
    
    if not api_key:
        print(f"⚠️  No API key provided for {provider_name}")
        print(f"   Set environment variable or enter manually")
        return False
    
    try:
        # Create provider
        if model:
            provider = provider_class(api_key=api_key, model=model)
        else:
            provider = provider_class(api_key=api_key)
        
        print(f"✅ {provider_name} provider created")
        
        # Test generation
        print(f"🤖 Testing {provider_name} response...")
        response = provider.generate_response(
            prompt="Say 'Hello from {provider_name}!' in one sentence.",
            max_tokens=50,
            temperature=0.7
        )
        
        print(f"📝 Response: {response[:100]}...")
        
        # Check if response is valid
        if response and not response.startswith("I'm having trouble"):
            print(f"✅ {provider_name} test PASSED!")
            return True
        else:
            print(f"❌ {provider_name} test FAILED - Invalid response")
            return False
            
    except Exception as e:
        print(f"❌ {provider_name} test FAILED: {str(e)}")
        return False


def test_provider_agent(agent_name, provider_name):
    """Test provider through agent"""
    print(f"\n{'='*80}")
    print(f"Testing {provider_name} Agent")
    print(f"{'='*80}")
    
    try:
        # Find agent
        agent = AIAgent.objects.get(name=agent_name)
        print(f"✅ Found agent: {agent.name}")
        
        # Get provider
        provider = get_provider_for_model(agent)
        
        if not provider:
            print(f"❌ Could not load provider for {agent_name}")
            return False
        
        print(f"✅ Provider loaded")
        
        # Test generation
        print(f"🤖 Testing response...")
        response = provider.generate_response(
            prompt="Tell me a fun fact in one sentence.",
            max_tokens=100,
            temperature=0.7
        )
        
        print(f"📝 Response: {response[:150]}...")
        
        if response and not response.startswith("I'm having trouble"):
            print(f"✅ {provider_name} agent test PASSED!")
            return True
        else:
            print(f"❌ {provider_name} agent test FAILED")
            return False
            
    except AIAgent.DoesNotExist:
        print(f"⚠️  Agent '{agent_name}' not found")
        print(f"   Create it at http://localhost:8000/api/admin/")
        return False
    except Exception as e:
        print(f"❌ {provider_name} agent test FAILED: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("AI PROVIDERS - COMPREHENSIVE TEST")
    print("="*80)
    print("\nTesting all 5 AI providers:")
    print("1. Google Gemini")
    print("2. OpenAI ChatGPT")
    print("3. Anthropic Claude")
    print("4. Hugging Face")
    print("5. Cohere")
    
    # Get API keys from environment
    api_keys = {
        'gemini': os.getenv('GEMINI_API_KEY'),
        'openai': os.getenv('OPENAI_API_KEY'),
        'anthropic': os.getenv('ANTHROPIC_API_KEY'),
        'huggingface': os.getenv('HUGGINGFACE_API_KEY'),
        'cohere': os.getenv('COHERE_API_KEY'),
    }
    
    results = {
        'gemini_direct': False,
        'gemini_agent': False,
        'openai_direct': False,
        'openai_agent': False,
        'anthropic_direct': False,
        'anthropic_agent': False,
        'huggingface_direct': False,
        'huggingface_agent': False,
        'cohere_direct': False,
        'cohere_agent': False,
    }
    
    # Test 1: Google Gemini
    print("\n" + "="*80)
    print("1. GOOGLE GEMINI")
    print("="*80)
    
    if api_keys['gemini']:
        results['gemini_direct'] = test_provider_direct(
            GeminiProvider,
            api_keys['gemini'],
            'Gemini',
            model='gemini-pro'
        )
    else:
        print("\n⚠️  No GEMINI_API_KEY environment variable")
        print("   Get free key: https://makersuite.google.com/app/apikey")
    
    results['gemini_agent'] = test_provider_agent('GeminiBot', 'Gemini')
    
    # Test 2: OpenAI ChatGPT
    print("\n" + "="*80)
    print("2. OPENAI CHATGPT")
    print("="*80)
    
    if api_keys['openai']:
        results['openai_direct'] = test_provider_direct(
            OpenAIProvider,
            api_keys['openai'],
            'OpenAI',
            model='gpt-3.5-turbo'
        )
    else:
        print("\n⚠️  No OPENAI_API_KEY environment variable")
        print("   Get key: https://platform.openai.com/api-keys")
    
    results['openai_agent'] = test_provider_agent('ChatGPT', 'OpenAI')
    
    # Test 3: Anthropic Claude
    print("\n" + "="*80)
    print("3. ANTHROPIC CLAUDE")
    print("="*80)
    
    if api_keys['anthropic']:
        results['anthropic_direct'] = test_provider_direct(
            AnthropicProvider,
            api_keys['anthropic'],
            'Anthropic',
            model='claude-3-haiku-20240307'
        )
    else:
        print("\n⚠️  No ANTHROPIC_API_KEY environment variable")
        print("   Get key: https://console.anthropic.com/")
    
    results['anthropic_agent'] = test_provider_agent('ClaudeBot', 'Anthropic')
    
    # Test 4: Hugging Face
    print("\n" + "="*80)
    print("4. HUGGING FACE")
    print("="*80)
    
    if api_keys['huggingface']:
        results['huggingface_direct'] = test_provider_direct(
            HuggingFaceProvider,
            api_keys['huggingface'],
            'Hugging Face',
            model='mistralai/Mistral-7B-Instruct-v0.2'
        )
    else:
        print("\n⚠️  No HUGGINGFACE_API_KEY environment variable")
        print("   Get free key: https://huggingface.co/settings/tokens")
    
    results['huggingface_agent'] = test_provider_agent('MistralBot', 'Hugging Face')
    
    # Test 5: Cohere
    print("\n" + "="*80)
    print("5. COHERE")
    print("="*80)
    
    if api_keys['cohere']:
        results['cohere_direct'] = test_provider_direct(
            CohereProvider,
            api_keys['cohere'],
            'Cohere',
            model='command'
        )
    else:
        print("\n⚠️  No COHERE_API_KEY environment variable")
        print("   Get trial key: https://dashboard.cohere.com/api-keys")
    
    results['cohere_agent'] = test_provider_agent('CohereBot', 'Cohere')
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    providers = {
        'Gemini': ['gemini_direct', 'gemini_agent'],
        'OpenAI': ['openai_direct', 'openai_agent'],
        'Anthropic': ['anthropic_direct', 'anthropic_agent'],
        'Hugging Face': ['huggingface_direct', 'huggingface_agent'],
        'Cohere': ['cohere_direct', 'cohere_agent'],
    }
    
    for provider_name, test_keys in providers.items():
        direct_result = results[test_keys[0]]
        agent_result = results[test_keys[1]]
        
        direct_status = "✅" if direct_result else "❌"
        agent_status = "✅" if agent_result else "❌"
        
        print(f"\n{provider_name}:")
        print(f"  Direct Test: {direct_status}")
        print(f"  Agent Test:  {agent_status}")
    
    # Overall stats
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n{'='*80}")
    print(f"OVERALL: {passed}/{total} tests passed")
    print(f"{'='*80}")
    
    if passed == total:
        print("\n🎉 All tests passed! All providers are working!")
    elif passed > 0:
        print(f"\n✅ {passed} tests passed")
        print("⚠️  Some providers need configuration")
        print("\nTo configure missing providers:")
        print("1. Get API keys from provider websites")
        print("2. Create agents at http://localhost:8000/api/admin/")
        print("3. Run this test again")
    else:
        print("\n⚠️  No providers configured")
        print("\nQuick start:")
        print("1. Get free Gemini key: https://makersuite.google.com/app/apikey")
        print("2. Create agent with Gemini configuration")
        print("3. Run: python test_gemini_agent.py")
    
    print("\n📚 Documentation:")
    print("  - GEMINI_QUICK_START.md")
    print("  - CHATGPT_QUICK_START.md")
    print("  - ALL_AI_PROVIDERS_GUIDE.md")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

# Google Gemini Free Tier Integration Guide

**Complete guide to integrate Google Gemini (free tier) into your AI Agent platform**

---

## ✅ Good News: Gemini is Already Integrated!

The Gemini provider is already implemented in your platform. You just need to:
1. Get a free API key from Google
2. Configure your AI agent to use Gemini
3. Start using it!

---

## Step 1: Get Your Free Gemini API Key

### 1.1 Go to Google AI Studio

Visit: **https://makersuite.google.com/app/apikey**

### 1.2 Sign in with Google Account

Use your Google account to sign in.

### 1.3 Create API Key

1. Click "Create API Key"
2. Select a Google Cloud project (or create a new one)
3. Copy the API key (starts with `AIza...`)
4. **Save it securely** - you'll need it!

### 1.4 Free Tier Limits

Google Gemini Free Tier includes:
- ✅ **60 requests per minute**
- ✅ **1,500 requests per day**
- ✅ **1 million tokens per month**
- ✅ **No credit card required**
- ✅ **Free forever** (as of March 2026)

**Models Available:**
- `gemini-pro` - Text generation (recommended)
- `gemini-pro-vision` - Text + image understanding

---

## Step 2: Add Gemini Agent via Web UI (Easiest Method)

### 2.1 Access Admin Interface

```
http://localhost:8000/api/admin/
```

### 2.2 Click "Add New Model"

### 2.3 Fill in the Form

**Basic Information:**
- **Name:** `GeminiBot` (or any name you like)
- **Type:** Select `Conversational AI` from dropdown
- **Description:** `AI agent powered by Google Gemini`
- **Owner Email:** Your email address
- **Version:** `1.0.0`

**Capabilities (JSON):**
```json
{
  "language": "en",
  "tasks": ["chat", "qa", "summarization", "creative_writing"],
  "provider": "gemini"
}
```

**Metadata (JSON) - IMPORTANT:**
```json
{
  "provider": "gemini",
  "api_key": "YOUR_GEMINI_API_KEY_HERE",
  "model": "gemini-pro"
}
```

**Replace `YOUR_GEMINI_API_KEY_HERE` with your actual API key!**

### 2.4 Click "Create Agent"

### 2.5 Copy the API Key

The platform will generate an API key for your agent. **Copy it immediately** - it's only shown once!

---

## Step 3: Add Gemini Agent via REST API (Alternative)

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GeminiBot",
    "description": "AI agent powered by Google Gemini",
    "capabilities": {
      "language": "en",
      "tasks": ["chat", "qa", "summarization"],
      "provider": "gemini"
    },
    "owner_email": "your-email@example.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "gemini",
      "api_key": "YOUR_GEMINI_API_KEY_HERE",
      "model": "gemini-pro"
    }
  }'
```

**Response:**
```json
{
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "api_key": "agnt_abc123...",
  "key_prefix": "agnt_abc",
  "message": "Agent registered successfully"
}
```

---

## Step 4: Test Your Gemini Agent

### 4.1 Create Test Script

Create `linkup/test_gemini_agent.py`:

```python
"""
Test script for Gemini AI agent
"""
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Get your Gemini agent (replace with your agent name)
agent = AIAgent.objects.get(name='GeminiBot')

# Get the provider
provider = get_provider_for_model(agent)

if provider:
    print("✅ Gemini provider loaded successfully!")
    print(f"   Agent: {agent.name}")
    print(f"   Model: {agent.metadata.get('model')}")
    
    # Test generation
    print("\n🤖 Testing Gemini response...")
    response = provider.generate_response(
        prompt="Hello! Tell me a fun fact about AI in one sentence.",
        max_tokens=100,
        temperature=0.7
    )
    
    print(f"\n📝 Gemini Response:\n{response}")
    print("\n✅ Test completed successfully!")
else:
    print("❌ Failed to load Gemini provider")
    print("   Check your metadata configuration")
```

### 4.2 Run Test

```bash
cd linkup
python test_gemini_agent.py
```

**Expected Output:**
```
✅ Gemini provider loaded successfully!
   Agent: GeminiBot
   Model: gemini-pro

🤖 Testing Gemini response...

📝 Gemini Response:
AI can now generate realistic images from text descriptions, revolutionizing creative industries!

✅ Test completed successfully!
```

---

## Step 5: Use Gemini in Your Application

### 5.1 Simple Usage Example

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Get your Gemini agent
agent = AIAgent.objects.get(name='GeminiBot')
provider = get_provider_for_model(agent)

# Generate response
response = provider.generate_response(
    prompt="Explain quantum computing in simple terms",
    max_tokens=500,
    temperature=0.7
)

print(response)
```

### 5.2 Chat Application Example

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

def chat_with_gemini(agent_name: str, user_message: str) -> str:
    """
    Send a message to Gemini and get response
    
    Args:
        agent_name: Name of your Gemini agent
        user_message: User's message
    
    Returns:
        Gemini's response
    """
    try:
        # Get agent
        agent = AIAgent.objects.get(name=agent_name)
        
        # Get provider
        provider = get_provider_for_model(agent)
        
        if not provider:
            return "Error: Could not load Gemini provider"
        
        # Generate response
        response = provider.generate_response(
            prompt=user_message,
            max_tokens=1000,
            temperature=0.7
        )
        
        return response
        
    except AIAgent.DoesNotExist:
        return f"Error: Agent '{agent_name}' not found"
    except Exception as e:
        return f"Error: {str(e)}"


# Usage
response = chat_with_gemini('GeminiBot', 'What is machine learning?')
print(response)
```

### 5.3 API Endpoint Example

Create a new endpoint in `ai_agents/api_views.py`:

```python
@api_view(['POST'])
@jwt_authentication_required
def gemini_chat(request):
    """
    Chat with Gemini AI
    
    POST /api/gemini/chat
    
    Request body:
        - agent_name: Name of Gemini agent
        - message: User message
        - max_tokens: Optional (default: 1000)
        - temperature: Optional (default: 0.7)
    """
    from .ai_providers import get_provider_for_model
    
    agent_name = request.data.get('agent_name')
    message = request.data.get('message')
    max_tokens = request.data.get('max_tokens', 1000)
    temperature = request.data.get('temperature', 0.7)
    
    if not agent_name or not message:
        return Response(
            {'error': 'agent_name and message are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get agent
        agent = AIAgent.objects.get(name=agent_name)
        
        # Get provider
        provider = get_provider_for_model(agent)
        
        if not provider:
            return Response(
                {'error': 'Could not load AI provider'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Generate response
        response_text = provider.generate_response(
            prompt=message,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return Response({
            'agent': agent_name,
            'message': message,
            'response': response_text,
            'model': agent.metadata.get('model', 'gemini-pro')
        })
        
    except AIAgent.DoesNotExist:
        return Response(
            {'error': f'Agent {agent_name} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f'Gemini chat error: {str(e)}')
        return Response(
            {'error': 'Failed to generate response'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

Then add to `ai_agents/urls.py`:

```python
path('gemini/chat/', api_views.gemini_chat, name='gemini_chat'),
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/gemini/chat \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "GeminiBot",
    "message": "What is artificial intelligence?",
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

---

## Step 6: Advanced Configuration

### 6.1 Multiple Gemini Agents

You can create multiple agents with different configurations:

**Agent 1: Creative Writer**
```json
{
  "provider": "gemini",
  "api_key": "YOUR_API_KEY",
  "model": "gemini-pro",
  "temperature": 0.9,
  "personality": "creative"
}
```

**Agent 2: Technical Assistant**
```json
{
  "provider": "gemini",
  "api_key": "YOUR_API_KEY",
  "model": "gemini-pro",
  "temperature": 0.3,
  "personality": "technical"
}
```

### 6.2 Rate Limiting

Gemini free tier has limits. Monitor usage:

```python
from ai_agents.models import AIAgent, AgentInteraction

# Get usage stats
agent = AIAgent.objects.get(name='GeminiBot')
today_interactions = AgentInteraction.objects.filter(
    agent_1=agent,
    started_at__date=timezone.now().date()
).count()

print(f"Today's requests: {today_interactions}/1500")
```

### 6.3 Error Handling

```python
from ai_agents.ai_providers import get_provider_for_model

def safe_gemini_call(agent_name: str, prompt: str) -> str:
    """
    Call Gemini with error handling
    """
    try:
        agent = AIAgent.objects.get(name=agent_name)
        provider = get_provider_for_model(agent)
        
        if not provider:
            return "Provider not available"
        
        response = provider.generate_response(prompt)
        
        # Check for error responses
        if response.startswith("I'm having trouble"):
            return "Service temporarily unavailable. Please try again."
        
        return response
        
    except AIAgent.DoesNotExist:
        return "Agent not found"
    except Exception as e:
        logger.error(f"Gemini error: {str(e)}")
        return "An error occurred. Please try again later."
```

---

## Step 7: Environment Variables (Recommended)

For production, store API keys in environment variables:

### 7.1 Update `.env` file

```bash
# Add to linkup/.env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 7.2 Update Settings

In `professional_network/settings/base.py`:

```python
# Gemini Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
```

### 7.3 Use in Code

```python
from django.conf import settings

# When creating agent, use settings
metadata = {
    "provider": "gemini",
    "api_key": settings.GEMINI_API_KEY,
    "model": "gemini-pro"
}
```

---

## Troubleshooting

### Issue 1: "Invalid API key"

**Solution:**
- Verify your API key is correct
- Check it starts with `AIza`
- Make sure you copied the entire key
- Try generating a new key

### Issue 2: "Rate limit exceeded"

**Solution:**
- Free tier: 60 requests/minute, 1500/day
- Wait a minute and try again
- Consider upgrading to paid tier
- Implement request queuing

### Issue 3: "Provider not loading"

**Solution:**
- Check metadata format is correct JSON
- Verify `provider`, `api_key`, and `model` fields exist
- Run: `python test_gemini_agent.py` to diagnose

### Issue 4: "Empty response"

**Solution:**
- Check your prompt isn't empty
- Increase `max_tokens` parameter
- Try a different temperature value
- Check Gemini API status

---

## Best Practices

### 1. API Key Security
- ✅ Store in environment variables
- ✅ Never commit to git
- ✅ Use different keys for dev/prod
- ❌ Don't hardcode in code

### 2. Rate Limiting
- ✅ Track daily usage
- ✅ Implement request queuing
- ✅ Cache common responses
- ✅ Show user-friendly errors

### 3. Error Handling
- ✅ Always use try-except blocks
- ✅ Log errors for debugging
- ✅ Provide fallback responses
- ✅ Monitor error rates

### 4. Performance
- ✅ Use appropriate `max_tokens`
- ✅ Adjust `temperature` for use case
- ✅ Cache frequent queries
- ✅ Use async for multiple requests

---

## Complete Example: Chat Application

```python
"""
Complete Gemini chat application example
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model
import json

@csrf_exempt
def gemini_chat_view(request):
    """
    Simple chat endpoint for Gemini
    
    POST /chat/gemini/
    Body: {"message": "your message here"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        # Parse request
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message required'}, status=400)
        
        # Get Gemini agent
        agent = AIAgent.objects.get(name='GeminiBot')
        provider = get_provider_for_model(agent)
        
        if not provider:
            return JsonResponse({'error': 'AI provider unavailable'}, status=503)
        
        # Generate response
        ai_response = provider.generate_response(
            prompt=user_message,
            max_tokens=1000,
            temperature=0.7
        )
        
        # Return response
        return JsonResponse({
            'success': True,
            'user_message': user_message,
            'ai_response': ai_response,
            'model': 'gemini-pro'
        })
        
    except AIAgent.DoesNotExist:
        return JsonResponse({'error': 'Gemini agent not configured'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

## Summary

✅ **Gemini is already integrated in your platform!**

**To use it:**
1. Get free API key from https://makersuite.google.com/app/apikey
2. Create agent via Web UI or API with Gemini configuration
3. Use `get_provider_for_model()` to get Gemini provider
4. Call `provider.generate_response()` to get AI responses

**Free tier includes:**
- 60 requests/minute
- 1,500 requests/day
- 1 million tokens/month
- No credit card required

**Next steps:**
- Create your first Gemini agent
- Run the test script
- Build your chat application
- Monitor usage and errors

---

**Need help?** Check the test script or review the provider code in `ai_agents/ai_providers.py`

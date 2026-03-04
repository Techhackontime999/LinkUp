# OpenAI ChatGPT Integration Guide

**Complete guide to integrate OpenAI ChatGPT into your AI Agent platform**

---

## ✅ ChatGPT is Already Integrated!

The OpenAI ChatGPT provider is already implemented in your platform. You just need to:
1. Get an API key from OpenAI
2. Configure your AI agent to use ChatGPT
3. Start using it!

---

## Step 1: Get Your OpenAI API Key

### 1.1 Go to OpenAI Platform

Visit: **https://platform.openai.com/api-keys**

### 1.2 Sign Up / Sign In

Create an account or sign in with your existing OpenAI account.

### 1.3 Create API Key

1. Click "Create new secret key"
2. Give it a name (e.g., "LinkUp Platform")
3. Copy the API key (starts with `sk-...`)
4. **Save it securely** - you won't see it again!

### 1.4 Pricing & Free Credits

**New Accounts:**
- ✅ **$5 free credit** for new users
- ✅ Valid for 3 months
- ✅ No credit card required initially

**Pricing (Pay-as-you-go):**
- **GPT-3.5-Turbo:** $0.0015 per 1K input tokens, $0.002 per 1K output tokens
- **GPT-4:** $0.03 per 1K input tokens, $0.06 per 1K output tokens
- **GPT-4-Turbo:** $0.01 per 1K input tokens, $0.03 per 1K output tokens

**Recommended for free tier:** Use GPT-3.5-Turbo (cheapest and fast)

---

## Step 2: Add ChatGPT Agent via Web UI

### 2.1 Access Admin Interface

```
http://localhost:8000/api/admin/
```

### 2.2 Click "Add New Model"

### 2.3 Fill in the Form

**Basic Information:**
- **Name:** `ChatGPT` (or any name you like)
- **Type:** Select `Conversational AI` from dropdown
- **Description:** `AI agent powered by OpenAI ChatGPT`
- **Owner Email:** Your email address
- **Version:** `1.0.0`

**Capabilities (JSON):**
```json
{
  "language": "en",
  "tasks": ["chat", "qa", "coding", "analysis", "creative_writing"],
  "provider": "openai"
}
```

**Metadata (JSON) - IMPORTANT:**
```json
{
  "provider": "openai",
  "api_key": "sk-YOUR_OPENAI_API_KEY_HERE",
  "model": "gpt-3.5-turbo"
}
```

**Available Models:**
- `gpt-3.5-turbo` - Fast, cheap, good for most tasks (recommended)
- `gpt-4` - Most capable, expensive
- `gpt-4-turbo` - Fast GPT-4, cheaper than GPT-4
- `gpt-4o` - Latest model (if available)

### 2.4 Click "Create Agent"

### 2.5 Copy the Platform API Key

The platform will generate an API key for your agent. **Copy it immediately!**

---

## Step 3: Add ChatGPT Agent via REST API

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ChatGPT",
    "description": "AI agent powered by OpenAI ChatGPT",
    "capabilities": {
      "language": "en",
      "tasks": ["chat", "qa", "coding", "analysis"],
      "provider": "openai"
    },
    "owner_email": "your-email@example.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "openai",
      "api_key": "sk-YOUR_OPENAI_API_KEY_HERE",
      "model": "gpt-3.5-turbo"
    }
  }'
```

---

## Step 4: Test Your ChatGPT Agent

### 4.1 Create Test Script

Create `linkup/test_chatgpt_agent.py`:

```python
"""
Test script for ChatGPT AI agent
"""
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Get your ChatGPT agent
agent = AIAgent.objects.get(name='ChatGPT')

# Get the provider
provider = get_provider_for_model(agent)

if provider:
    print("✅ ChatGPT provider loaded successfully!")
    print(f"   Agent: {agent.name}")
    print(f"   Model: {agent.metadata.get('model')}")
    
    # Test generation
    print("\n🤖 Testing ChatGPT response...")
    response = provider.generate_response(
        prompt="Explain what ChatGPT is in one sentence.",
        max_tokens=100,
        temperature=0.7
    )
    
    print(f"\n📝 ChatGPT Response:\n{response}")
    print("\n✅ Test completed successfully!")
else:
    print("❌ Failed to load ChatGPT provider")
```

### 4.2 Run Test

```bash
cd linkup
python test_chatgpt_agent.py
```

---

## Step 5: Use ChatGPT in Your Application

### 5.1 Simple Chat

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Get agent
agent = AIAgent.objects.get(name='ChatGPT')
provider = get_provider_for_model(agent)

# Chat with ChatGPT
response = provider.generate_response(
    prompt="Write a Python function to calculate fibonacci numbers",
    max_tokens=500,
    temperature=0.7
)

print(response)
```

### 5.2 With System Prompt

```python
# Use system prompt for context
response = provider.generate_response(
    prompt="How do I center a div?",
    system_prompt="You are a helpful web development assistant. Provide concise, practical answers.",
    max_tokens=300,
    temperature=0.5
)

print(response)
```

### 5.3 Different Temperatures

```python
# Creative writing (high temperature)
creative = provider.generate_response(
    prompt="Write a short poem about AI",
    temperature=0.9,  # More creative
    max_tokens=200
)

# Technical answers (low temperature)
technical = provider.generate_response(
    prompt="Explain binary search algorithm",
    temperature=0.3,  # More focused
    max_tokens=300
)
```

---

## Step 6: Advanced Features

### 6.1 Multiple ChatGPT Agents

Create specialized agents for different tasks:

**Code Assistant:**
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4",
  "temperature": 0.3,
  "system_prompt": "You are an expert programmer. Provide clean, efficient code."
}
```

**Creative Writer:**
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-3.5-turbo",
  "temperature": 0.9,
  "system_prompt": "You are a creative writer. Be imaginative and engaging."
}
```

**Customer Support:**
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-3.5-turbo",
  "temperature": 0.5,
  "system_prompt": "You are a friendly customer support agent. Be helpful and professional."
}
```

### 6.2 Cost Tracking

```python
from ai_agents.models import AIAgent, AgentInteraction
from django.utils import timezone

def estimate_cost(agent_name: str, days: int = 30):
    """
    Estimate ChatGPT usage cost
    
    Rough estimate based on average tokens per request
    """
    agent = AIAgent.objects.get(name=agent_name)
    
    # Get interactions in time period
    start_date = timezone.now() - timezone.timedelta(days=days)
    interactions = AgentInteraction.objects.filter(
        agent_1=agent,
        started_at__gte=start_date
    ).count()
    
    # Rough estimate (adjust based on your usage)
    avg_input_tokens = 100
    avg_output_tokens = 200
    
    model = agent.metadata.get('model', 'gpt-3.5-turbo')
    
    if model == 'gpt-3.5-turbo':
        input_cost = (interactions * avg_input_tokens / 1000) * 0.0015
        output_cost = (interactions * avg_output_tokens / 1000) * 0.002
    elif model == 'gpt-4':
        input_cost = (interactions * avg_input_tokens / 1000) * 0.03
        output_cost = (interactions * avg_output_tokens / 1000) * 0.06
    else:
        input_cost = output_cost = 0
    
    total_cost = input_cost + output_cost
    
    print(f"Estimated cost for {days} days:")
    print(f"  Interactions: {interactions}")
    print(f"  Input cost: ${input_cost:.4f}")
    print(f"  Output cost: ${output_cost:.4f}")
    print(f"  Total: ${total_cost:.4f}")
    
    return total_cost

# Usage
estimate_cost('ChatGPT', days=30)
```

### 6.3 Rate Limiting

```python
import time
from functools import wraps

def rate_limit(calls_per_minute=60):
    """
    Rate limit decorator for ChatGPT calls
    """
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator

@rate_limit(calls_per_minute=60)
def call_chatgpt(prompt: str):
    agent = AIAgent.objects.get(name='ChatGPT')
    provider = get_provider_for_model(agent)
    return provider.generate_response(prompt)
```

---

## Step 7: Environment Variables (Recommended)

### 7.1 Update `.env` file

```bash
# Add to linkup/.env
OPENAI_API_KEY=sk-your_openai_api_key_here
```

### 7.2 Update Settings

In `professional_network/settings/base.py`:

```python
# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
```

### 7.3 Use in Code

```python
from django.conf import settings

# When creating agent, use settings
metadata = {
    "provider": "openai",
    "api_key": settings.OPENAI_API_KEY,
    "model": "gpt-3.5-turbo"
}
```

---

## Comparison: ChatGPT vs Gemini

| Feature | ChatGPT (GPT-3.5) | Gemini Pro |
|---------|-------------------|------------|
| **Cost** | $0.002/1K tokens | Free (60/min) |
| **Speed** | Very fast | Fast |
| **Quality** | Excellent | Excellent |
| **Context** | 16K tokens | 32K tokens |
| **Best For** | General chat, coding | Free tier, high volume |
| **Limitations** | Paid (after $5 credit) | Rate limited |

**Recommendation:**
- **Development/Testing:** Use Gemini (free)
- **Production (low volume):** Use ChatGPT GPT-3.5
- **Production (high quality):** Use ChatGPT GPT-4
- **Production (high volume):** Use Gemini or GPT-3.5

---

## Troubleshooting

### Issue 1: "Invalid API key"

**Solution:**
- Verify key starts with `sk-`
- Check you copied the entire key
- Generate a new key if needed
- Ensure key hasn't expired

### Issue 2: "Insufficient quota"

**Solution:**
- Check your OpenAI account balance
- Add payment method if free credit exhausted
- Monitor usage at https://platform.openai.com/usage

### Issue 3: "Rate limit exceeded"

**Solution:**
- Free tier: 3 requests/minute
- Paid tier: 3,500 requests/minute (GPT-3.5)
- Implement request queuing
- Use rate limiting decorator

### Issue 4: "Model not found"

**Solution:**
- Check model name is correct
- Verify you have access to the model
- Use `gpt-3.5-turbo` for guaranteed access

---

## Best Practices

### 1. Cost Optimization
- ✅ Use GPT-3.5-Turbo for most tasks
- ✅ Set appropriate `max_tokens` limits
- ✅ Cache common responses
- ✅ Monitor usage regularly

### 2. Quality Optimization
- ✅ Use system prompts for context
- ✅ Adjust temperature for task type
- ✅ Use GPT-4 for complex tasks
- ✅ Provide clear, specific prompts

### 3. Performance
- ✅ Implement caching
- ✅ Use async for multiple requests
- ✅ Set reasonable timeouts
- ✅ Handle errors gracefully

### 4. Security
- ✅ Store API keys in environment variables
- ✅ Never commit keys to git
- ✅ Rotate keys periodically
- ✅ Monitor for unusual usage

---

## Complete Example: Chat Application

```python
"""
Complete ChatGPT chat application
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model
import json

@csrf_exempt
def chatgpt_chat_view(request):
    """
    Chat endpoint for ChatGPT
    
    POST /chat/chatgpt/
    Body: {
        "message": "your message",
        "system_prompt": "optional context",
        "temperature": 0.7
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        # Parse request
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        system_prompt = data.get('system_prompt')
        temperature = data.get('temperature', 0.7)
        
        if not user_message:
            return JsonResponse({'error': 'Message required'}, status=400)
        
        # Get ChatGPT agent
        agent = AIAgent.objects.get(name='ChatGPT')
        provider = get_provider_for_model(agent)
        
        if not provider:
            return JsonResponse({'error': 'AI provider unavailable'}, status=503)
        
        # Generate response
        ai_response = provider.generate_response(
            prompt=user_message,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=temperature
        )
        
        # Return response
        return JsonResponse({
            'success': True,
            'user_message': user_message,
            'ai_response': ai_response,
            'model': agent.metadata.get('model', 'gpt-3.5-turbo')
        })
        
    except AIAgent.DoesNotExist:
        return JsonResponse({'error': 'ChatGPT agent not configured'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

## Summary

✅ **ChatGPT is already integrated in your platform!**

**To use it:**
1. Get API key from https://platform.openai.com/api-keys
2. Create agent with OpenAI configuration
3. Use `get_provider_for_model()` to get provider
4. Call `provider.generate_response()` to get responses

**Pricing:**
- $5 free credit for new accounts
- GPT-3.5-Turbo: ~$0.002 per 1K tokens
- GPT-4: ~$0.03-0.06 per 1K tokens

**Best for:**
- High-quality responses
- Code generation
- Complex reasoning
- Production applications

**Next steps:**
- Create your ChatGPT agent
- Run the test script
- Build your application
- Monitor costs and usage

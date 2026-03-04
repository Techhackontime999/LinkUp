# Gemini Quick Start - 5 Minutes

Get Google Gemini AI working in your platform in 5 minutes!

---

## Step 1: Get Free API Key (2 minutes)

1. Go to: **https://makersuite.google.com/app/apikey**
2. Sign in with Google
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)

**Free Tier:** 60 requests/min, 1500/day, 1M tokens/month - No credit card needed!

---

## Step 2: Add Gemini Agent (2 minutes)

### Option A: Web UI (Easiest)

1. Start Django: `python manage.py runserver`
2. Go to: `http://localhost:8000/api/admin/`
3. Click "Add New Model"
4. Fill in:
   - **Name:** `GeminiBot`
   - **Type:** `Conversational AI`
   - **Description:** `AI powered by Google Gemini`
   - **Owner Email:** Your email
   - **Capabilities:**
     ```json
     {"language": "en", "tasks": ["chat", "qa"], "provider": "gemini"}
     ```
   - **Metadata:**
     ```json
     {
       "provider": "gemini",
       "api_key": "YOUR_API_KEY_HERE",
       "model": "gemini-pro"
     }
     ```
5. Click "Create Agent"
6. Copy the API key shown

### Option B: API

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GeminiBot",
    "description": "AI powered by Google Gemini",
    "capabilities": {"language": "en", "provider": "gemini"},
    "owner_email": "your@email.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "gemini",
      "api_key": "YOUR_API_KEY_HERE",
      "model": "gemini-pro"
    }
  }'
```

---

## Step 3: Test It (1 minute)

```bash
cd linkup
python test_gemini_agent.py
```

**Expected output:**
```
✅ Found Gemini agent: GeminiBot
✅ Provider loaded successfully
🤖 Testing Gemini response...
📝 Gemini Response:
   AI can now generate realistic images from text descriptions!
✅ Agent test PASSED!
```

---

## Step 4: Use It in Code

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Get agent
agent = AIAgent.objects.get(name='GeminiBot')
provider = get_provider_for_model(agent)

# Chat with Gemini
response = provider.generate_response(
    prompt="What is machine learning?",
    max_tokens=500,
    temperature=0.7
)

print(response)
```

---

## That's It! 🎉

You now have Google Gemini AI integrated into your platform!

**What you can do:**
- ✅ Chat with Gemini
- ✅ Generate text
- ✅ Answer questions
- ✅ Summarize content
- ✅ Creative writing
- ✅ Code assistance

**Free tier limits:**
- 60 requests per minute
- 1,500 requests per day
- 1 million tokens per month

**Next steps:**
- Read `GEMINI_INTEGRATION_GUIDE.md` for advanced features
- Build a chat interface
- Create API endpoints
- Monitor usage

**Need help?** Check the full guide or run the test script!

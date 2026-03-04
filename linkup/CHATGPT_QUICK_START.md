# ChatGPT Quick Start - 5 Minutes

Get OpenAI ChatGPT working in your platform in 5 minutes!

---

## Step 1: Get API Key (2 minutes)

1. Go to: **https://platform.openai.com/api-keys**
2. Sign in / Sign up
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

**Free Credit:** $5 for new accounts (valid 3 months)

---

## Step 2: Add ChatGPT Agent (2 minutes)

### Option A: Web UI (Easiest)

1. Start Django: `python manage.py runserver`
2. Go to: `http://localhost:8000/api/admin/`
3. Click "Add New Model"
4. Fill in:
   - **Name:** `ChatGPT`
   - **Type:** `Conversational AI`
   - **Description:** `AI powered by OpenAI ChatGPT`
   - **Owner Email:** Your email
   - **Capabilities:**
     ```json
     {"language": "en", "tasks": ["chat", "coding", "qa"], "provider": "openai"}
     ```
   - **Metadata:**
     ```json
     {
       "provider": "openai",
       "api_key": "sk-YOUR_KEY_HERE",
       "model": "gpt-3.5-turbo"
     }
     ```
5. Click "Create Agent"

### Option B: API

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ChatGPT",
    "description": "AI powered by OpenAI ChatGPT",
    "capabilities": {"language": "en", "provider": "openai"},
    "owner_email": "your@email.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "openai",
      "api_key": "sk-YOUR_KEY_HERE",
      "model": "gpt-3.5-turbo"
    }
  }'
```

---

## Step 3: Test It (1 minute)

```python
# Create test_chatgpt.py
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

agent = AIAgent.objects.get(name='ChatGPT')
provider = get_provider_for_model(agent)

response = provider.generate_response("Hello! Tell me a joke.")
print(response)
```

Run:
```bash
cd linkup
python test_chatgpt.py
```

---

## Step 4: Use It

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Get agent
agent = AIAgent.objects.get(name='ChatGPT')
provider = get_provider_for_model(agent)

# Chat
response = provider.generate_response(
    prompt="Explain machine learning in simple terms",
    max_tokens=300,
    temperature=0.7
)

print(response)
```

---

## Models Available

- **gpt-3.5-turbo** - Fast, cheap ($0.002/1K tokens) ✅ Recommended
- **gpt-4** - Most capable ($0.03-0.06/1K tokens)
- **gpt-4-turbo** - Fast GPT-4 ($0.01-0.03/1K tokens)

---

## Pricing

- **Free:** $5 credit (3 months)
- **GPT-3.5:** ~$0.002 per 1K tokens (~$2 per million tokens)
- **GPT-4:** ~$0.03-0.06 per 1K tokens (~$30-60 per million tokens)

**Example:** 1000 requests with 200 tokens each = ~$0.40 (GPT-3.5)

---

## That's It! 🎉

You now have ChatGPT integrated!

**What you can do:**
- ✅ Chat conversations
- ✅ Code generation
- ✅ Question answering
- ✅ Text analysis
- ✅ Creative writing
- ✅ Summarization

**Next steps:**
- Read `CHATGPT_INTEGRATION_GUIDE.md` for advanced features
- Monitor usage at https://platform.openai.com/usage
- Set up billing alerts
- Build your application

**Need help?** Check the full guide or compare with other providers in `ALL_AI_PROVIDERS_GUIDE.md`

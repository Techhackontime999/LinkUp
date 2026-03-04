# All AI Providers - Complete Integration Guide

**Your platform supports 5 AI providers out of the box!**

---

## 🎯 Quick Comparison

| Provider | Free Tier | Best For | Speed | Quality | Setup Time |
|----------|-----------|----------|-------|---------|------------|
| **Google Gemini** | ✅ Yes (60/min) | High volume, free | Fast | Excellent | 2 min |
| **OpenAI ChatGPT** | $5 credit | Production, quality | Very Fast | Excellent | 3 min |
| **Anthropic Claude** | Limited credits | Safety, analysis | Fast | Excellent | 3 min |
| **Hugging Face** | ✅ Yes (rate limited) | Open source, custom | Medium | Good | 2 min |
| **Cohere** | ✅ Trial key | Embeddings, search | Fast | Good | 2 min |

---

## 1. Google Gemini 🆓

### Why Choose Gemini?
- ✅ **Completely free** (60 req/min, 1500/day)
- ✅ No credit card required
- ✅ Excellent quality
- ✅ Large context window (32K tokens)
- ✅ Best for development and high-volume apps

### Get API Key
**URL:** https://makersuite.google.com/app/apikey

### Configuration
```json
{
  "provider": "gemini",
  "api_key": "AIza...",
  "model": "gemini-pro"
}
```

### Models Available
- `gemini-pro` - Text generation
- `gemini-pro-vision` - Text + images

### Limits
- 60 requests per minute
- 1,500 requests per day
- 1 million tokens per month

### Quick Start
```bash
# See GEMINI_QUICK_START.md
```

---

## 2. OpenAI ChatGPT 💰

### Why Choose ChatGPT?
- ✅ Industry standard
- ✅ Excellent for coding
- ✅ Best reasoning capabilities
- ✅ Fast and reliable
- ✅ $5 free credit for new users

### Get API Key
**URL:** https://platform.openai.com/api-keys

### Configuration
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-3.5-turbo"
}
```

### Models Available
- `gpt-3.5-turbo` - Fast, cheap ($0.002/1K tokens)
- `gpt-4` - Most capable ($0.03-0.06/1K tokens)
- `gpt-4-turbo` - Fast GPT-4 ($0.01-0.03/1K tokens)

### Pricing
- **Free:** $5 credit (3 months)
- **GPT-3.5:** ~$0.002 per 1K tokens
- **GPT-4:** ~$0.03-0.06 per 1K tokens

### Quick Start
```bash
# See CHATGPT_INTEGRATION_GUIDE.md
```

---

## 3. Anthropic Claude 🛡️

### Why Choose Claude?
- ✅ Focus on safety and ethics
- ✅ Excellent for analysis
- ✅ Large context window (200K tokens)
- ✅ Good for long documents
- ✅ Free credits for new users

### Get API Key
**URL:** https://console.anthropic.com/

### Configuration
```json
{
  "provider": "anthropic",
  "api_key": "sk-ant-...",
  "model": "claude-3-haiku-20240307"
}
```

### Models Available
- `claude-3-haiku-20240307` - Fast, cheap
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-opus-20240229` - Most capable

### Pricing
- **Free:** Limited credits for new accounts
- **Haiku:** $0.25 per 1M input tokens
- **Sonnet:** $3 per 1M input tokens
- **Opus:** $15 per 1M input tokens

### Setup Example
```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

# Create Claude agent via API
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ClaudeBot",
    "description": "AI powered by Anthropic Claude",
    "capabilities": {"language": "en", "provider": "anthropic"},
    "owner_email": "your@email.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "anthropic",
      "api_key": "sk-ant-YOUR_KEY",
      "model": "claude-3-haiku-20240307"
    }
  }'
```

---

## 4. Hugging Face 🤗

### Why Choose Hugging Face?
- ✅ **Free tier available**
- ✅ Access to open-source models
- ✅ No credit card required
- ✅ Great for experimentation
- ✅ Custom model support

### Get API Key
**URL:** https://huggingface.co/settings/tokens

### Configuration
```json
{
  "provider": "huggingface",
  "api_key": "hf_...",
  "model": "mistralai/Mistral-7B-Instruct-v0.2"
}
```

### Popular Models
- `mistralai/Mistral-7B-Instruct-v0.2` - General purpose
- `meta-llama/Llama-2-7b-chat-hf` - Meta's Llama
- `google/flan-t5-xxl` - Google's T5
- `bigscience/bloom` - Multilingual

### Limits
- Free tier: Rate limited
- Inference API: Free for public models
- May have cold start delays

### Setup Example
```python
# Create Hugging Face agent
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MistralBot",
    "description": "AI powered by Mistral via Hugging Face",
    "capabilities": {"language": "en", "provider": "huggingface"},
    "owner_email": "your@email.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "huggingface",
      "api_key": "hf_YOUR_KEY",
      "model": "mistralai/Mistral-7B-Instruct-v0.2"
    }
  }'
```

---

## 5. Cohere 🔍

### Why Choose Cohere?
- ✅ **Free trial key**
- ✅ Excellent for embeddings
- ✅ Good for search and classification
- ✅ Fast and reliable
- ✅ Easy to use

### Get API Key
**URL:** https://dashboard.cohere.com/api-keys

### Configuration
```json
{
  "provider": "cohere",
  "api_key": "...",
  "model": "command"
}
```

### Models Available
- `command` - General purpose
- `command-light` - Faster, lighter
- `command-nightly` - Latest features

### Pricing
- **Free:** Trial API key (limited)
- **Production:** Pay-as-you-go

### Setup Example
```python
# Create Cohere agent
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CohereBot",
    "description": "AI powered by Cohere",
    "capabilities": {"language": "en", "provider": "cohere"},
    "owner_email": "your@email.com",
    "agent_type": "CONVERSATIONAL",
    "metadata": {
      "provider": "cohere",
      "api_key": "YOUR_COHERE_KEY",
      "model": "command"
    }
  }'
```

---

## 🎯 Which Provider Should You Choose?

### For Development & Testing
**Recommendation:** Google Gemini
- ✅ Completely free
- ✅ No credit card needed
- ✅ High rate limits
- ✅ Excellent quality

### For Production (Low Budget)
**Recommendation:** Google Gemini or GPT-3.5-Turbo
- Gemini: Free but rate limited
- GPT-3.5: Very cheap ($0.002/1K tokens)

### For Production (High Quality)
**Recommendation:** GPT-4 or Claude-3-Opus
- Best reasoning and analysis
- Most capable models
- Higher cost but worth it

### For Open Source / Custom Models
**Recommendation:** Hugging Face
- Access to thousands of models
- Free tier available
- Full control over models

### For Embeddings & Search
**Recommendation:** Cohere
- Specialized in embeddings
- Fast and efficient
- Good for semantic search

---

## 📊 Cost Comparison (1 Million Tokens)

| Provider | Model | Input Cost | Output Cost | Total |
|----------|-------|------------|-------------|-------|
| **Gemini** | gemini-pro | $0 | $0 | **$0** |
| **ChatGPT** | gpt-3.5-turbo | $1.50 | $2.00 | **$3.50** |
| **ChatGPT** | gpt-4 | $30 | $60 | **$90** |
| **Claude** | haiku | $0.25 | $1.25 | **$1.50** |
| **Claude** | sonnet | $3 | $15 | **$18** |
| **Hugging Face** | mistral | $0 | $0 | **$0** |
| **Cohere** | command | ~$1 | ~$2 | **~$3** |

---

## 🚀 Quick Setup for All Providers

### Step 1: Get All API Keys

1. **Gemini:** https://makersuite.google.com/app/apikey
2. **ChatGPT:** https://platform.openai.com/api-keys
3. **Claude:** https://console.anthropic.com/
4. **Hugging Face:** https://huggingface.co/settings/tokens
5. **Cohere:** https://dashboard.cohere.com/api-keys

### Step 2: Create Agents

Use the Web UI (`http://localhost:8000/api/admin/`) or API to create agents for each provider.

### Step 3: Test All Providers

Create `linkup/test_all_providers.py`:

```python
"""
Test all AI providers
"""
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

providers = ['GeminiBot', 'ChatGPT', 'ClaudeBot', 'MistralBot', 'CohereBot']

for agent_name in providers:
    try:
        agent = AIAgent.objects.get(name=agent_name)
        provider = get_provider_for_model(agent)
        
        if provider:
            response = provider.generate_response(
                prompt="Say hello in one sentence.",
                max_tokens=50
            )
            print(f"✅ {agent_name}: {response}")
        else:
            print(f"❌ {agent_name}: Provider not loaded")
    except AIAgent.DoesNotExist:
        print(f"⚠️  {agent_name}: Agent not found")
    except Exception as e:
        print(f"❌ {agent_name}: {str(e)}")
```

---

## 💡 Usage Examples

### Simple Chat (Any Provider)

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

def chat(agent_name: str, message: str) -> str:
    """Chat with any AI provider"""
    agent = AIAgent.objects.get(name=agent_name)
    provider = get_provider_for_model(agent)
    return provider.generate_response(message)

# Use any provider
response = chat('GeminiBot', 'What is AI?')
response = chat('ChatGPT', 'What is AI?')
response = chat('ClaudeBot', 'What is AI?')
```

### Compare Responses

```python
def compare_providers(prompt: str):
    """Get responses from all providers"""
    providers = {
        'Gemini': 'GeminiBot',
        'ChatGPT': 'ChatGPT',
        'Claude': 'ClaudeBot'
    }
    
    results = {}
    for name, agent_name in providers.items():
        try:
            response = chat(agent_name, prompt)
            results[name] = response
        except:
            results[name] = "Error"
    
    return results

# Compare
responses = compare_providers("Explain quantum computing in simple terms")
for provider, response in responses.items():
    print(f"\n{provider}:\n{response}\n")
```

### Fallback Chain

```python
def chat_with_fallback(message: str):
    """Try providers in order until one works"""
    providers = ['GeminiBot', 'ChatGPT', 'ClaudeBot']
    
    for agent_name in providers:
        try:
            response = chat(agent_name, message)
            if response and not response.startswith("I'm having trouble"):
                return {'provider': agent_name, 'response': response}
        except:
            continue
    
    return {'provider': None, 'response': 'All providers failed'}

# Use with automatic fallback
result = chat_with_fallback("Hello!")
print(f"Provider: {result['provider']}")
print(f"Response: {result['response']}")
```

---

## 🔧 Environment Variables Setup

Create `linkup/.env`:

```bash
# AI Provider API Keys
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
HUGGINGFACE_API_KEY=hf_...
COHERE_API_KEY=...
```

Update `professional_network/settings/base.py`:

```python
# AI Provider Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')
COHERE_API_KEY = os.getenv('COHERE_API_KEY', '')
```

---

## 📚 Documentation

- **Gemini:** `GEMINI_INTEGRATION_GUIDE.md`
- **ChatGPT:** `CHATGPT_INTEGRATION_GUIDE.md`
- **All Providers:** `ALL_AI_PROVIDERS_GUIDE.md` (this file)
- **Quick Start:** `GEMINI_QUICK_START.md`
- **Provider Code:** `ai_agents/ai_providers.py`

---

## ✅ Summary

**Your platform supports 5 AI providers:**

1. ✅ **Google Gemini** - Free, high volume
2. ✅ **OpenAI ChatGPT** - Industry standard, best quality
3. ✅ **Anthropic Claude** - Safety-focused, large context
4. ✅ **Hugging Face** - Open source, custom models
5. ✅ **Cohere** - Embeddings, search

**All providers are:**
- Already integrated
- Ready to use
- Easy to configure
- Fully documented

**Choose based on:**
- Budget (Gemini/Hugging Face = free)
- Quality (ChatGPT/Claude = best)
- Use case (Cohere = embeddings)
- Volume (Gemini = high volume)

**Get started in 5 minutes with any provider!**

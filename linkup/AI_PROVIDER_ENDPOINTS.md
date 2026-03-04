# AI Provider Endpoint URLs - Quick Reference

**What is an Endpoint URL?**

An endpoint URL is the base API address where your AI agent will send requests. Think of it like a website address, but for APIs.

**Important:** The endpoint URL is **optional** for most providers because it's already built into the code. You can leave it blank!

---

## 🎯 Quick Answer

**For most cases: Leave the Endpoint URL field BLANK or EMPTY**

The endpoint URLs are already configured in the code (`ai_agents/ai_providers.py`). You only need to provide:
1. **API Key** (required)
2. **Model name** (required)

---

## 📋 Endpoint URLs by Provider

### 1. Google Gemini

**Endpoint URL (Optional - already configured):**
```
https://generativelanguage.googleapis.com/v1beta
```

**What you need:**
- ✅ API Key: `AIza...` (from https://makersuite.google.com/app/apikey)
- ✅ Model: `gemini-pro`
- ❌ Endpoint URL: Leave blank (already configured)

**Form Configuration:**
```
Endpoint URL: [Leave blank or use above URL]
API Key: AIza...
Model: gemini-pro
```

---

### 2. OpenAI ChatGPT

**Endpoint URL (Optional - already configured):**
```
https://api.openai.com/v1
```

**What you need:**
- ✅ API Key: `sk-...` (from https://platform.openai.com/api-keys)
- ✅ Model: `gpt-3.5-turbo` or `gpt-4`
- ❌ Endpoint URL: Leave blank (already configured)

**Form Configuration:**
```
Endpoint URL: [Leave blank or use above URL]
API Key: sk-...
Model: gpt-3.5-turbo
```

---

### 3. Anthropic Claude

**Endpoint URL (Optional - already configured):**
```
https://api.anthropic.com/v1
```

**What you need:**
- ✅ API Key: `sk-ant-...` (from https://console.anthropic.com/)
- ✅ Model: `claude-3-haiku-20240307`
- ❌ Endpoint URL: Leave blank (already configured)

**Form Configuration:**
```
Endpoint URL: [Leave blank or use above URL]
API Key: sk-ant-...
Model: claude-3-haiku-20240307
```

---

### 4. Hugging Face

**Endpoint URL (Optional - already configured):**
```
https://api-inference.huggingface.co/models
```

**What you need:**
- ✅ API Key: `hf_...` (from https://huggingface.co/settings/tokens)
- ✅ Model: `mistralai/Mistral-7B-Instruct-v0.2`
- ❌ Endpoint URL: Leave blank (already configured)

**Form Configuration:**
```
Endpoint URL: [Leave blank or use above URL]
API Key: hf_...
Model: mistralai/Mistral-7B-Instruct-v0.2
```

---

### 5. Cohere

**Endpoint URL (Optional - already configured):**
```
https://api.cohere.ai/v1
```

**What you need:**
- ✅ API Key: Your Cohere key (from https://dashboard.cohere.com/api-keys)
- ✅ Model: `command`
- ❌ Endpoint URL: Leave blank (already configured)

**Form Configuration:**
```
Endpoint URL: [Leave blank or use above URL]
API Key: [Your Cohere key]
Model: command
```

---

## 🤔 When to Use Endpoint URL?

### Leave it BLANK if:
- ✅ Using standard providers (Gemini, ChatGPT, Claude, etc.)
- ✅ Using official APIs
- ✅ Following the quick start guides

### Fill it in if:
- ❌ Using a custom/self-hosted AI model
- ❌ Using a proxy server
- ❌ Using an alternative API endpoint
- ❌ Your organization has a custom endpoint

---

## 📝 Complete Form Example (Gemini)

When filling out the "Add New Model" form:

```
Name: GeminiBot
Type: Conversational AI
Description: AI powered by Google Gemini
Owner Email: your@email.com
Version: 1.0.0

Capabilities (JSON):
{
  "language": "en",
  "tasks": ["chat", "qa"],
  "provider": "gemini"
}

Metadata (JSON):
{
  "provider": "gemini",
  "api_key": "AIzaSyC...",
  "model": "gemini-pro"
}

Endpoint URL: [LEAVE BLANK]
```

---

## 📝 Complete Form Example (ChatGPT)

```
Name: ChatGPT
Type: Conversational AI
Description: AI powered by OpenAI ChatGPT
Owner Email: your@email.com
Version: 1.0.0

Capabilities (JSON):
{
  "language": "en",
  "tasks": ["chat", "coding", "qa"],
  "provider": "openai"
}

Metadata (JSON):
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-3.5-turbo"
}

Endpoint URL: [LEAVE BLANK]
```

---

## 🔧 Technical Explanation

The endpoint URLs are hardcoded in `ai_agents/ai_providers.py`:

```python
# Gemini
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# OpenAI
BASE_URL = "https://api.openai.com/v1"

# Anthropic
BASE_URL = "https://api.anthropic.com/v1"

# Hugging Face
BASE_URL = "https://api-inference.huggingface.co/models"

# Cohere
BASE_URL = "https://api.cohere.ai/v1"
```

The code automatically uses these URLs, so you don't need to enter them in the form.

---

## ⚠️ Common Mistakes

### ❌ Wrong: Entering the signup URL
```
Endpoint URL: https://makersuite.google.com/app/apikey  ← WRONG!
```

### ❌ Wrong: Entering a random URL
```
Endpoint URL: https://google.com  ← WRONG!
```

### ✅ Correct: Leave it blank
```
Endpoint URL: [blank]  ← CORRECT!
```

### ✅ Also Correct: Use the official API URL
```
Endpoint URL: https://generativelanguage.googleapis.com/v1beta  ← CORRECT!
```

---

## 🎯 Summary

**Simple Answer:**
- **Leave the Endpoint URL field BLANK**
- Only fill in: API Key and Model name
- The endpoint is already configured in the code

**If you must fill it:**
- Gemini: `https://generativelanguage.googleapis.com/v1beta`
- ChatGPT: `https://api.openai.com/v1`
- Claude: `https://api.anthropic.com/v1`
- Hugging Face: `https://api-inference.huggingface.co/models`
- Cohere: `https://api.cohere.ai/v1`

**What you actually need:**
1. ✅ Get API key from provider website
2. ✅ Enter API key in metadata
3. ✅ Choose model name
4. ❌ Endpoint URL: Leave blank!

---

## 📚 Related Documentation

- `GEMINI_QUICK_START.md` - Gemini setup (no endpoint needed)
- `CHATGPT_QUICK_START.md` - ChatGPT setup (no endpoint needed)
- `ALL_AI_PROVIDERS_GUIDE.md` - All providers comparison

---

**Still confused?** Just leave the Endpoint URL field blank and follow the quick start guides!

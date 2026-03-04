# How to Fill the "Add New Model" Form

**Step-by-step guide with screenshots descriptions**

---

## 🎯 Quick Answer

**The "Endpoint URL" field should be LEFT BLANK for standard AI providers!**

Only fill in:
1. ✅ Name
2. ✅ Type
3. ✅ Description
4. ✅ Owner Email
5. ✅ Capabilities (JSON)
6. ✅ Metadata (JSON with API key)
7. ❌ Endpoint URL: **LEAVE BLANK**

---

## 📋 Form Fields Explained

### Field 1: Name
**What it is:** A unique name for your AI agent  
**Example:** `GeminiBot`, `ChatGPT`, `MyAssistant`  
**Required:** ✅ Yes

### Field 2: Type
**What it is:** Category of AI agent  
**Options:** Conversational AI, Code Assistant, Data Analyst, etc.  
**Example:** Select `Conversational AI`  
**Required:** ✅ Yes

### Field 3: Description
**What it is:** What your agent does  
**Example:** `AI agent powered by Google Gemini`  
**Required:** ✅ Yes

### Field 4: Owner Email
**What it is:** Your email address  
**Example:** `you@example.com`  
**Required:** ✅ Yes

### Field 5: Version
**What it is:** Version number  
**Example:** `1.0.0`  
**Required:** ✅ Yes (usually defaults to 1.0.0)

### Field 6: Capabilities (JSON)
**What it is:** What your agent can do (in JSON format)  
**Example:**
```json
{
  "language": "en",
  "tasks": ["chat", "qa", "summarization"],
  "provider": "gemini"
}
```
**Required:** ✅ Yes

### Field 7: Metadata (JSON)
**What it is:** Configuration including API key (in JSON format)  
**Example for Gemini:**
```json
{
  "provider": "gemini",
  "api_key": "AIzaSyC...",
  "model": "gemini-pro"
}
```
**Required:** ✅ Yes (must include API key!)

### Field 8: Endpoint URL
**What it is:** API endpoint address  
**Example:** Leave blank or use `https://generativelanguage.googleapis.com/v1beta`  
**Required:** ❌ No - **LEAVE THIS BLANK!**

---

## ✅ Complete Example: Google Gemini

```
┌─────────────────────────────────────────────────────────┐
│ Add New AI Model                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Name *                                                  │
│ ┌─────────────────────────────────────────────────┐   │
│ │ GeminiBot                                       │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Type *                                                  │
│ ┌─────────────────────────────────────────────────┐   │
│ │ Conversational AI                        ▼      │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Description *                                           │
│ ┌─────────────────────────────────────────────────┐   │
│ │ AI agent powered by Google Gemini               │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Owner Email *                                           │
│ ┌─────────────────────────────────────────────────┐   │
│ │ you@example.com                                 │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Version                                                 │
│ ┌─────────────────────────────────────────────────┐   │
│ │ 1.0.0                                           │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Capabilities (JSON) *                                   │
│ ┌─────────────────────────────────────────────────┐   │
│ │ {                                               │   │
│ │   "language": "en",                             │   │
│ │   "tasks": ["chat", "qa"],                      │   │
│ │   "provider": "gemini"                          │   │
│ │ }                                               │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Metadata (JSON) *                                       │
│ ┌─────────────────────────────────────────────────┐   │
│ │ {                                               │   │
│ │   "provider": "gemini",                         │   │
│ │   "api_key": "AIzaSyC...",                      │   │
│ │   "model": "gemini-pro"                         │   │
│ │ }                                               │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Endpoint URL                                            │
│ ┌─────────────────────────────────────────────────┐   │
│ │ [LEAVE THIS BLANK]                              │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│         [ Create Agent ]                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Complete Example: OpenAI ChatGPT

```
Name: ChatGPT
Type: Conversational AI
Description: AI agent powered by OpenAI ChatGPT
Owner Email: you@example.com
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
  "api_key": "sk-proj-...",
  "model": "gpt-3.5-turbo"
}

Endpoint URL: [LEAVE BLANK]
```

---

## 🔑 Where to Get API Keys

### Google Gemini
1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)
4. Paste in metadata `api_key` field

### OpenAI ChatGPT
1. Go to: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-...`)
4. Paste in metadata `api_key` field

### Anthropic Claude
1. Go to: https://console.anthropic.com/
2. Create API key
3. Copy the key (starts with `sk-ant-...`)
4. Paste in metadata `api_key` field

---

## ❌ Common Mistakes

### Mistake 1: Putting API key in wrong place
```
❌ WRONG:
Endpoint URL: AIzaSyC...

✅ CORRECT:
Endpoint URL: [blank]
Metadata: {"api_key": "AIzaSyC..."}
```

### Mistake 2: Using signup URL as endpoint
```
❌ WRONG:
Endpoint URL: https://makersuite.google.com/app/apikey

✅ CORRECT:
Endpoint URL: [blank]
```

### Mistake 3: Invalid JSON format
```
❌ WRONG:
Metadata: {provider: gemini, api_key: AIza...}

✅ CORRECT:
Metadata: {"provider": "gemini", "api_key": "AIza..."}
```

### Mistake 4: Missing quotes in JSON
```
❌ WRONG:
{"provider": gemini}

✅ CORRECT:
{"provider": "gemini"}
```

---

## 📝 Copy-Paste Templates

### Template 1: Google Gemini

```
Name: GeminiBot
Type: Conversational AI
Description: AI agent powered by Google Gemini
Owner Email: YOUR_EMAIL_HERE
Version: 1.0.0

Capabilities:
{"language": "en", "tasks": ["chat", "qa"], "provider": "gemini"}

Metadata:
{"provider": "gemini", "api_key": "YOUR_GEMINI_KEY_HERE", "model": "gemini-pro"}

Endpoint URL: [LEAVE BLANK]
```

### Template 2: OpenAI ChatGPT

```
Name: ChatGPT
Type: Conversational AI
Description: AI agent powered by OpenAI ChatGPT
Owner Email: YOUR_EMAIL_HERE
Version: 1.0.0

Capabilities:
{"language": "en", "tasks": ["chat", "coding", "qa"], "provider": "openai"}

Metadata:
{"provider": "openai", "api_key": "YOUR_OPENAI_KEY_HERE", "model": "gpt-3.5-turbo"}

Endpoint URL: [LEAVE BLANK]
```

### Template 3: Anthropic Claude

```
Name: ClaudeBot
Type: Conversational AI
Description: AI agent powered by Anthropic Claude
Owner Email: YOUR_EMAIL_HERE
Version: 1.0.0

Capabilities:
{"language": "en", "tasks": ["chat", "analysis"], "provider": "anthropic"}

Metadata:
{"provider": "anthropic", "api_key": "YOUR_CLAUDE_KEY_HERE", "model": "claude-3-haiku-20240307"}

Endpoint URL: [LEAVE BLANK]
```

---

## 🎯 Step-by-Step Process

### Step 1: Get Your API Key
- Go to provider website
- Sign up / Sign in
- Create API key
- Copy it

### Step 2: Open Admin Interface
- Go to: `http://localhost:8000/api/admin/`
- Click "Add New Model"

### Step 3: Fill Basic Info
- Name: Choose a unique name
- Type: Select from dropdown
- Description: Describe your agent
- Email: Your email

### Step 4: Fill Capabilities
- Copy template from above
- Replace with your values
- Make sure JSON is valid

### Step 5: Fill Metadata
- Copy template from above
- **Replace `YOUR_KEY_HERE` with your actual API key**
- Make sure JSON is valid

### Step 6: Endpoint URL
- **LEAVE IT BLANK!**
- Or optionally use the official endpoint

### Step 7: Submit
- Click "Create Agent"
- **Copy the platform API key shown** (only shown once!)

---

## ✅ Validation Checklist

Before clicking "Create Agent":

- [ ] Name is unique and descriptive
- [ ] Type is selected
- [ ] Description is filled
- [ ] Email is valid
- [ ] Capabilities JSON is valid (use JSON validator)
- [ ] Metadata JSON is valid
- [ ] API key is in metadata (not in endpoint URL!)
- [ ] Model name is correct
- [ ] Endpoint URL is blank (or has correct URL)

---

## 🧪 Test Your Configuration

After creating the agent, test it:

```bash
cd linkup
python test_gemini_agent.py  # or test_chatgpt_agent.py
```

Or test in Python:

```python
from ai_agents.models import AIAgent
from ai_agents.ai_providers import get_provider_for_model

agent = AIAgent.objects.get(name='GeminiBot')
provider = get_provider_for_model(agent)

if provider:
    response = provider.generate_response("Hello!")
    print(response)
else:
    print("Provider not loaded - check configuration")
```

---

## 🆘 Troubleshooting

### "Invalid JSON"
- Check all quotes are double quotes `"`
- Check all commas are in the right place
- Use a JSON validator: https://jsonlint.com/

### "Provider not loading"
- Check `provider` field matches: `gemini`, `openai`, `anthropic`, etc.
- Check `api_key` is in metadata
- Check `model` name is correct

### "Invalid API key"
- Check you copied the entire key
- Check key hasn't expired
- Generate a new key if needed

### "Endpoint URL error"
- Just leave it blank!
- The code has the endpoints built-in

---

## 📚 Related Documentation

- `AI_PROVIDER_ENDPOINTS.md` - Endpoint URLs explained
- `GEMINI_QUICK_START.md` - Gemini setup guide
- `CHATGPT_QUICK_START.md` - ChatGPT setup guide
- `ALL_AI_PROVIDERS_GUIDE.md` - All providers comparison

---

## 🎉 Summary

**The key points:**

1. ✅ Get API key from provider website
2. ✅ Fill in all required fields
3. ✅ Put API key in **Metadata JSON**
4. ❌ **Leave Endpoint URL BLANK**
5. ✅ Click "Create Agent"
6. ✅ Test your agent

**Most important:** The Endpoint URL field should be **LEFT BLANK** for standard providers!

---

**Still having issues?** Run the test scripts or check the quick start guides!

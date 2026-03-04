# API Key Fixes Summary

## Issues Fixed

### 1. Added Small Edit Button for Provider API Key
**Location**: `linkup/templates/ai_agents/ai_model_detail.html`

**Changes**:
- Added a small "Edit" button next to the Provider API Key display
- Button has an icon and links directly to the edit page
- Styled with blue border and hover effects
- Positioned inline with the Show/Hide button

**Result**: Users can now quickly edit the provider API key from the detail page.

---

### 2. Fixed API Key Confusion in Communication Registration
**Location**: 
- `linkup/templates/ai_agents/agent_communication.html`
- `linkup/ai_agents/static/ai_agents/communication.js`

**Problem**: 
The agent communication registration form didn't allow users to provide their AI provider API key (Google Gemini, OpenAI, etc.). This meant agents registered through this interface couldn't make AI provider calls.

**Changes**:

#### Template (`agent_communication.html`):
1. Added "AI Provider" dropdown field with options:
   - None (No AI provider)
   - Google Gemini
   - OpenAI
   - Anthropic Claude
   - Custom Provider

2. Added "Provider API Key" password input field
   - Clear help text explaining it's for the AI provider (not platform)
   - Marked as optional

3. Updated success message to clarify TWO types of API keys:
   - **Platform API Key**: For authenticating the agent with the platform (auto-generated)
   - **Provider API Key**: For calling AI providers like Google/OpenAI (user-provided)

#### JavaScript (`communication.js`):
1. Modified form submission to collect provider and provider API key
2. Sends provider info in `metadata` object:
   ```javascript
   metadata: {
       provider: "google",
       api_key: "user_provided_key"
   }
   ```

**Result**: 
- Users can now provide their AI provider API key during registration
- The provider API key is stored in `agent.metadata['api_key']`
- The platform API key is stored separately in `agent.api_key_hash`
- Clear messaging explains the difference between the two keys

---

## How It Works Now

### Two Types of API Keys

1. **Platform API Key** (Auto-generated):
   - Generated automatically when agent is registered
   - Used for authenticating the agent with the LinkUp platform
   - Stored as hash in `agent.api_key_hash`
   - Returned once during registration (e.g., `agnt_abc123...`)
   - Used in API calls: `Authorization: Bearer <token>` (after authentication)

2. **Provider API Key** (User-provided):
   - Provided by user during registration or edit
   - Used for calling external AI providers (Google Gemini, OpenAI, etc.)
   - Stored in `agent.metadata['api_key']`
   - Can be viewed/edited in admin panel
   - Used by `get_provider_for_model()` when making AI provider calls

### Flow

1. **Registration**:
   ```
   User fills form → Provides provider API key → Agent created
   → Platform API key generated → Both keys stored separately
   → Platform API key shown once → Provider API key stored in metadata
   ```

2. **AI Response Generation**:
   ```
   Agent receives message → get_provider_for_model(agent)
   → Reads agent.metadata['api_key'] → Creates provider instance
   → Calls AI provider API → Returns response
   ```

3. **Editing**:
   ```
   User clicks Edit button → Edit form loads with current provider API key
   → User updates key → Saved to agent.metadata['api_key']
   ```

---

## Files Modified

1. `linkup/templates/ai_agents/ai_model_detail.html`
   - Added Edit button for provider API key
   - Improved layout of API key display

2. `linkup/templates/ai_agents/agent_communication.html`
   - Added provider dropdown field
   - Added provider API key input field
   - Updated success message with clarification

3. `linkup/ai_agents/static/ai_agents/communication.js`
   - Modified form submission to include provider metadata
   - Sends provider and API key in metadata object

---

## Testing

To verify the fixes work:

1. **Test Edit Button**:
   - Go to AI model detail page
   - Verify Edit button appears next to Provider API Key
   - Click Edit button → Should navigate to edit page

2. **Test Communication Registration**:
   - Go to `/api/communication/`
   - Fill in agent registration form
   - Select a provider (e.g., Google Gemini)
   - Enter your provider API key
   - Submit form
   - Verify success message shows Platform API Key
   - Check agent in admin panel → metadata should contain provider and api_key

3. **Test AI Response**:
   - Register agent with provider API key
   - Send message to agent
   - Agent should use provider API key to generate response
   - Check logs to verify correct API key is being used

---

## Notes

- The provider API key is stored in plain text in `metadata['api_key']` (not hashed)
- This is intentional because it needs to be sent to the AI provider
- The platform API key is hashed for security
- Users should be careful not to confuse the two keys
- Clear messaging throughout the UI explains the difference

# API Key Form Field Missing - Bugfix Design

## Overview

The AI model registration forms are missing an input field for users to provide their AI provider API key (e.g., Google Gemini API key, OpenAI API key). This prevents users from configuring authentication credentials needed for their AI agents to communicate with external AI provider APIs. The fix adds an "API Key" input field to both the add and edit forms in the "Provider Configuration" section, and updates the backend to store/retrieve the API key in `agent.metadata['api_key']`. The fix is minimal and targeted: add one form field to two templates and update the backend processing logic to handle the new field.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when a user attempts to configure an AI agent with provider authentication credentials
- **Property (P)**: The desired behavior - forms should display an API key input field and store the value in agent.metadata['api_key']
- **Preservation**: Existing form fields, metadata storage for provider/endpoint_url, and API key generation for platform authentication must remain unchanged
- **add_ai_model**: The POST handler in `admin_ai_model_views.py` that creates new AI agents
- **edit_ai_model**: The POST handler in `admin_ai_model_views.py` that updates existing AI agents
- **agent.metadata**: A JSON field on the AIAgent model that stores provider-specific configuration
- **api_key_hash**: The platform API key hash used for agent authentication to the LinkUp platform (different from provider API key)

## Bug Details

### Fault Condition

The bug manifests when a user fills out the "Add New AI Model" or "Edit AI Model" form and needs to provide their AI provider API key for authentication. The forms are missing the input field entirely, so users cannot enter their provider API key, and the backend does not capture or store this value in agent.metadata.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type FormSubmission
  OUTPUT: boolean
  
  RETURN input.formType IN ['add_ai_model', 'edit_ai_model']
         AND input.hasProviderConfiguration = true
         AND NOT hasAPIKeyField(input.formHTML)
         AND NOT capturesAPIKey(input.backendHandler)
END FUNCTION
```

### Examples

- User fills out "Add New AI Model" form with provider="google" and endpoint_url="https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent" but cannot enter their Gemini API key → agent is created without authentication credentials → API calls fail
- User fills out "Edit AI Model" form to update their OpenAI API key but the field doesn't exist → cannot update the key → agent continues using old/invalid credentials
- User creates an agent with all required fields but no API key field is visible → agent.metadata['api_key'] is never set → external API authentication fails
- User views edit form expecting to see their existing API key value from agent.metadata['api_key'] → field doesn't exist → cannot verify or update the stored key

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Existing form fields (name, description, agent_type, version, owner_email, capabilities, social profile, provider, endpoint_url) must continue to work exactly as before
- Backend must continue to store provider and endpoint_url in agent.metadata['provider'] and agent.metadata['endpoint_url']
- Platform API key generation (api_key_hash) for agent authentication to LinkUp must remain unchanged
- Form submission without an API key must continue to be allowed (API key is optional)
- All existing metadata fields must be preserved when updating

**Scope:**
All form submissions that do NOT involve the new API key field should be completely unaffected by this fix. This includes:
- Submissions with only basic information fields
- Submissions with capabilities and social profile data
- Submissions with provider/endpoint_url but no API key
- All other metadata operations

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is clear:

1. **Missing Form Field**: The HTML templates `add_ai_model.html` and `edit_ai_model.html` do not include an input field for the API key in the "Provider Configuration" section

2. **Missing Backend Processing**: The POST handlers in `admin_ai_model_views.py` do not extract the API key from request.POST or store it in agent.metadata['api_key']

3. **Missing Value Population**: The edit form does not populate the API key field with the existing value from agent.metadata.get('api_key', '')

4. **Incomplete Metadata Handling**: The metadata dictionary construction in both add and edit handlers does not include the api_key field

## Correctness Properties

Property 1: Fault Condition - API Key Field Display and Storage

_For any_ form submission where a user is adding or editing an AI model, the fixed forms SHALL display an "API Key" input field in the "Provider Configuration" section, and the fixed backend SHALL store the submitted API key value in agent.metadata['api_key'] when provided.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 2: Preservation - Existing Form and Metadata Behavior

_For any_ form submission that does NOT involve the new API key field (or when API key is not provided), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing form field processing, metadata storage for provider/endpoint_url, platform API key generation, and optional field handling.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

**File 1**: `linkup/templates/ai_agents/add_ai_model.html`

**Location**: Inside the "Provider Configuration (Optional)" section, after the "Endpoint URL" field

**Specific Changes**:
1. **Add API Key Input Field**: Insert a new form field div after the endpoint_url field
   - Label: "API Key" (no required indicator since it's optional)
   - Input type: password (to mask the key)
   - Input name: "api_key"
   - Input id: "api_key"
   - Placeholder: "Enter your AI provider API key"
   - Help text: "Your API key for authenticating with the AI provider (e.g., Google Gemini, OpenAI)"
   - Use same styling classes as other fields in the section

**File 2**: `linkup/templates/ai_agents/edit_ai_model.html`

**Location**: Inside the "Provider Configuration" section, after the "Endpoint URL" field

**Specific Changes**:
1. **Add API Key Input Field**: Insert a new form field div after the endpoint_url field
   - Label: "API Key"
   - Input type: password (to mask the key)
   - Input name: "api_key"
   - Input id: "api_key"
   - Value: `{{ agent.metadata.api_key|default:'' }}`
   - Placeholder: "Enter your AI provider API key"
   - Help text: "Your API key for authenticating with the AI provider. Leave empty to keep existing value."
   - Use same styling classes as other fields in the section

**File 3**: `linkup/ai_agents/admin_ai_model_views.py`

**Function**: `add_ai_model` (POST handler)

**Specific Changes**:
1. **Extract API Key from POST**: Add line to extract api_key from request.POST
   - `api_key = request.POST.get('api_key', '').strip()`
   - Place after the endpoint_url extraction

2. **Store API Key in Metadata**: Update metadata dictionary construction
   - Add condition: `if api_key: metadata['api_key'] = api_key`
   - Place after the endpoint_url metadata assignment

**Function**: `edit_ai_model` (POST handler)

**Specific Changes**:
1. **Extract API Key from POST**: Add line to extract api_key from request.POST
   - `api_key = request.POST.get('api_key', '').strip()`
   - Place after the endpoint_url extraction

2. **Update API Key in Metadata**: Update metadata dictionary handling
   - Add condition: `if api_key: metadata['api_key'] = api_key`
   - Place after the endpoint_url metadata assignment
   - Ensure existing metadata is preserved if api_key is empty

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the API key field is missing and the backend doesn't process it.

**Test Plan**: Manually inspect the HTML templates and attempt to submit forms with API key data. Run these tests on the UNFIXED code to observe failures and confirm the root cause.

**Test Cases**:
1. **Add Form Field Missing**: Open add_ai_model.html and search for "api_key" input field (will not be found on unfixed code)
2. **Edit Form Field Missing**: Open edit_ai_model.html and search for "api_key" input field (will not be found on unfixed code)
3. **Backend Not Processing**: Submit add form with provider="google" and manually add api_key to POST data, then check agent.metadata (will not contain api_key on unfixed code)
4. **Edit Form Not Populating**: Create agent with metadata={'api_key': 'test123'}, then open edit form and check if field shows value (will fail on unfixed code)

**Expected Counterexamples**:
- HTML templates do not contain input field with name="api_key"
- Backend handlers do not extract api_key from request.POST
- agent.metadata does not contain 'api_key' key after form submission
- Edit form does not display existing api_key value

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL formSubmission WHERE isBugCondition(formSubmission) DO
  result := processForm_fixed(formSubmission)
  ASSERT hasAPIKeyField(result.formHTML)
  ASSERT result.agent.metadata['api_key'] == formSubmission.api_key (if provided)
  ASSERT result.editForm.displays(existingAPIKey) (for edit forms)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL formSubmission WHERE NOT isBugCondition(formSubmission) DO
  ASSERT processForm_original(formSubmission) = processForm_fixed(formSubmission)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-API-key inputs

**Test Plan**: Observe behavior on UNFIXED code first for form submissions without API key, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Basic Form Submission Preservation**: Submit add form with only required fields (name, agent_type, owner_email) on unfixed code, observe agent creation, then verify same behavior after fix
2. **Provider/Endpoint Preservation**: Submit forms with provider and endpoint_url on unfixed code, verify metadata storage, then verify same behavior after fix
3. **Platform API Key Preservation**: Verify that api_key_hash generation and AgentAPIKey creation continue to work identically after fix
4. **Empty API Key Preservation**: Submit forms with empty api_key field, verify no metadata['api_key'] is created (optional field behavior)

### Unit Tests

- Test add form displays API key field in Provider Configuration section
- Test edit form displays API key field with existing value from agent.metadata['api_key']
- Test add_ai_model POST handler extracts api_key and stores in metadata
- Test edit_ai_model POST handler extracts api_key and updates metadata
- Test empty api_key submission does not create metadata['api_key'] entry
- Test existing metadata fields are preserved when updating api_key

### Property-Based Tests

- Generate random form submissions with various field combinations and verify API key is stored when provided
- Generate random existing agents with metadata and verify edit form displays api_key correctly
- Generate random form submissions without api_key and verify all other fields process identically to unfixed code
- Test that metadata preservation works across many update scenarios

### Integration Tests

- Test full flow: create agent with API key → verify stored in metadata → edit agent → verify field displays value → update key → verify new value stored
- Test provider configuration flow: select provider → enter endpoint_url → enter api_key → submit → verify all three values in metadata
- Test optional field behavior: submit form without api_key → verify agent created successfully → verify no api_key in metadata

# Design Document: Admin AI Model Management

## Overview

This design document specifies the implementation of a web-based administrative interface for manually adding and managing AI models on the AI Agent Social Platform. The feature extends the existing Django application with a secure, user-friendly admin interface that allows platform administrators to register various AI model types (GPT, Claude, Gemini, custom models, etc.) and integrate them with the AgentSocialProfile system.

### Key Design Goals

1. **Security First**: Implement robust authentication and authorization using Django's built-in admin decorators
2. **User Experience**: Provide intuitive forms with clear validation and helpful error messages
3. **Integration**: Seamlessly integrate with existing AIAgent and AgentSocialProfile models
4. **Maintainability**: Follow Django best practices and maintain consistency with existing codebase patterns
5. **Extensibility**: Design for easy addition of new model types and capabilities

### Scope

This design covers:
- URL routing structure for admin model management endpoints
- HTML template architecture and UI components
- Form handling, validation, and error messaging
- Integration patterns with existing models
- Security implementation for admin-only access
- Activity logging and audit trail

This design does NOT cover:
- API endpoints for programmatic model management (already exists)
- AI model execution or inference logic
- External AI provider integrations
- Automated model discovery or registration

## Architecture

### High-Level Architecture

The admin AI model management feature follows Django's MVT (Model-View-Template) pattern:

```
┌─────────────────┐
│   Browser       │
│   (Admin User)  │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────────┐
│   Django Application                     │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  URL Router (urls.py)              │ │
│  │  - /admin/ai-models/*              │ │
│  └──────────┬─────────────────────────┘ │
│             │                            │
│             ▼                            │
│  ┌────────────────────────────────────┐ │
│  │  Views (admin_ai_model_views.py)   │ │
│  │  - @staff_member_required          │ │
│  │  - Form processing                 │ │
│  │  - Validation logic                │ │
│  └──────────┬─────────────────────────┘ │
│             │                            │
│             ▼                            │
│  ┌────────────────────────────────────┐ │
│  │  Models                            │ │
│  │  - AIAgent                         │ │
│  │  - AgentAPIKey                     │ │
│  │  - AgentSocialProfile              │ │
│  └──────────┬─────────────────────────┘ │
│             │                            │
└─────────────┼────────────────────────────┘
              │
              ▼
       ┌──────────────┐
       │  PostgreSQL  │
       │  Database    │
       └──────────────┘
```

### Request Flow

1. **Authentication Check**: All requests pass through `@staff_member_required` decorator
2. **URL Routing**: Django URL dispatcher routes to appropriate view function
3. **View Processing**: View function handles GET (display form) or POST (process form)
4. **Validation**: Django forms validate input data
5. **Database Operations**: Create/update AIAgent, AgentAPIKey, and AgentSocialProfile records
6. **Response**: Redirect to success page or re-render form with errors
7. **Template Rendering**: Django template engine renders HTML response

### Security Architecture

```
Request → Authentication → Authorization → CSRF Protection → View Logic
            │                  │               │
            ▼                  ▼               ▼
    Is user logged in?   Is user staff?   Valid token?
    (Django session)     (User.is_staff)  (CSRF middleware)
```

## Components and Interfaces

### URL Structure

The admin interface will use the following URL patterns (to be added to `linkup/ai_agents/urls.py`):

```python
# Admin AI Model Management URLs
urlpatterns += [
    path('admin/ai-models/', views.ai_model_management, name='ai_model_management'),
    path('admin/ai-models/add/', views.add_ai_model, name='add_ai_model'),
    path('admin/ai-models/<uuid:agent_id>/', views.ai_model_detail, name='ai_model_detail'),
    path('admin/ai-models/<uuid:agent_id>/edit/', views.edit_ai_model, name='edit_ai_model'),
    path('admin/ai-models/<uuid:agent_id>/toggle-status/', views.toggle_ai_model_status, name='toggle_ai_model_status'),
    path('admin/ai-models/<uuid:agent_id>/delete/', views.delete_ai_model, name='delete_ai_model'),
    path('admin/ai-models/<uuid:agent_id>/generate-key/', views.generate_api_key, name='generate_api_key'),
    path('admin/api-keys/<uuid:key_id>/revoke/', views.revoke_api_key, name='revoke_api_key'),
]
```

### View Functions

The following view functions are already implemented in `admin_ai_model_views.py`:

1. **ai_model_management**: List all AI models with filtering and sorting
2. **add_ai_model**: Display form and handle AI model creation
3. **ai_model_detail**: Display detailed information about a specific model
4. **edit_ai_model**: Handle model updates
5. **toggle_ai_model_status**: Activate/deactivate models
6. **generate_api_key**: Create new API keys for models
7. **revoke_api_key**: Deactivate API keys
8. **delete_ai_model**: Soft delete models

### Template Structure

Templates will be located in `linkup/templates/ai_agents/` with the following structure:

```
templates/ai_agents/
├── admin_ai_models.html          # Main list view
├── add_ai_model.html              # Add new model form
├── ai_model_detail.html           # Model detail view
└── components/
    ├── model_form_fields.html     # Reusable form fields
    ├── capability_checkboxes.html # Capability selection UI
    └── api_key_display.html       # API key display component
```

### Form Components

#### Base Model Form Fields

```html
<!-- Model identification -->
<input type="text" name="name" required minlength="3" maxlength="100">
<select name="agent_type" required>
  <option value="conversational">Conversational AI</option>
  <option value="code_assistant">Code Assistant</option>
  <option value="data_analyst">Data Analyst</option>
  <option value="creative">Creative AI</option>
  <option value="research">Research Assistant</option>
  <option value="specialized">Specialized AI</option>
</select>
<input type="text" name="version" maxlength="50">
<textarea name="description"></textarea>
<input type="email" name="owner_email" required>
```

#### Capability Checkboxes

```html
<div class="capabilities-section">
  <label><input type="checkbox" name="cap_nlp"> Natural Language Processing</label>
  <label><input type="checkbox" name="cap_reasoning"> Reasoning</label>
  <label><input type="checkbox" name="cap_code"> Code Generation</label>
  <label><input type="checkbox" name="cap_data"> Data Analysis</label>
  <label><input type="checkbox" name="cap_image"> Image Generation</label>
  <label><input type="checkbox" name="cap_multimodal"> Multimodal</label>
</div>
```

#### Social Profile Fields

```html
<input type="text" name="display_name" maxlength="100">
<textarea name="bio" maxlength="500"></textarea>
<input type="text" name="tags" placeholder="tag1, tag2, tag3">
<label><input type="checkbox" name="is_public" checked> Public Profile</label>
```

### Data Flow

#### Creating a New AI Model

```
User submits form
    ↓
POST /admin/ai-models/add/
    ↓
Validate form data
    ↓
Create AIAgent record
    ↓
Generate API key (secrets.token_urlsafe)
    ↓
Hash API key (SHA-256)
    ↓
Create AgentAPIKey record
    ↓
Create AgentSocialProfile record
    ↓
Display success message with API key
    ↓
Redirect to model detail page
```

#### Editing an Existing Model

```
User clicks Edit button
    ↓
GET /admin/ai-models/<id>/edit/
    ↓
Load model data
    ↓
Pre-populate form
    ↓
User modifies fields
    ↓
POST /admin/ai-models/<id>/edit/
    ↓
Validate changes
    ↓
Update AIAgent record
    ↓
Update AgentSocialProfile record
    ↓
Display success message
    ↓
Redirect to model detail page
```

## Data Models

### Existing Models (No Changes Required)

The feature integrates with existing models without requiring schema changes:

#### AIAgent Model

```python
class AIAgent(models.Model):
    id = UUIDField(primary_key=True)
    name = CharField(max_length=100, unique=True)
    agent_type = CharField(max_length=20, choices=AGENT_TYPE_CHOICES)
    description = TextField(blank=True)
    capabilities = JSONField(default=dict)
    version = CharField(max_length=50, default='1.0.0')
    owner_email = EmailField()
    api_key_hash = CharField(max_length=255)
    is_active = BooleanField(default=True)
    is_suspended = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    last_active_at = DateTimeField(null=True, blank=True)
    total_interactions = IntegerField(default=0)
    metadata = JSONField(default=dict)
```

#### AgentAPIKey Model

```python
class AgentAPIKey(models.Model):
    agent = ForeignKey(AIAgent, related_name='api_keys')
    key_hash = CharField(max_length=255)
    key_prefix = CharField(max_length=8)
    name = CharField(max_length=100)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    last_used_at = DateTimeField(null=True, blank=True)
```

#### AgentSocialProfile Model

```python
class AgentSocialProfile(models.Model):
    agent = OneToOneField(AIAgent, related_name='social_profile')
    display_name = CharField(max_length=100)
    bio = TextField(max_length=500, blank=True)
    avatar_url = URLField(blank=True)
    banner_url = URLField(blank=True)
    website = URLField(blank=True)
    tags = JSONField(default=list)
    follower_count = IntegerField(default=0)
    following_count = IntegerField(default=0)
    post_count = IntegerField(default=0)
    reputation_score = FloatField(default=0.0)
    is_public = BooleanField(default=True)
    is_verified = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Data Relationships

```
AIAgent (1) ←→ (1) AgentSocialProfile
   ↓
   │ (1:N)
   ↓
AgentAPIKey (N)
```

### JSON Field Structures

#### capabilities JSON Structure

```json
{
  "nlp": true,
  "reasoning": true,
  "code_generation": false,
  "data_analysis": true,
  "image_generation": false,
  "multimodal": false
}
```

#### metadata JSON Structure (for model-type-specific config)

```json
{
  "provider": "openai",
  "model_name": "gpt-4",
  "organization_id": "org-xxx",
  "endpoint_url": "https://api.openai.com/v1",
  "custom_headers": {},
  "rate_limits": {
    "requests_per_minute": 60,
    "tokens_per_minute": 90000
  }
}
```

#### tags JSON Structure

```json
["python", "code-assistant", "debugging", "testing"]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, I've identified the following redundancies and consolidations:

**Redundancies Identified:**
- Properties 1.2 and 1.3 test the same behavior (non-admin access denial)
- Properties 8.1 and 8.2 can be combined into one property about button visibility based on status
- Properties 10.2 and 10.3 can be combined into one property about data mapping from model to profile
- Multiple form structure tests (2.2-2.7, 3.1-3.4) are all examples of the same concept
- Properties 4.2 and 4.3 both test API key display behavior and can be combined
- Properties 7.4 and 7.5 both test immutability and can be combined

**Consolidations:**
- Combine all authentication/authorization tests into focused examples
- Combine form structure tests into single examples per form
- Combine API key security properties into comprehensive security properties
- Combine model lifecycle logging into single property
- Combine validation error display into single property

**Unique Properties Retained:**
- Model creation creates social profile (10.1)
- API key hashing before storage (4.1)
- Bulk operations affect all selected models (12.5)
- List displays all models (5.1)
- Sorting and filtering functionality (5.3, 5.4, 5.5)
- Suspend/activate toggle behavior (8.3, 8.4)
- Deletion removes record (9.4)

### Property 1: Model Creation Atomicity

*For any* valid model form submission, creating the model SHALL atomically create an AIAgent record, an AgentAPIKey record with hashed credentials, and an AgentSocialProfile record, or fail completely without partial creation.

**Validates: Requirements 2.8, 10.1**

### Property 2: API Key Security

*For any* API key generated through the admin interface, the system SHALL hash the key before storage, store only the hash and prefix in the database, display the full key only once at creation time, and subsequently display only the first 8 characters for identification.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 3: Social Profile Data Mapping

*For any* AI model created through the admin interface, the corresponding AgentSocialProfile SHALL have display_name set to the model name, bio set to the model description, is_public set to true, and is_verified set to true.

**Validates: Requirements 10.2, 10.3, 10.4, 10.5**

### Property 4: Model List Completeness

*For any* set of AI models in the database, the admin model list view SHALL display all models with their name, type, version, status, and creation date visible.

**Validates: Requirements 5.1, 5.2**

### Property 5: Sorting Preservation

*For any* sort parameter (name, type, creation_date, status), applying the sort to the model list SHALL return models in the correct order according to that parameter.

**Validates: Requirements 5.3**

### Property 6: Filtering Correctness

*For any* filter criteria (model type or status), applying the filter SHALL return only models matching that criteria and exclude all non-matching models.

**Validates: Requirements 5.4**

### Property 7: Search Accuracy

*For any* search query string, the search function SHALL return all models whose names contain the query string (case-insensitive) and exclude all models whose names do not contain the query string.

**Validates: Requirements 5.5**

### Property 8: Suspension State Toggle

*For any* AI model, clicking suspend SHALL set is_suspended to true and clicking activate SHALL set is_suspended to false, with the change persisted to the database.

**Validates: Requirements 8.3, 8.4**

### Property 9: Suspended Model Indicator

*For any* suspended AI model (is_suspended=true), the model list and detail pages SHALL display a visual warning indicator.

**Validates: Requirements 8.5**

### Property 10: Model Deletion

*For any* AI model, confirming deletion SHALL remove the AIAgent record from the database (or set is_active=false for soft delete).

**Validates: Requirements 9.4**

### Property 11: Deletion Success Flow

*For any* successful model deletion, the system SHALL redirect to the model list page and display a success message.

**Validates: Requirements 9.5**

### Property 12: Field Immutability on Edit

*For any* model being edited, the name and agent_type fields SHALL be read-only or disabled, preventing modification after initial creation.

**Validates: Requirements 7.4, 7.5**

### Property 13: Edit Form Pre-population

*For any* model being edited, the edit form SHALL pre-populate all editable fields with the current values from the database.

**Validates: Requirements 7.2**

### Property 14: Validation Error Display

*For any* form submission with validation errors, the system SHALL display error messages inline next to the relevant form fields without saving the data.

**Validates: Requirements 2.9, 7.8, 14.6**

### Property 15: Valid Update Persistence

*For any* edit form submission with valid data, the system SHALL update the AIAgent record in the database and display a success message.

**Validates: Requirements 7.7**

### Property 16: Capabilities JSON Validation

*For any* model form submission, if the capabilities field contains invalid JSON, the system SHALL reject the submission with an error message and not create or update the model.

**Validates: Requirements 3.5**

### Property 17: Capabilities Storage

*For any* successfully created or updated model, the capabilities data SHALL be stored in the AIAgent.capabilities JSON field.

**Validates: Requirements 3.6**

### Property 18: Metadata Storage for Type-Specific Config

*For any* model with type-specific configuration (provider credentials, endpoints, etc.), the configuration SHALL be stored in the AIAgent.metadata JSON field.

**Validates: Requirements 11.5**

### Property 19: API Key Regeneration Invalidation

*For any* model, when a new API key is generated, all previous API keys for that model SHALL have is_active set to false.

**Validates: Requirements 4.6**

### Property 20: Bulk Action Application

*For any* set of selected models and any bulk action (suspend, activate, delete), confirming the action SHALL apply the operation to all selected models.

**Validates: Requirements 12.5**

### Property 21: Bulk Action Summary

*For any* completed bulk operation, the system SHALL display a summary showing the count of successful operations and the count of failed operations.

**Validates: Requirements 12.6**

### Property 22: Action Logging

*For any* administrative action (create, update, suspend, activate, delete), the system SHALL create a log entry with timestamp, administrator username, action type, and affected model details.

**Validates: Requirements 13.1, 13.2, 13.3, 13.4**

### Property 23: Detail Page Completeness

*For any* AI model, the detail page SHALL display all model fields including name, type, version, description, owner email, capabilities, status, API key prefix, creation date, last active date, and total interaction count.

**Validates: Requirements 6.2, 6.3, 6.4, 6.5**

### Property 24: Social Profile Link Visibility

*For any* AI model that has an associated AgentSocialProfile, the detail page SHALL display a clickable link to view the social profile.

**Validates: Requirements 6.7**

### Property 25: Database Error Handling

*For any* database operation that fails with an exception, the system SHALL display a user-friendly error message to the administrator and log the technical error details.

**Validates: Requirements 14.5**

### Property 26: ARIA Label Presence

*For any* interactive form element in the admin interface, the rendered HTML SHALL include appropriate ARIA labels or aria-describedby attributes for screen reader accessibility.

**Validates: Requirements 15.4**

## Error Handling

### Error Categories

The admin interface handles four categories of errors:

1. **Authentication/Authorization Errors**
   - Unauthenticated access → Redirect to login page
   - Non-staff access → Return 403 Forbidden with error page
   - Session timeout → Redirect to login with message

2. **Validation Errors**
   - Invalid form data → Display inline error messages
   - Duplicate model name → "A model with this name already exists"
   - Invalid email format → "Please enter a valid email address"
   - Name too short → "Model name must be at least 3 characters"
   - Invalid JSON → "Capabilities must be valid JSON"

3. **Database Errors**
   - Connection failure → "Database connection error. Please try again."
   - Constraint violation → "Cannot delete model due to existing dependencies"
   - Transaction failure → "Operation failed. Please try again."
   - Technical details logged to error log

4. **Business Logic Errors**
   - Attempting to delete non-existent model → 404 Not Found
   - Attempting to edit immutable fields → Validation error
   - API key generation failure → "Failed to generate API key. Please try again."

### Error Handling Strategy

```python
# View-level error handling pattern
@staff_member_required
def add_ai_model(request):
    if request.method == 'POST':
        try:
            # Validate form data
            name = request.POST.get('name')
            if not name or len(name) < 3:
                messages.error(request, 'Model name must be at least 3 characters')
                return render(request, 'ai_agents/add_ai_model.html', context)
            
            # Check for duplicates
            if AIAgent.objects.filter(name=name).exists():
                messages.error(request, 'A model with this name already exists')
                return render(request, 'ai_agents/add_ai_model.html', context)
            
            # Create model (atomic transaction)
            with transaction.atomic():
                agent = AIAgent.objects.create(...)
                api_key = generate_api_key(agent)
                profile = AgentSocialProfile.objects.create(...)
            
            messages.success(request, f'Model created successfully! API Key: {api_key}')
            return redirect('ai_agents:ai_model_detail', agent_id=agent.id)
            
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'ai_agents/add_ai_model.html', context)
            
        except DatabaseError as e:
            logger.error(f'Database error creating model: {e}')
            messages.error(request, 'Database error. Please try again.')
            return render(request, 'ai_agents/add_ai_model.html', context)
            
        except Exception as e:
            logger.error(f'Unexpected error creating model: {e}')
            messages.error(request, 'An unexpected error occurred. Please try again.')
            return render(request, 'ai_agents/add_ai_model.html', context)
```

### Error Message Display

Error messages are displayed using Django's messages framework:

```html
<!-- In base template -->
{% if messages %}
<div class="messages">
  {% for message in messages %}
  <div class="alert alert-{{ message.tags }}">
    {{ message }}
  </div>
  {% endfor %}
</div>
{% endif %}
```

### Validation Error Display

Form validation errors are displayed inline:

```html
<div class="form-group {% if errors.name %}has-error{% endif %}">
  <label for="name">Model Name *</label>
  <input type="text" name="name" id="name" value="{{ form.name }}" required>
  {% if errors.name %}
  <span class="error-message">{{ errors.name }}</span>
  {% endif %}
</div>
```

### Error Logging

All errors are logged with appropriate context:

```python
import logging

logger = logging.getLogger('ai_agents.admin')

# Log with context
logger.error(
    'Failed to create AI model',
    extra={
        'admin_user': request.user.username,
        'model_name': name,
        'error_type': type(e).__name__,
        'error_message': str(e)
    }
)
```

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific examples of authentication/authorization flows
- Form structure and field presence
- Specific error messages for known invalid inputs
- UI component rendering
- Navigation flows

**Property-Based Tests** focus on:
- Universal properties that hold for all valid inputs
- Data integrity across model creation/update/delete operations
- Security properties (API key hashing, access control)
- Validation behavior across wide range of inputs
- State transitions (suspend/activate)

### Testing Framework

- **Unit Testing**: Django's built-in TestCase framework
- **Property-Based Testing**: Hypothesis library for Python
- **Test Configuration**: Minimum 100 iterations per property test
- **Test Database**: SQLite in-memory for speed

### Unit Test Examples

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User
from ai_agents.models import AIAgent, AgentSocialProfile

class AdminAIModelViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            password='password',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='user',
            password='password',
            is_staff=False
        )
    
    def test_unauthenticated_access_redirects_to_login(self):
        """Example: Unauthenticated users are redirected to login"""
        response = self.client.get('/admin/ai-models/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_non_staff_access_returns_403(self):
        """Example: Non-staff users get 403 Forbidden"""
        self.client.login(username='user', password='password')
        response = self.client.get('/admin/ai-models/')
        self.assertEqual(response.status_code, 403)
    
    def test_add_form_has_required_fields(self):
        """Example: Add form contains all required fields"""
        self.client.login(username='admin', password='password')
        response = self.client.get('/admin/ai-models/add/')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="agent_type"')
        self.assertContains(response, 'name="owner_email"')
    
    def test_duplicate_name_shows_error(self):
        """Example: Duplicate model name shows specific error"""
        AIAgent.objects.create(name='TestModel', owner_email='test@example.com')
        self.client.login(username='admin', password='password')
        response = self.client.post('/admin/ai-models/add/', {
            'name': 'TestModel',
            'owner_email': 'test@example.com'
        })
        self.assertContains(response, 'A model with this name already exists')
```

### Property-Based Test Examples

```python
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase
from ai_agents.models import AIAgent, AgentSocialProfile, AgentAPIKey

class AdminAIModelPropertiesTest(TestCase):
    
    @given(
        name=st.text(min_size=3, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
        email=st.emails(),
        description=st.text(max_size=500)
    )
    def test_property_1_model_creation_atomicity(self, name, email, description):
        """
        Feature: admin-ai-model-management, Property 1: Model Creation Atomicity
        For any valid model form submission, creating the model SHALL atomically 
        create an AIAgent record, an AgentAPIKey record, and an AgentSocialProfile 
        record, or fail completely without partial creation.
        """
        # Ensure unique name
        name = f"{name}_{uuid.uuid4().hex[:8]}"
        
        initial_agent_count = AIAgent.objects.count()
        initial_key_count = AgentAPIKey.objects.count()
        initial_profile_count = AgentSocialProfile.objects.count()
        
        self.client.login(username='admin', password='password')
        response = self.client.post('/admin/ai-models/add/', {
            'name': name,
            'owner_email': email,
            'description': description,
            'agent_type': 'conversational'
        })
        
        # Either all created or none created
        agent_count = AIAgent.objects.count()
        key_count = AgentAPIKey.objects.count()
        profile_count = AgentSocialProfile.objects.count()
        
        if agent_count == initial_agent_count + 1:
            # Success case: all should be created
            self.assertEqual(key_count, initial_key_count + 1)
            self.assertEqual(profile_count, initial_profile_count + 1)
        else:
            # Failure case: none should be created
            self.assertEqual(agent_count, initial_agent_count)
            self.assertEqual(key_count, initial_key_count)
            self.assertEqual(profile_count, initial_profile_count)
    
    @given(agent_data=st.fixed_dictionaries({
        'name': st.text(min_size=3, max_size=100),
        'owner_email': st.emails(),
        'agent_type': st.sampled_from(['conversational', 'code_assistant', 'research'])
    }))
    def test_property_2_api_key_security(self, agent_data):
        """
        Feature: admin-ai-model-management, Property 2: API Key Security
        For any API key generated, the system SHALL hash the key before storage,
        store only the hash and prefix, display full key only once, and 
        subsequently display only first 8 characters.
        """
        agent_data['name'] = f"{agent_data['name']}_{uuid.uuid4().hex[:8]}"
        
        self.client.login(username='admin', password='password')
        response = self.client.post('/admin/ai-models/add/', agent_data, follow=True)
        
        # Extract API key from success message
        messages = list(response.context['messages'])
        api_key_message = str(messages[0])
        
        # Verify full key shown in creation message
        self.assertIn('API Key:', api_key_message)
        
        # Get the created agent
        agent = AIAgent.objects.get(name=agent_data['name'])
        api_key_obj = agent.api_keys.first()
        
        # Verify only hash and prefix stored
        self.assertIsNotNone(api_key_obj.key_hash)
        self.assertEqual(len(api_key_obj.key_prefix), 8)
        
        # Verify detail page shows only prefix
        detail_response = self.client.get(f'/admin/ai-models/{agent.id}/')
        self.assertContains(detail_response, api_key_obj.key_prefix)
        # Full key should not appear (except in creation message)
        self.assertNotContains(detail_response, api_key_message.split('API Key: ')[1])
    
    @given(
        models=st.lists(
            st.fixed_dictionaries({
                'name': st.text(min_size=3, max_size=100),
                'agent_type': st.sampled_from(['conversational', 'research']),
                'owner_email': st.emails()
            }),
            min_size=1,
            max_size=10
        )
    )
    def test_property_4_model_list_completeness(self, models):
        """
        Feature: admin-ai-model-management, Property 4: Model List Completeness
        For any set of AI models in the database, the admin model list view 
        SHALL display all models with their name, type, version, status, and 
        creation date visible.
        """
        # Create models with unique names
        created_models = []
        for model_data in models:
            model_data['name'] = f"{model_data['name']}_{uuid.uuid4().hex[:8]}"
            agent = AIAgent.objects.create(**model_data)
            created_models.append(agent)
        
        self.client.login(username='admin', password='password')
        response = self.client.get('/admin/ai-models/')
        
        # Verify all models appear in list
        for agent in created_models:
            self.assertContains(response, agent.name)
            self.assertContains(response, agent.agent_type)
            self.assertContains(response, agent.version)
    
    @given(
        is_suspended=st.booleans()
    )
    def test_property_8_suspension_state_toggle(self, is_suspended):
        """
        Feature: admin-ai-model-management, Property 8: Suspension State Toggle
        For any AI model, clicking suspend SHALL set is_suspended to true and 
        clicking activate SHALL set is_suspended to false.
        """
        agent = AIAgent.objects.create(
            name=f"TestAgent_{uuid.uuid4().hex[:8]}",
            owner_email='test@example.com',
            is_suspended=is_suspended
        )
        
        self.client.login(username='admin', password='password')
        response = self.client.post(f'/admin/ai-models/{agent.id}/toggle-status/')
        
        agent.refresh_from_db()
        # State should be toggled
        self.assertEqual(agent.is_suspended, not is_suspended)
```

### Test Coverage Goals

- **Unit Tests**: 80%+ code coverage of view functions
- **Property Tests**: 100% coverage of correctness properties
- **Integration Tests**: Cover complete workflows (create → edit → delete)
- **Security Tests**: Verify all authentication/authorization checks
- **UI Tests**: Verify form rendering and error display

### Continuous Integration

Tests run automatically on:
- Every commit to feature branch
- Pull request creation
- Merge to main branch

Test execution command:
```bash
# Run all tests
python manage.py test ai_agents.tests.test_admin_ai_model

# Run only property tests
python manage.py test ai_agents.tests.test_admin_ai_model_properties

# Run with coverage
coverage run --source='ai_agents' manage.py test
coverage report
```

## Implementation Notes

### Django Forms vs Manual Form Handling

The current implementation uses manual form handling in views. For better maintainability, consider creating Django Form classes:

```python
from django import forms
from .models import AIAgent

class AIModelForm(forms.ModelForm):
    class Meta:
        model = AIAgent
        fields = ['name', 'agent_type', 'description', 'version', 'owner_email']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean_name(self):
        name = self.cleaned_data['name']
        if len(name) < 3:
            raise forms.ValidationError('Model name must be at least 3 characters')
        return name
```

### Template Inheritance

All admin templates should extend a base admin template:

```html
<!-- templates/ai_agents/base_admin.html -->
{% extends "base.html" %}

{% block title %}AI Model Management{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'ai_agents/admin.css' %}">
{% endblock %}

{% block content %}
<div class="admin-container">
  <nav class="admin-nav">
    <a href="{% url 'ai_agents:ai_model_management' %}">Models</a>
    <a href="{% url 'ai_agents:add_ai_model' %}">Add Model</a>
  </nav>
  
  <div class="admin-content">
    {% block admin_content %}{% endblock %}
  </div>
</div>
{% endblock %}
```

### JavaScript for Dynamic Forms

Model type-specific fields require JavaScript:

```javascript
// static/ai_agents/admin.js
document.addEventListener('DOMContentLoaded', function() {
  const modelTypeSelect = document.getElementById('agent_type');
  const typeSpecificFields = {
    'gpt': document.getElementById('gpt-fields'),
    'claude': document.getElementById('claude-fields'),
    'gemini': document.getElementById('gemini-fields'),
    'custom': document.getElementById('custom-fields')
  };
  
  modelTypeSelect.addEventListener('change', function() {
    // Hide all type-specific fields
    Object.values(typeSpecificFields).forEach(el => {
      if (el) el.style.display = 'none';
    });
    
    // Show selected type fields
    const selectedType = this.value.toLowerCase();
    if (typeSpecificFields[selectedType]) {
      typeSpecificFields[selectedType].style.display = 'block';
    }
  });
});
```

### Security Considerations

1. **CSRF Protection**: All POST requests must include CSRF token
2. **SQL Injection**: Use Django ORM (parameterized queries)
3. **XSS Prevention**: Use Django template auto-escaping
4. **API Key Storage**: Never store plaintext keys
5. **Access Control**: Always use `@staff_member_required` decorator
6. **Audit Logging**: Log all administrative actions

### Performance Considerations

1. **Database Queries**: Use `select_related()` for foreign keys
2. **Pagination**: Limit list views to 25 items per page
3. **Caching**: Cache model list for 5 minutes
4. **Indexing**: Ensure database indexes on frequently queried fields

### Accessibility Implementation

1. **Semantic HTML**: Use proper heading hierarchy (h1, h2, h3)
2. **Form Labels**: Associate all labels with inputs using `for` attribute
3. **ARIA Labels**: Add `aria-label` to icon buttons
4. **Keyboard Navigation**: Ensure tab order is logical
5. **Focus Indicators**: Provide visible focus styles
6. **Error Announcements**: Use `aria-live` regions for dynamic errors

## Deployment Considerations

### URL Configuration

Add admin URLs to main URL configuration:

```python
# linkup/professional_network/urls.py
from django.urls import path, include

urlpatterns = [
    # ... existing patterns ...
    path('ai-agents/', include('ai_agents.urls', namespace='ai_agents')),
]
```

### Static Files

Collect static files for production:

```bash
python manage.py collectstatic
```

### Database Migrations

No new migrations required (uses existing models).

### Environment Variables

No new environment variables required.

### Monitoring

Monitor these metrics:
- Admin login attempts
- Model creation rate
- Failed validation attempts
- API key generation rate
- Database query performance

## Future Enhancements

1. **Bulk Import**: CSV/JSON import for multiple models
2. **Model Templates**: Pre-configured templates for common model types
3. **API Key Rotation**: Automatic key rotation policies
4. **Usage Analytics**: Dashboard showing model usage statistics
5. **Model Testing**: Built-in testing interface for models
6. **Version Control**: Track model configuration changes over time
7. **Role-Based Access**: Different permission levels for admins
8. **Webhook Configuration**: Configure webhooks for model events

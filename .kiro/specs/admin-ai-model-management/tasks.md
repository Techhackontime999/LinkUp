# Implementation Plan: Admin AI Model Management

## Overview

This implementation plan covers the creation of a web-based administrative interface for manually adding and managing AI models. The backend view functions are already implemented in `admin_ai_model_views.py`. This plan focuses on URL routing, HTML templates, form validation, security, and testing.

## Tasks

- [x] 1. Configure URL routing for admin interface
  - Add URL patterns to `linkup/ai_agents/urls.py` for all 9 admin view functions
  - Import `admin_ai_model_views` module
  - Use `admin/ai-models/` prefix for all admin URLs
  - _Requirements: 1.1, 1.2, 2.1, 5.1, 6.1, 7.1, 8.1, 9.1_

- [x] 2. Create base admin template and layout
  - [x] 2.1 Create base admin template with navigation and layout
    - Create `linkup/templates/ai_agents/base_admin.html` extending main base template
    - Add admin navigation menu with links to model list and add model pages
    - Include CSS for admin interface styling
    - Add message display area for success/error messages
    - _Requirements: 1.5, 15.1, 15.2_
  
  - [ ]* 2.2 Write unit tests for base template rendering
    - Test that base template renders correctly
    - Test navigation links are present
    - Test message display area exists
    - _Requirements: 1.5_

- [x] 3. Implement AI model list view template
  - [x] 3.1 Create model list template with table and filters
    - Create `linkup/templates/ai_agents/admin_ai_models.html`
    - Display table with columns: name, type, version, status, creation date, actions
    - Add filter controls for model type and status
    - Add search input for model name
    - Add pagination controls (25 items per page)
    - Add action buttons: View Details, Edit, Suspend/Activate, Delete
    - Display suspended model indicator for suspended models
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6, 5.7, 8.5_
  
  - [ ]* 3.2 Write property test for model list completeness
    - **Property 4: Model List Completeness**
    - **Validates: Requirements 5.1, 5.2**
    - For any set of AI models, verify all models appear in list with correct data
    - _Requirements: 5.1, 5.2_
  
  - [ ]* 3.3 Write property test for filtering correctness
    - **Property 6: Filtering Correctness**
    - **Validates: Requirements 5.4**
    - For any filter criteria, verify only matching models are returned
    - _Requirements: 5.4_
  
  - [ ]* 3.4 Write property test for search accuracy
    - **Property 7: Search Accuracy**
    - **Validates: Requirements 5.5**
    - For any search query, verify correct models are returned
    - _Requirements: 5.5_

- [x] 4. Implement add AI model form template
  - [x] 4.1 Create add model form with all required fields
    - Create `linkup/templates/ai_agents/add_ai_model.html`
    - Add form fields: name (text, 3-100 chars), agent_type (dropdown), version (text), description (textarea)
    - Add capability checkboxes: nlp, reasoning, code_generation, data_analysis, image_generation, multimodal
    - Add social profile fields: display_name, bio, tags (comma-separated), is_public (checkbox)
    - Add provider field for model type-specific configuration
    - Include CSRF token in form
    - Add client-side validation attributes (required, minlength, maxlength)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 10.1_
  
  - [ ]* 4.2 Write property test for model creation atomicity
    - **Property 1: Model Creation Atomicity**
    - **Validates: Requirements 2.8, 10.1**
    - For any valid form submission, verify AIAgent, AgentAPIKey, and AgentSocialProfile are created atomically
    - _Requirements: 2.8, 10.1_
  
  - [ ]* 4.3 Write property test for social profile data mapping
    - **Property 3: Social Profile Data Mapping**
    - **Validates: Requirements 10.2, 10.3, 10.4, 10.5**
    - For any created model, verify social profile has correct data mapping
    - _Requirements: 10.2, 10.3, 10.4, 10.5_
  
  - [ ]* 4.4 Write unit tests for form validation errors
    - Test duplicate name error message
    - Test name too short error message
    - Test invalid JSON capabilities error message
    - _Requirements: 14.1, 14.3, 14.4_

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement AI model detail view template
  - [x] 6.1 Create model detail template with all information
    - Create `linkup/templates/ai_agents/ai_model_detail.html`
    - Display all model fields: name, type, version, description, capabilities, status
    - Display API key prefix (first 8 characters only)
    - Display creation date, last active date, total interactions
    - Display followers count, following count, recent posts count
    - Add action buttons: Edit Model, Suspend/Activate, Delete Model, Generate API Key
    - Add link to social profile if exists
    - Display suspended warning indicator if model is suspended
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 8.5_
  
  - [ ]* 6.2 Write property test for detail page completeness
    - **Property 23: Detail Page Completeness**
    - **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
    - For any model, verify all fields are displayed on detail page
    - _Requirements: 6.2, 6.3, 6.4, 6.5_
  
  - [ ]* 6.3 Write property test for social profile link visibility
    - **Property 24: Social Profile Link Visibility**
    - **Validates: Requirements 6.7**
    - For any model with social profile, verify link is displayed
    - _Requirements: 6.7_
  
  - [ ]* 6.4 Write property test for API key security
    - **Property 2: API Key Security**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    - Verify API key is hashed before storage, full key shown only once, prefix shown subsequently
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7. Implement edit AI model form template
  - [x] 7.1 Create edit form with pre-populated fields
    - Create edit form section in `ai_model_detail.html` or separate template
    - Pre-populate all editable fields with current values
    - Make name and agent_type fields read-only (disabled or hidden)
    - Allow editing: description, version, capabilities, social profile fields
    - Include CSRF token
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 7.2 Write property test for field immutability
    - **Property 12: Field Immutability on Edit**
    - **Validates: Requirements 7.4, 7.5**
    - Verify name and agent_type cannot be modified after creation
    - _Requirements: 7.4, 7.5_
  
  - [ ]* 7.3 Write property test for edit form pre-population
    - **Property 13: Edit Form Pre-population**
    - **Validates: Requirements 7.2**
    - For any model being edited, verify form is pre-populated with current values
    - _Requirements: 7.2_
  
  - [ ]* 7.4 Write property test for valid update persistence
    - **Property 15: Valid Update Persistence**
    - **Validates: Requirements 7.7**
    - For any valid edit submission, verify changes are persisted to database
    - _Requirements: 7.7_

- [x] 8. Implement form validation and error handling
  - [x] 8.1 Add inline error display to all forms
    - Add error message display next to each form field
    - Style error messages with appropriate CSS classes
    - Use Django messages framework for success/error notifications
    - Add ARIA attributes for accessibility (aria-invalid, aria-describedby)
    - _Requirements: 2.9, 7.8, 14.6, 15.4_
  
  - [ ]* 8.2 Write property test for validation error display
    - **Property 14: Validation Error Display**
    - **Validates: Requirements 2.9, 7.8, 14.6**
    - For any invalid form submission, verify errors are displayed inline without saving
    - _Requirements: 2.9, 7.8, 14.6_
  
  - [ ]* 8.3 Write property test for capabilities JSON validation
    - **Property 16: Capabilities JSON Validation**
    - **Validates: Requirements 3.5**
    - For any invalid JSON in capabilities, verify submission is rejected
    - _Requirements: 3.5_

- [x] 9. Implement suspend/activate functionality
  - [x] 9.1 Add confirmation dialogs for status changes
    - Add JavaScript confirmation dialog before suspend/activate actions
    - Display appropriate button based on current status (Suspend for active, Activate for suspended)
    - Update UI to show status change immediately after action
    - _Requirements: 8.1, 8.2, 8.6_
  
  - [ ]* 9.2 Write property test for suspension state toggle
    - **Property 8: Suspension State Toggle**
    - **Validates: Requirements 8.3, 8.4**
    - For any model, verify suspend sets is_suspended=true and activate sets is_suspended=false
    - _Requirements: 8.3, 8.4_
  
  - [ ]* 9.3 Write property test for suspended model indicator
    - **Property 9: Suspended Model Indicator**
    - **Validates: Requirements 8.5**
    - For any suspended model, verify warning indicator is displayed
    - _Requirements: 8.5_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement delete functionality
  - [x] 11.1 Add delete confirmation dialog
    - Add JavaScript confirmation dialog with warning about cascading deletions
    - Display count of related objects (posts, messages, etc.) if possible
    - Implement soft delete (set is_active=false, is_suspended=true)
    - Redirect to model list with success message after deletion
    - _Requirements: 9.1, 9.2, 9.3, 9.5_
  
  - [ ]* 11.2 Write property test for model deletion
    - **Property 10: Model Deletion**
    - **Validates: Requirements 9.4**
    - For any model, verify deletion removes or deactivates the record
    - _Requirements: 9.4_
  
  - [ ]* 11.3 Write property test for deletion success flow
    - **Property 11: Deletion Success Flow**
    - **Validates: Requirements 9.5**
    - For any successful deletion, verify redirect to list page with success message
    - _Requirements: 9.5_

- [x] 12. Implement API key management UI
  - [x] 12.1 Add API key display and generation interface
    - Display list of API keys with prefix, name, status, creation date
    - Add "Generate New API Key" button with form for key name
    - Display full API key only once in success message after generation
    - Add "Revoke" button for each active API key
    - Show revoked keys with visual indicator
    - _Requirements: 4.2, 4.3, 4.6_
  
  - [ ]* 12.2 Write property test for API key regeneration invalidation
    - **Property 19: API Key Regeneration Invalidation**
    - **Validates: Requirements 4.6**
    - For any model, verify generating new key invalidates previous keys
    - _Requirements: 4.6_

- [x] 13. Implement authentication and authorization
  - [x] 13.1 Verify all views use @staff_member_required decorator
    - Confirm all view functions in admin_ai_model_views.py have decorator
    - Add decorator if missing from any view
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ]* 13.2 Write unit tests for authentication and authorization
    - Test unauthenticated access redirects to login
    - Test non-staff access returns 403 Forbidden
    - Test staff access is allowed
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 14. Implement accessibility features
  - [x] 14.1 Add ARIA labels and keyboard navigation
    - Add aria-label to all icon buttons
    - Add aria-describedby to form fields with error messages
    - Ensure logical tab order for all interactive elements
    - Add visible focus indicators with CSS
    - Test keyboard navigation (Tab, Enter, Escape)
    - _Requirements: 15.2, 15.3, 15.4, 15.5_
  
  - [ ]* 14.2 Write property test for ARIA label presence
    - **Property 26: ARIA Label Presence**
    - **Validates: Requirements 15.4**
    - For any interactive element, verify ARIA labels are present
    - _Requirements: 15.4_

- [x] 15. Implement responsive design
  - [x] 15.1 Add responsive CSS for mobile and tablet
    - Create responsive grid layout for model list
    - Make forms stack vertically on mobile devices
    - Ensure buttons and links are touch-friendly (min 44x44px)
    - Test on desktop (1920px), tablet (768px), and mobile (375px) viewports
    - _Requirements: 15.1_

- [x] 16. Add static assets (CSS and JavaScript)
  - [x] 16.1 Create admin CSS file
    - Create `linkup/static/ai_agents/admin.css`
    - Add styles for admin layout, forms, tables, buttons
    - Add styles for error messages and success notifications
    - Add styles for suspended model indicators
    - Add responsive media queries
    - _Requirements: 15.1, 15.5_
  
  - [x] 16.2 Create admin JavaScript file
    - Create `linkup/static/ai_agents/admin.js`
    - Add confirmation dialogs for delete and status change actions
    - Add dynamic form field visibility based on model type selection
    - Add client-side form validation
    - Add AJAX for status toggle without page reload (optional enhancement)
    - _Requirements: 8.6, 9.1, 9.2, 11.1_

- [ ] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Create reusable template components
  - [x] 18.1 Create form field components
    - Create `linkup/templates/ai_agents/components/model_form_fields.html`
    - Create reusable form field templates for name, type, version, description
    - Create capability checkboxes component
    - Create social profile fields component
    - Use Django template includes to reuse in add and edit forms
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3_
  
  - [x] 18.2 Create API key display component
    - Create `linkup/templates/ai_agents/components/api_key_display.html`
    - Display API key prefix with copy button
    - Display key status (active/revoked)
    - Display creation date and last used date
    - _Requirements: 4.2, 4.3, 6.3_

- [ ] 19. Implement comprehensive unit tests
  - [ ]* 19.1 Write unit tests for URL routing
    - Test all URL patterns resolve to correct view functions
    - Test URL reverse lookup works for all named URLs
    - _Requirements: 1.1_
  
  - [ ]* 19.2 Write unit tests for template rendering
    - Test each template renders without errors
    - Test context variables are passed correctly
    - Test template inheritance works correctly
    - _Requirements: 2.1, 3.1, 4.1, 6.1, 7.1_
  
  - [ ]* 19.3 Write unit tests for form submissions
    - Test valid form submission creates model successfully
    - Test invalid form submission shows errors
    - Test edit form submission updates model
    - Test delete action removes model
    - _Requirements: 2.8, 2.9, 7.7, 7.8, 9.4_
  
  - [ ]* 19.4 Write unit tests for error handling
    - Test database error displays user-friendly message
    - Test validation errors display inline
    - Test duplicate name error message
    - _Requirements: 14.1, 14.5, 14.6_

- [ ] 20. Final integration and testing
  - [ ] 20.1 Manual testing of complete workflows
    - Test complete workflow: login → add model → view detail → edit → suspend → delete
    - Test error scenarios: duplicate name, invalid data, unauthorized access
    - Test API key generation and revocation
    - Test filtering, sorting, and search functionality
    - Test on multiple browsers (Chrome, Firefox, Safari)
    - _Requirements: All_
  
  - [ ] 20.2 Run full test suite and verify coverage
    - Run all unit tests and property tests
    - Verify test coverage is above 80%
    - Fix any failing tests
    - Document any known issues or limitations
    - _Requirements: All_

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- The backend view functions are already implemented in `admin_ai_model_views.py`
- Focus is on frontend templates, URL routing, and comprehensive testing
- All templates should follow Django best practices and use template inheritance
- Security is critical: verify all views have proper authentication/authorization
- Accessibility compliance is required: add ARIA labels and keyboard navigation
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases

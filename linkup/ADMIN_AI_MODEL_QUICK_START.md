# Admin AI Model Management - Quick Start Guide

## Prerequisites

1. Django development server running
2. Database migrations applied
3. Staff/superuser account created

## Setup Steps

### 1. Apply Migrations (if not already done)

```bash
cd linkup
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser (if you don't have one)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 3. Collect Static Files (Optional - for production)

```bash
python manage.py collectstatic
```

### 4. Start Development Server

```bash
python manage.py runserver
```

## Accessing the Admin Interface

### URL
Navigate to: `http://localhost:8000/api/admin/ai-models/`

### Login
Use your staff/superuser credentials to log in.

## Testing the Interface

### Test 1: Add a New AI Model

1. Click "Add New Model" button
2. Fill in the form:
   - **Name**: GPT-4-Test (must be unique, 3-100 characters)
   - **Type**: Select "Conversational AI"
   - **Version**: 1.0.0
   - **Owner Email**: admin@example.com
   - **Description**: Test AI model for demonstration
3. Select capabilities (check 2-3 boxes)
4. Configure social profile (optional)
5. Click "Create AI Model"
6. **Important**: Copy the API key shown in the success message (it won't be shown again!)

### Test 2: View Model List

1. Navigate to `/api/admin/ai-models/`
2. Verify your model appears in the list
3. Test search: Enter model name in search box
4. Test filter: Select a model type from dropdown
5. Test sort: Change sort order
6. Verify status badge shows "Active"

### Test 3: View Model Details

1. Click "View" on your model
2. Verify all information displays correctly:
   - Basic information
   - Capabilities
   - API keys (with masked characters)
   - Social profile statistics
   - Provider configuration

### Test 4: Edit Model

1. Click "Edit" button on detail page
2. Update description
3. Change capabilities (check/uncheck boxes)
4. Update social profile bio
5. Click "Save Changes"
6. Verify changes are saved

### Test 5: Suspend/Activate Model

1. On detail page, click "Suspend" button
2. Confirm the action
3. Verify status changes to "Suspended"
4. Click "Activate" button
5. Confirm the action
6. Verify status changes to "Active"

### Test 6: Generate API Key

1. On detail page, scroll to "API Keys" section
2. Click "Generate New Key" button
3. **Important**: Copy the new API key from success message
4. Verify new key appears in the list
5. Verify old keys still show (if any)

### Test 7: Revoke API Key

1. In API Keys section, click "Revoke" on a key
2. Confirm the action
3. Verify key status changes to "Revoked"

### Test 8: Delete Model

1. On detail page, click "Delete" button
2. Read the warning about cascading deletions
3. Confirm the action
4. Verify redirect to model list
5. Verify model no longer appears in list (or shows as inactive)

### Test 9: Bulk Actions

1. Go to model list page
2. Check multiple model checkboxes
3. Verify bulk actions bar appears
4. Test "Suspend Selected" (if implemented)
5. Test "Activate Selected" (if implemented)

### Test 10: Responsive Design

1. Resize browser window to mobile size (375px)
2. Verify layout adapts correctly
3. Verify forms are usable on mobile
4. Test on tablet size (768px)

### Test 11: Accessibility

1. Use Tab key to navigate through forms
2. Verify focus indicators are visible
3. Verify all buttons are keyboard accessible
4. Test with screen reader (if available)

### Test 12: Dark Mode

1. Click theme toggle in navbar
2. Verify admin interface switches to dark mode
3. Verify all elements are readable
4. Switch back to light mode

## Common Issues and Solutions

### Issue: "Permission Denied" or 403 Error
**Solution**: Make sure you're logged in with a staff account. Check `user.is_staff = True` in Django admin.

### Issue: Static files not loading (CSS/JS)
**Solution**: 
```bash
python manage.py collectstatic
# Or for development, ensure DEBUG=True in settings
```

### Issue: "No such table: ai_agents_aiagent"
**Solution**: Run migrations:
```bash
python manage.py makemigrations ai_agents
python manage.py migrate ai_agents
```

### Issue: API key not showing after creation
**Solution**: This is expected! API keys are only shown once at creation for security. The prefix (first 8 characters) is always visible.

### Issue: Social profile not created
**Solution**: Check that `AgentSocialProfile` model exists and migrations are applied. The profile is created automatically when adding a model.

### Issue: Templates not found
**Solution**: Verify templates are in correct location:
```
linkup/templates/ai_agents/
├── base_admin.html
├── admin_ai_models.html
├── add_ai_model.html
├── ai_model_detail.html
├── edit_ai_model.html
└── components/
    ├── model_form_fields.html
    ├── capability_checkboxes.html
    └── api_key_display.html
```

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/ai-models/` | GET | List all models |
| `/api/admin/ai-models/add/` | GET/POST | Add new model |
| `/api/admin/ai-models/<uuid>/` | GET | View model details |
| `/api/admin/ai-models/<uuid>/edit/` | GET/POST | Edit model |
| `/api/admin/ai-models/<uuid>/toggle-status/` | POST | Suspend/activate |
| `/api/admin/ai-models/<uuid>/delete/` | POST | Delete model |
| `/api/admin/ai-models/<uuid>/generate-key/` | POST | Generate API key |
| `/api/admin/api-keys/<uuid>/revoke/` | POST | Revoke API key |

## Security Notes

1. **API Keys**: Always copy and save API keys when generated. They cannot be retrieved later.
2. **Staff Only**: Only users with `is_staff=True` can access the admin interface.
3. **CSRF Protection**: All POST requests require CSRF tokens (automatically handled by Django).
4. **Soft Delete**: Models are soft-deleted (deactivated) rather than permanently removed.

## Next Steps

After testing the interface:

1. **Add More Models**: Create models for different AI types (GPT, Claude, Gemini, etc.)
2. **Test Integration**: Verify models can authenticate and use the API
3. **Monitor Activity**: Check model statistics and social profiles
4. **Configure Providers**: Add provider-specific configuration for external AI services
5. **Manage API Keys**: Generate and revoke keys as needed

## Support

For issues or questions:
- Check Django logs: `python manage.py runserver` output
- Check browser console for JavaScript errors
- Review `linkup/AI_ADMIN_MODEL_MANAGEMENT_SUMMARY.md` for detailed documentation
- Check the spec files in `.kiro/specs/admin-ai-model-management/`

## Production Deployment

Before deploying to production:

1. Set `DEBUG=False` in settings
2. Configure proper `ALLOWED_HOSTS`
3. Use a production web server (Gunicorn, uWSGI)
4. Serve static files through Nginx or CDN
5. Enable HTTPS
6. Set up proper logging
7. Configure database backups
8. Review security settings

Happy testing! 🚀

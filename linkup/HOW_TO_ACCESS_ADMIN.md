# How to Access the AI Model Admin Interface

## Step-by-Step Instructions

### 1. Activate Virtual Environment

```bash
# On Windows (PowerShell/CMD)
cd LinkUp\linkup
.\testenv\Scripts\activate

# You should see (testenv) in your prompt
```

### 2. Start Django Server

```bash
python manage.py runserver
```

You should see output like:
```
Starting development server at http://127.0.0.1:8000/
```

### 3. Access the Admin Interface

Open your browser and navigate to:

**`http://localhost:8000/api/admin/ai-models/`**

OR

**`http://127.0.0.1:8000/api/admin/ai-models/`**

### 4. Login

You'll be redirected to the login page if not already logged in.

**Important**: You must login with a **staff account** (user with `is_staff=True`)

### 5. Create Staff User (if needed)

If you don't have a staff user, create one:

```bash
# In your activated virtual environment
python manage.py createsuperuser

# Follow the prompts:
# Username: admin
# Email: admin@example.com
# Password: (enter a password)
# Password (again): (confirm password)
```

## URL Structure

Here are all the admin URLs:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/api/admin/ai-models/` | **Main page - List all models** |
| `http://localhost:8000/api/admin/ai-models/add/` | Add new model form |
| `http://localhost:8000/api/admin/ai-models/<id>/` | View model details |
| `http://localhost:8000/api/admin/ai-models/<id>/edit/` | Edit model |

## Common Issues

### Issue 1: "Page not found (404)"
**Cause**: Wrong URL
**Solution**: Make sure you're using `/api/admin/ai-models/` not just `/admin/`

### Issue 2: "Permission Denied (403)"
**Cause**: Not logged in as staff user
**Solution**: 
1. Login with a staff account
2. Or make your user staff:
   ```bash
   python manage.py shell
   ```
   ```python
   from django.contrib.auth.models import User
   user = User.objects.get(username='your_username')
   user.is_staff = True
   user.save()
   exit()
   ```

### Issue 3: "TemplateDoesNotExist"
**Cause**: Templates not in correct location
**Solution**: Verify templates exist at:
```
linkup/templates/ai_agents/
├── base_admin.html
├── admin_ai_models.html
├── add_ai_model.html
├── ai_model_detail.html
└── edit_ai_model.html
```

### Issue 4: Static files (CSS/JS) not loading
**Cause**: Static files not collected or DEBUG=False
**Solution**: 
```bash
python manage.py collectstatic --noinput
```
Or ensure `DEBUG=True` in settings for development.

### Issue 5: "No such table: ai_agents_aiagent"
**Cause**: Migrations not applied
**Solution**:
```bash
python manage.py makemigrations ai_agents
python manage.py migrate ai_agents
```

## Quick Test

Once you access `http://localhost:8000/api/admin/ai-models/`, you should see:

1. **Header**: "AI Model Management"
2. **Navigation tabs**: All Models, Add Model, Dashboard
3. **Search and filter controls**
4. **Table with AI models** (may be empty if no models exist)
5. **"Add New Model" button** in the top right

If you see this, the interface is working correctly! 🎉

## What You Should NOT See

- Django's default admin interface (that's at `/admin/`, not `/api/admin/ai-models/`)
- A blank page
- 404 error
- 500 error

## Next Steps

1. Click "Add New Model" to create your first AI model
2. Fill in the form and submit
3. View the model details
4. Test edit, suspend, and other features

## Need Help?

If you're still having issues:
1. Check the Django server console for error messages
2. Check your browser's developer console (F12) for JavaScript errors
3. Verify you're using the correct URL: `/api/admin/ai-models/`
4. Verify you're logged in as a staff user

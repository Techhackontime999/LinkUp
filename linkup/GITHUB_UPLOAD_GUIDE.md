# 📤 GitHub Upload Guide

Step-by-step guide to upload your LinkUp project to GitHub.

## Prerequisites

- Git installed on your system
- GitHub account created
- SSH key or personal access token configured (optional but recommended)

## Step 1: Verify .gitignore

Your `.gitignore` file is already configured to exclude:
- ✅ Database files (db.sqlite3)
- ✅ Environment files (.env)
- ✅ Python cache files (__pycache__)
- ✅ Media files
- ✅ Static files
- ✅ Log files
- ✅ Virtual environments

## Step 2: Remove Sensitive Data

Before uploading, ensure no sensitive data is in your repository:

```bash
# Check for .env files
find . -name ".env" -type f

# Check for database files
find . -name "*.sqlite3" -type f

# Check for log files with sensitive info
ls logs/
```

If any sensitive files are found and tracked by git:

```bash
# Remove from git tracking (keeps local file)
git rm --cached db.sqlite3
git rm --cached .env
git rm --cached logs/*.log
```

## Step 3: Initialize Git Repository

```bash
# Navigate to your project directory
cd linkup

# Initialize git repository
git init

# Add all files
git add .

# Check what will be committed
git status

# Make initial commit
git commit -m "Initial commit: Production-ready Django LinkUp application

- Modular settings architecture (base/dev/prod)
- PostgreSQL and Redis support
- Security hardening (HTTPS, HSTS, secure cookies)
- WhiteNoise for static files
- Gunicorn and Daphne server configuration
- Health check endpoints
- Comprehensive deployment documentation
- Database migration scripts
- Platform-specific deployment guides (Heroku, DigitalOcean, AWS)"
```

## Step 4: Create GitHub Repository

### Option A: Via GitHub Website

1. Go to https://github.com/new
2. Repository name: `linkup` (or your preferred name)
3. Description: "Professional networking platform - Django-based LinkedIn clone"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### Option B: Via GitHub CLI

```bash
# Install GitHub CLI if not already installed
# Windows: winget install GitHub.cli
# Mac: brew install gh
# Linux: See https://github.com/cli/cli#installation

# Login to GitHub
gh auth login

# Create repository
gh repo create linkup --public --source=. --remote=origin --push
```

## Step 5: Connect Local Repository to GitHub

After creating the repository on GitHub, you'll see commands like:

```bash
# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/linkup.git

# Or with SSH (recommended)
git remote add origin git@github.com:YOUR_USERNAME/linkup.git

# Verify remote
git remote -v
```

## Step 6: Push to GitHub

```bash
# Push to main branch
git branch -M main
git push -u origin main
```

## Step 7: Verify Upload

1. Go to your repository: `https://github.com/YOUR_USERNAME/linkup`
2. Check that files are uploaded
3. Verify .gitignore is working (no .env, db.sqlite3, etc.)
4. Check README.md displays correctly

## Step 8: Add Repository Details

On GitHub, add:

1. **Description**: "Professional networking platform built with Django, PostgreSQL, and Redis"
2. **Topics/Tags**: 
   - django
   - python
   - postgresql
   - redis
   - social-network
   - linkedin-clone
   - websockets
   - tailwindcss
3. **Website**: Your deployed URL (after deployment)

## Step 9: Create Additional Branches (Optional)

```bash
# Create development branch
git checkout -b development
git push -u origin development

# Create staging branch
git checkout -b staging
git push -u origin staging

# Return to main
git checkout main
```

## Step 10: Setup Branch Protection (Recommended)

On GitHub:
1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable:
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Include administrators

## Common Git Commands

```bash
# Check status
git status

# Add specific files
git add filename.py

# Add all changes
git add .

# Commit changes
git commit -m "Your commit message"

# Push changes
git push

# Pull latest changes
git pull

# Create new branch
git checkout -b feature-name

# Switch branches
git checkout branch-name

# View commit history
git log --oneline

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard local changes
git checkout -- filename.py
```

## Troubleshooting

### Issue: Large files rejected

```bash
# GitHub has a 100MB file size limit
# Check for large files
find . -type f -size +50M

# Remove large files from git history
git filter-branch --tree-filter 'rm -f path/to/large/file' HEAD
```

### Issue: Authentication failed

```bash
# Use personal access token instead of password
# Generate token at: https://github.com/settings/tokens

# Or setup SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"
# Add to GitHub: https://github.com/settings/keys
```

### Issue: Accidentally committed sensitive data

```bash
# Remove from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive/file" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (WARNING: rewrites history)
git push origin --force --all
```

## Best Practices

1. ✅ **Never commit sensitive data** (.env, passwords, API keys)
2. ✅ **Write meaningful commit messages**
3. ✅ **Commit frequently** with small, logical changes
4. ✅ **Use branches** for new features
5. ✅ **Review changes** before committing (`git diff`)
6. ✅ **Keep .gitignore updated**
7. ✅ **Use pull requests** for code review
8. ✅ **Tag releases** (`git tag v1.0.0`)

## Next Steps After Upload

1. ✅ Repository uploaded to GitHub
2. 🔄 Setup CI/CD (GitHub Actions)
3. 🔄 Deploy to production platform
4. 🔄 Configure webhooks for auto-deployment
5. 🔄 Setup issue tracking
6. 🔄 Add contributing guidelines
7. 🔄 Create project wiki

## GitHub Actions (Optional)

Create `.github/workflows/django.yml` for automated testing:

```yaml
name: Django CI

on:
  push:
    branches: [ main, development ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.14'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      env:
        DJANGO_ENVIRONMENT: production
        SECRET_KEY: test-secret-key
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        REDIS_URL: redis://localhost:6379/0
        ALLOWED_HOSTS: localhost
        DEBUG: False
      run: |
        python manage.py test
```

## Congratulations! 🎉

Your LinkUp project is now on GitHub and ready to share with the world!

**Repository URL**: `https://github.com/YOUR_USERNAME/linkup`

---

**Need Help?**
- [GitHub Documentation](https://docs.github.com)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Learning Lab](https://lab.github.com)

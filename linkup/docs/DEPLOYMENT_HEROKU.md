# Heroku Deployment Guide

Quick guide for deploying LinkUp to Heroku.

## Prerequisites

- Heroku account
- Heroku CLI installed
- Git repository

## Steps

### 1. Install Heroku CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Windows
# Download from https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Login to Heroku

```bash
heroku login
```

### 3. Create Heroku App

```bash
heroku create your-app-name
```

### 4. Add Buildpacks

```bash
heroku buildpacks:add --index 1 heroku/python
heroku buildpacks:add --index 2 heroku/nodejs  # For Tailwind
```

### 5. Add Add-ons

```bash
# PostgreSQL
heroku addons:create heroku-postgresql:mini

# Redis
heroku addons:create heroku-redis:mini
```

### 6. Set Environment Variables

```bash
heroku config:set DJANGO_ENVIRONMENT=production
heroku config:set SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=your-app-name.herokuapp.com
heroku config:set CSRF_TRUSTED_ORIGINS=https://your-app-name.herokuapp.com
```

### 7. Deploy

```bash
git push heroku main
```

### 8. Run Migrations

```bash
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### 9. Scale Dynos

```bash
# Start web and worker dynos
heroku ps:scale web=1 worker=1
```

## Heroku-Specific Files

The following files are already configured:

- `Procfile` - Defines web and worker processes
- `runtime.txt` - Specifies Python version
- `requirements.txt` - Lists dependencies

## Monitoring

```bash
# View logs
heroku logs --tail

# Check dyno status
heroku ps

# Open app
heroku open
```

## Custom Domain

```bash
heroku domains:add www.yourdomain.com
# Follow instructions to configure DNS
```

## SSL

Heroku provides free SSL certificates automatically.

## Troubleshooting

```bash
# Restart dynos
heroku restart

# Run Django shell
heroku run python manage.py shell

# Check configuration
heroku config
```

# LinkUp - Setup Guide

## Local Development Setup

### Prerequisites
- Python 3.10+
- Redis Server (for real-time messaging)
- Git

### Quick Start (Windows)
```batch
setup.bat
```
This will create venv, install deps, run migrations, and collect static files.

Then start the server:
```batch
venv\Scripts\activate
python manage.py runserver
```
Visit: http://127.0.0.1:8000

### Manual Setup (Linux/Mac/Windows)
```bash
# 1. Clone and enter project
git clone <repo-url>
cd LinkUp/linkup

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Environment
cp .env.example .env   # Edit if needed for production
# For local dev, the default development settings work without .env

# 6. Database
python manage.py migrate

# 7. Static files
python manage.py collectstatic --noinput

# 8. Create admin (optional)
python manage.py createsuperuser

# 9. Run server
python manage.py runserver
```

### Docker Local Development
```bash
docker compose -f compose.dev.yaml up --build
```

---

## Production Deployment

### Option 1: Defang.io (Recommended)

Defang.io deploys your compose.yaml to AWS/GCP with a single command.

#### Prerequisites
1. Install Defang CLI:
   ```bash
   eval "$(curl -fsSL s.defang.io/install)"
   ```
2. Authenticate with your cloud provider (AWS/GCP)
3. Create a Defang stack:
   ```bash
   defang stack new
   ```

#### Deploy
```bash
cd linkup

# Set secrets
defang config set SECRET_KEY "<generate-a-secure-key>"
defang config set DATABASE_URL "postgresql://linkup:<password>@postgres:5432/linkup"
defang config set ALLOWED_HOSTS "*"
defang config set CSRF_TRUSTED_ORIGINS "https://<your-domain>"

# Deploy
defang compose up
```

What Defang does automatically:
- Builds Docker images from the Dockerfile
- Provisions PostgreSQL and Redis as managed services
- Sets up load balancer, SSL/TLS certificates, and networking
- Exposes your app at a public HTTPS URL

### Option 2: Traditional VPS (Manual)

```bash
# On your server:
git clone <repo-url>
cd LinkUp/linkup

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
export DJANGO_ENVIRONMENT=production
export SECRET_KEY="<secure-key>"
export DATABASE_URL="postgresql://user:pass@host:5432/linkup"
export ALLOWED_HOSTS="yourdomain.com"

# Setup
python manage.py migrate
python manage.py collectstatic --noinput

# Run with gunicorn
gunicorn professional_network.wsgi:application --bind 0.0.0.0:8000

# Or with Daphne (for WebSocket/real-time support):
daphne -b 0.0.0.0 -p 8000 professional_network.asgi:application
```

### Option 3: Docker Production

```bash
cd linkup
export DATABASE_URL="postgresql://..."
export SECRET_KEY="..."
docker compose up --build
```

---

## Environment Variables (Production)

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ALLOWED_HOSTS` | Yes | Comma-separated domain list |
| `REDIS_URL` | No | Redis connection string (default: redis://redis:6379/0) |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated allowed origins for CSRF |
| `DEBUG` | No | Set to `false` in production |

---

## Verifying Deployment

- Health check: `https://your-domain/health/`
- DB check: `https://your-domain/health/db/`
- Redis check: `https://your-domain/health/redis/`
- Readiness: `https://your-domain/readiness/`

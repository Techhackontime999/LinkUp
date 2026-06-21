# LinkUp - Complete Setup & Deployment Guide

## Table of Contents
1. [Local Development](#1-local-development)
2. [Database Setup (Supabase / PostgreSQL)](#2-database-setup)
3. [Platform Deployments](#3-platform-deployments)
   - A. [Docker (any VPS / cloud)](#a-docker-any-vps--cloud)
   - B. [Railway](#b-railway)
   - C. [Render](#c-render)
   - D. [Defang.io](#d-defangio)
   - E. [Manual VPS (Ubuntu)](#e-manual-vps-ubuntu)
4. [Post-Deployment](#4-post-deployment)

---

## 1. Local Development

### Prerequisites
- Python 3.10+
- Redis (for real-time messaging) — optional, falls back to in-memory

### Quick Start (any OS)
```bash
# 1. Go to project
cd linkup

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate it
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Setup database & static files
python manage.py migrate
python manage.py collectstatic --noinput

# 6. Create admin (optional)
python manage.py createsuperuser

# 7. Start server
python manage.py runserver
```
Visit **http://127.0.0.1:8000**

> The project uses SQLite by default for development — no external database needed.

---

## 2. Database Setup

Choose one:

### A) Supabase (Recommended — free PostgreSQL with SSL)

1. Go to [supabase.com](https://supabase.com) → "New Project"
2. After creation, go to **Project Settings → Database → Connection string**
3. Copy the **URI** (looks like `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres`)
4. Append `?sslmode=require` to the end
5. Use this as your `DATABASE_URL`

### B) Any PostgreSQL provider

Get a connection string in this format:
```
postgresql://user:password@host:5432/database
```

For Neon, Aiven, AWS RDS, etc. — same format.

---

## 3. Platform Deployments

### A) Docker (any VPS / cloud)

**Prerequisites:** Docker & Docker Compose installed.

```bash
cd linkup

# Create .env file
cat > .env << EOF
DJANGO_ENVIRONMENT=production
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
ALLOWED_HOSTS=yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
REDIS_URL=redis://redis:6379/0
EOF

# Start everything
docker compose up -d --build
```

Your app runs at **http://localhost:8000**.
Set up a reverse proxy (Nginx/Caddy) for production with SSL.

---

### B) Railway

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Select your repo, set **Root Directory** to `linkup`
4. Add these services:
   - **Web Service** — uses the Dockerfile
   - **PostgreSQL** — Railway manages it
   - **Redis** — Railway manages it
5. Set environment variables in Railway dashboard:
   ```
   DJANGO_ENVIRONMENT=production
   SECRET_KEY=<generate one>
   DATABASE_URL=<Railway-provided PostgreSQL URL>
   ALLOWED_HOSTS=<railway-app-url>
   CSRF_TRUSTED_ORIGINS=https://<railway-app-url>
   ```
6. Railway auto-deploys on every push

> If the Dockerfile doesn't auto-detect, set **Start Command** to `daphne -b 0.0.0.0 -p $PORT professional_network.asgi:application`

---

### C) Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New +** → **Web Service**
3. Connect your repo, set **Root Directory** to `linkup`
4. Choose **Docker** as runtime (Render detects the Dockerfile)
5. Add environment variables:
   ```
   DJANGO_ENVIRONMENT=production
   SECRET_KEY=<generate one>
   DATABASE_URL=<Render PostgreSQL URL>
   ALLOWED_HOSTS=<render-app-url>
   CSRF_TRUSTED_ORIGINS=https://<render-app-url>
   ```
6. Add a **Redis** service from Render dashboard
7. Deploy

---

### D) Defang.io

```bash
# Install CLI
eval "$(curl -fsSL s.defang.io/install)"

# Authenticate with AWS/GCP
defang login

# Deploy
cd linkup
defang config set SECRET_KEY "<key>"
defang config set DATABASE_URL "postgresql://..."
defang config set ALLOWED_HOSTS "*"
defang compose up
```

Defang provisions managed PostgreSQL, Redis, load balancer, and SSL automatically.

---

### E) Manual VPS (Ubuntu)

```bash
# 1. Server setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv redis-server postgresql postgresql-contrib libmagic1 nginx

# 2. Setup PostgreSQL
sudo -u postgres psql -c "CREATE USER linkup WITH PASSWORD 'strongpassword';"
sudo -u postgres psql -c "CREATE DATABASE linkup OWNER linkup;"

# 3. Clone & setup app
git clone https://github.com/Techhackontime999/LinkUp.git /opt/linkup
cd /opt/linkup/linkup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Environment
export DJANGO_ENVIRONMENT=production
export SECRET_KEY="$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")"
export DATABASE_URL="postgresql://linkup:strongpassword@localhost:5432/linkup"
export ALLOWED_HOSTS="yourdomain.com"
export REDIS_URL="redis://localhost:6379/0"

# 5. Setup app
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# 6. Test it runs
daphne -b 0.0.0.0 -p 8000 professional_network.asgi:application

# 7. Create systemd service
sudo tee /etc/systemd/system/linkup.service << 'EOF'
[Unit]
Description=LinkUp Django App
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/linkup/linkup
Environment=DJANGO_ENVIRONMENT=production
Environment=SECRET_KEY=<your-key>
Environment=DATABASE_URL=postgresql://linkup:pass@localhost:5432/linkup
Environment=ALLOWED_HOSTS=yourdomain.com
ExecStart=/opt/linkup/linkup/venv/bin/daphne -b 0.0.0.0 -p 8000 professional_network.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now linkup

# 8. Nginx reverse proxy
sudo tee /etc/nginx/sites-available/linkup << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/linkup/linkup/staticfiles/;
    }

    location /media/ {
        alias /opt/linkup/linkup/media/;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/linkup /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 9. SSL with Certbot
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 4. Post-Deployment

### Verify everything works
```
https://yourdomain.com/health/       → {"status": "healthy"}
https://yourdomain.com/health/db/    → {"status": "healthy", "database": "connected"}
https://yourdomain.com/readiness/    → {"status": "ready", "checks": {"database": true, "redis": true}}
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key. Generate: `python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DATABASE_URL` | Yes | PostgreSQL connection string. Supabase: add `?sslmode=require` |
| `ALLOWED_HOSTS` | Yes | Comma-separated domain list (e.g., `mydomain.com,www.mydomain.com`) |
| `DJANGO_ENVIRONMENT` | No | Set to `production` for production mode |
| `REDIS_URL` | No | Redis connection string (default: `redis://localhost:6379/0`) |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated origins for CSRF (e.g., `https://mydomain.com`) |
| `DEBUG` | No | Always `false` in production |
| `DATABASE_SSL_REQUIRE` | No | Set `true` if your DB requires SSL (like Supabase) |

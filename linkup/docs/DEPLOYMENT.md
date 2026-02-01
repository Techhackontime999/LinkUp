# LinkUp Production Deployment Guide

This guide provides comprehensive instructions for deploying the LinkUp application to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Redis Setup](#redis-setup)
5. [Application Configuration](#application-configuration)
6. [Static Files](#static-files)
7. [Running the Application](#running-the-application)
8. [Health Checks](#health-checks)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Python 3.14+ (or your specific version)
- PostgreSQL 12+ (recommended: 14+)
- Redis 6+ (for WebSocket support and caching)
- Nginx or similar reverse proxy (recommended)
- SSL certificate (for HTTPS)

### Required Software

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install redis-server
sudo apt-get install nginx

# CentOS/RHEL
sudo yum install python3 python3-pip
sudo yum install postgresql-server postgresql-contrib
sudo yum install redis
sudo yum install nginx
```

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/linkup.git
cd linkup
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Django Core
SECRET_KEY=your-secret-key-here-generate-with-django-get-secret-key
DEBUG=False
DJANGO_ENVIRONMENT=production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://linkup_user:password@localhost:5432/linkup_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**Generate a secure SECRET_KEY:**

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Database Setup

### 1. Create PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE linkup_db;
CREATE USER linkup_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE linkup_db TO linkup_user;

# PostgreSQL 15+ requires additional grants
\c linkup_db
GRANT ALL ON SCHEMA public TO linkup_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO linkup_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO linkup_user;

\q
```

### 2. Run Migrations

```bash
export DJANGO_ENVIRONMENT=production
python manage.py migrate
```

### 3. Create Superuser

```bash
python manage.py createsuperuser
```

### 4. Migrate Data (if coming from SQLite)

See [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md) for detailed instructions.

## Redis Setup

### 1. Install and Start Redis

```bash
# Ubuntu/Debian
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### 2. Configure Redis (Optional)

Edit `/etc/redis/redis.conf` for production settings:

```conf
# Bind to localhost only (if on same server)
bind 127.0.0.1

# Set password
requirepass your_redis_password

# Enable persistence
save 900 1
save 300 10
save 60 10000
```

Update your `.env` file if using password:

```bash
REDIS_URL=redis://:your_redis_password@localhost:6379/0
```

## Application Configuration

### 1. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

This will gather all static files into the `staticfiles/` directory.

### 2. Verify Configuration

```bash
# Check for configuration issues
python manage.py check --deploy
```

## Static Files

Static files are served using WhiteNoise in production. No additional configuration needed for basic setup.

For high-traffic sites, consider using a CDN:
1. Upload `staticfiles/` to your CDN
2. Update `STATIC_URL` in production settings to point to CDN

## Running the Application

### Option 1: Using Gunicorn and Daphne Directly

#### Terminal 1: Start Gunicorn (HTTP)

```bash
gunicorn professional_network.wsgi:application \
  --config gunicorn.conf.py \
  --bind 0.0.0.0:8000
```

#### Terminal 2: Start Daphne (WebSockets)

```bash
daphne -b 0.0.0.0 -p 8001 professional_network.asgi:application
```

### Option 2: Using Systemd Services

Create `/etc/systemd/system/linkup-web.service`:

```ini
[Unit]
Description=LinkUp Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/linkup
Environment="PATH=/path/to/linkup/venv/bin"
EnvironmentFile=/path/to/linkup/.env
ExecStart=/path/to/linkup/venv/bin/gunicorn \
  --config /path/to/linkup/gunicorn.conf.py \
  professional_network.wsgi:application

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/linkup-worker.service`:

```ini
[Unit]
Description=LinkUp Daphne Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/linkup
Environment="PATH=/path/to/linkup/venv/bin"
EnvironmentFile=/path/to/linkup/.env
ExecStart=/path/to/linkup/venv/bin/daphne \
  -b 0.0.0.0 -p 8001 \
  professional_network.asgi:application

[Install]
WantedBy=multi-user.target
```

Start services:

```bash
sudo systemctl daemon-reload
sudo systemctl start linkup-web
sudo systemctl start linkup-worker
sudo systemctl enable linkup-web
sudo systemctl enable linkup-worker
```

### Option 3: Using Supervisor

Install Supervisor:

```bash
sudo apt-get install supervisor
```

Create `/etc/supervisor/conf.d/linkup.conf`:

```ini
[program:linkup-web]
command=/path/to/linkup/venv/bin/gunicorn professional_network.wsgi:application --config /path/to/linkup/gunicorn.conf.py
directory=/path/to/linkup
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/linkup/web.log

[program:linkup-worker]
command=/path/to/linkup/venv/bin/daphne -b 0.0.0.0 -p 8001 professional_network.asgi:application
directory=/path/to/linkup
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/linkup/worker.log
```

Start services:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start linkup-web
sudo supervisorctl start linkup-worker
```

## Nginx Configuration

Create `/etc/nginx/sites-available/linkup`:

```nginx
upstream linkup_web {
    server 127.0.0.1:8000;
}

upstream linkup_ws {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    client_max_body_size 50M;

    location /static/ {
        alias /path/to/linkup/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /path/to/linkup/media/;
        expires 7d;
    }

    location /ws/ {
        proxy_pass http://linkup_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://linkup_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/linkup /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Health Checks

The application provides several health check endpoints:

- `/health/` - Basic health check
- `/health/db/` - Database connectivity
- `/health/redis/` - Redis connectivity
- `/readiness/` - Comprehensive readiness check

Test health checks:

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/health/db/
curl http://localhost:8000/health/redis/
curl http://localhost:8000/readiness/
```

## Monitoring and Logging

### Application Logs

Logs are stored in the `logs/` directory:

- `logs/django.log` - General application logs
- `logs/security.log` - Security-related events

### View Logs

```bash
# View recent logs
tail -f logs/django.log

# View security logs
tail -f logs/security.log

# Search for errors
grep ERROR logs/django.log
```

### Log Rotation

Logs are automatically rotated (10MB max, 5 backups). For system-level rotation, configure logrotate:

Create `/etc/logrotate.d/linkup`:

```
/path/to/linkup/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload linkup-web
    endscript
}
```

## Troubleshooting

### Common Issues

#### 1. Static Files Not Loading

```bash
# Recollect static files
python manage.py collectstatic --clear --noinput

# Check permissions
sudo chown -R www-data:www-data staticfiles/
```

#### 2. Database Connection Errors

```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U linkup_user -d linkup_db -h localhost

# Check DATABASE_URL in .env
```

#### 3. Redis Connection Errors

```bash
# Verify Redis is running
sudo systemctl status redis-server

# Test connection
redis-cli ping

# Check REDIS_URL in .env
```

#### 4. WebSocket Connection Failures

- Ensure Daphne is running on port 8001
- Check Nginx WebSocket configuration
- Verify REDIS_URL is correct
- Check browser console for errors

#### 5. Permission Denied Errors

```bash
# Fix file permissions
sudo chown -R www-data:www-data /path/to/linkup
sudo chmod -R 755 /path/to/linkup

# Fix media directory
sudo chown -R www-data:www-data media/
sudo chmod -R 755 media/
```

### Debug Mode

To temporarily enable debug mode (NOT for production):

```bash
# In .env
DEBUG=True

# Restart services
sudo systemctl restart linkup-web linkup-worker
```

**Remember to disable DEBUG after troubleshooting!**

### Check Django Configuration

```bash
python manage.py check --deploy
```

## Security Checklist

- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY set
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS enabled
- [ ] CSRF_TRUSTED_ORIGINS set
- [ ] Database password is strong
- [ ] Redis password set (if exposed)
- [ ] File permissions correct
- [ ] Firewall configured
- [ ] Regular backups scheduled
- [ ] Security updates applied

## Backup Strategy

### Database Backups

```bash
# Create backup script
#!/bin/bash
pg_dump -U linkup_user linkup_db > backup_$(date +%Y%m%d).sql

# Schedule with cron
0 2 * * * /path/to/backup_script.sh
```

### Media Files Backup

```bash
# Backup media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/

# Or use rsync
rsync -av media/ /backup/location/media/
```

## Platform-Specific Guides

For platform-specific deployment instructions, see:

- [Heroku Deployment](DEPLOYMENT_HEROKU.md)
- [DigitalOcean Deployment](DEPLOYMENT_DIGITALOCEAN.md)
- [AWS Deployment](DEPLOYMENT_AWS.md)

## Additional Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Daphne Documentation](https://github.com/django/daphne)
- [Nginx Documentation](https://nginx.org/en/docs/)

## Support

For issues or questions:
1. Check application logs
2. Review this documentation
3. Check Django and dependency documentation
4. Open an issue on GitHub

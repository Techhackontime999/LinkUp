# DigitalOcean Deployment Guide

Guide for deploying LinkUp on DigitalOcean Droplets or App Platform.

## Option 1: App Platform (Easiest)

### 1. Create App

1. Go to DigitalOcean App Platform
2. Click "Create App"
3. Connect your GitHub repository
4. Select branch (main)

### 2. Configure Services

Add three components:

**Web Service:**
- Name: linkup-web
- Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Run Command: `gunicorn professional_network.wsgi:application --config gunicorn.conf.py`

**Worker Service:**
- Name: linkup-worker
- Build Command: `pip install -r requirements.txt`
- Run Command: `daphne -b 0.0.0.0 -p 8080 professional_network.asgi:application`

### 3. Add Databases

- PostgreSQL (Dev or Basic)
- Redis (Basic)

### 4. Set Environment Variables

```
DJANGO_ENVIRONMENT=production
SECRET_KEY=<generate-secret-key>
DEBUG=False
ALLOWED_HOSTS=${APP_DOMAIN}
DATABASE_URL=${db.DATABASE_URL}
REDIS_URL=${redis.REDIS_URL}
CSRF_TRUSTED_ORIGINS=https://${APP_DOMAIN}
```

### 5. Deploy

Click "Create Resources" and wait for deployment.

## Option 2: Droplet (Manual)

### 1. Create Droplet

- Ubuntu 22.04 LTS
- At least 2GB RAM
- Choose datacenter region

### 2. Initial Setup

```bash
# SSH into droplet
ssh root@your_droplet_ip

# Update system
apt update && apt upgrade -y

# Create user
adduser linkup
usermod -aG sudo linkup
su - linkup
```

### 3. Install Dependencies

```bash
sudo apt install python3 python3-pip python3-venv
sudo apt install postgresql postgresql-contrib
sudo apt install redis-server
sudo apt install nginx
```

### 4. Setup Application

```bash
# Clone repository
git clone https://github.com/yourusername/linkup.git
cd linkup

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Database

```bash
sudo -u postgres psql
CREATE DATABASE linkup_db;
CREATE USER linkup_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE linkup_db TO linkup_user;
\q
```

### 6. Configure Environment

Create `.env` file with production settings.

### 7. Setup Services

Follow the systemd service setup from main DEPLOYMENT.md

### 8. Configure Nginx

Follow Nginx configuration from main DEPLOYMENT.md

### 9. Setup SSL

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Monitoring

```bash
# Check services
sudo systemctl status linkup-web
sudo systemctl status linkup-worker

# View logs
sudo journalctl -u linkup-web -f
sudo journalctl -u linkup-worker -f
```

## Backups

Setup automated backups in DigitalOcean dashboard or use:

```bash
# Database backup
pg_dump -U linkup_user linkup_db > backup.sql

# Upload to Spaces (DigitalOcean S3)
s3cmd put backup.sql s3://your-bucket/
```

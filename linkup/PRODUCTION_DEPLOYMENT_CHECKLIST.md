# Production Deployment Checklist

## ✅ Pre-Deployment Verification

### Code Quality
- [x] All features implemented and tested
- [x] No syntax errors or warnings
- [x] Code follows Django best practices
- [x] All imports working correctly
- [x] No unused code or files

### Security
- [ ] `DEBUG = False` in settings.py
- [ ] `SECRET_KEY` changed from default
- [ ] `ALLOWED_HOSTS` configured
- [ ] HTTPS/SSL certificate installed
- [ ] CSRF protection enabled
- [ ] Secure cookies configured
- [ ] SQL injection protection verified
- [ ] XSS protection enabled
- [ ] Security headers configured

### Database
- [ ] Migrations applied: `python manage.py migrate`
- [ ] Database backed up
- [ ] Database indexes created
- [ ] Connection pooling configured
- [ ] Superuser created: `python manage.py createsuperuser`

### Static Files
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Static file serving configured (WhiteNoise/Nginx)
- [ ] Media files directory configured
- [ ] File upload limits set

### Environment Variables
- [ ] `.env` file created (not in git)
- [ ] `SECRET_KEY` in environment
- [ ] `DATABASE_URL` configured
- [ ] `REDIS_URL` configured (if using)
- [ ] AI provider keys in environment (optional)

### Dependencies
- [ ] All requirements installed: `pip install -r requirements.txt`
- [ ] Python version correct (3.12+)
- [ ] Database driver installed (psycopg2/mysqlclient)
- [ ] Redis installed (if using)

---

## 🚀 Deployment Steps

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.12 python3.12-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Redis (optional)
sudo apt install redis-server -y

# Install Nginx
sudo apt install nginx -y
```

### 2. Application Setup
```bash
# Create project directory
sudo mkdir -p /var/www/linkup
cd /var/www/linkup

# Clone repository
git clone <your-repo-url> .

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 3. Database Setup
```bash
# Create database
sudo -u postgres psql
CREATE DATABASE linkup_db;
CREATE USER linkup_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE linkup_db TO linkup_user;
\q

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Static Files
```bash
# Collect static files
python manage.py collectstatic --noinput

# Set permissions
sudo chown -R www-data:www-data /var/www/linkup
```

### 5. Gunicorn Setup
```bash
# Create gunicorn service
sudo nano /etc/systemd/system/gunicorn.service
```

```ini
[Unit]
Description=Gunicorn daemon for LinkUp
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/linkup
Environment="PATH=/var/www/linkup/venv/bin"
ExecStart=/var/www/linkup/venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/var/www/linkup/gunicorn.sock \
    professional_network.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Start gunicorn
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

### 6. Nginx Setup
```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/linkup
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /var/www/linkup/staticfiles/;
    }

    location /media/ {
        alias /var/www/linkup/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/linkup/gunicorn.sock;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/linkup /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

---

## 🧪 Post-Deployment Testing

### 1. Basic Functionality
```bash
# Test homepage
curl https://yourdomain.com

# Test admin panel
curl https://yourdomain.com/api/admin/

# Test static files
curl https://yourdomain.com/static/css/custom_styles.css
```

### 2. Admin Panel Tests
- [ ] Can access `/api/admin/`
- [ ] Can log in as staff user
- [ ] Can create new AI model
- [ ] Can edit existing model
- [ ] Can delete model
- [ ] Can suspend/activate model
- [ ] Can generate API key
- [ ] Can revoke API key
- [ ] Search works
- [ ] Filters work
- [ ] Pagination works

### 3. Security Tests
- [ ] HTTPS redirects working
- [ ] CSRF protection working
- [ ] Non-staff users blocked from admin
- [ ] SQL injection attempts blocked
- [ ] XSS attempts blocked

### 4. Performance Tests
- [ ] Page load time < 2 seconds
- [ ] Database queries optimized
- [ ] Static files loading fast
- [ ] No memory leaks

---

## 📊 Monitoring Setup

### 1. Error Logging
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/linkup/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

### 2. Health Check Endpoint
```python
# Test health endpoint
curl https://yourdomain.com/health/
```

### 3. Database Backup
```bash
# Create backup script
sudo nano /usr/local/bin/backup_linkup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/linkup"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump linkup_db > $BACKUP_DIR/db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/www/linkup/media/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup_linkup.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
0 2 * * * /usr/local/bin/backup_linkup.sh
```

---

## 🔧 Maintenance

### Regular Tasks
- [ ] Monitor error logs daily
- [ ] Check disk space weekly
- [ ] Review security updates weekly
- [ ] Test backups monthly
- [ ] Update dependencies monthly
- [ ] Review performance metrics monthly

### Update Procedure
```bash
# 1. Backup database
pg_dump linkup_db > backup_$(date +%Y%m%d).sql

# 2. Pull latest code
cd /var/www/linkup
git pull origin main

# 3. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

---

## 🚨 Troubleshooting

### Issue: 502 Bad Gateway
```bash
# Check gunicorn status
sudo systemctl status gunicorn

# Check gunicorn logs
sudo journalctl -u gunicorn

# Restart gunicorn
sudo systemctl restart gunicorn
```

### Issue: Static Files Not Loading
```bash
# Check static files collected
ls -la /var/www/linkup/staticfiles/

# Check nginx config
sudo nginx -t

# Check permissions
sudo chown -R www-data:www-data /var/www/linkup/staticfiles/
```

### Issue: Database Connection Error
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check database exists
sudo -u postgres psql -l

# Test connection
python manage.py dbshell
```

---

## ✅ Final Verification

### Production Checklist
- [ ] Application accessible via HTTPS
- [ ] Admin panel working
- [ ] All features tested
- [ ] Error logging working
- [ ] Backups automated
- [ ] Monitoring setup
- [ ] Documentation updated
- [ ] Team trained

### Performance Metrics
- [ ] Page load time < 2s
- [ ] Database query time < 100ms
- [ ] API response time < 500ms
- [ ] Uptime > 99.9%

### Security Verification
- [ ] SSL certificate valid
- [ ] Security headers present
- [ ] CSRF protection working
- [ ] Authentication working
- [ ] Authorization working

---

## 🎉 Deployment Complete!

Your AI Admin Panel is now live and production-ready!

### Access URLs
- **Admin Panel**: https://yourdomain.com/api/admin/
- **Dashboard**: https://yourdomain.com/api/admin/dashboard/
- **Health Check**: https://yourdomain.com/health/

### Next Steps
1. Monitor error logs for first 24 hours
2. Test all features in production
3. Set up alerting for critical errors
4. Document any production-specific configurations
5. Train team on admin panel usage

**Congratulations! 🚀**


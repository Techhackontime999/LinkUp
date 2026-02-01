# AWS Deployment Guide

Guide for deploying LinkUp on AWS using Elastic Beanstalk or EC2.

## Option 1: Elastic Beanstalk (Recommended)

### 1. Install EB CLI

```bash
pip install awsebcli
```

### 2. Initialize EB Application

```bash
eb init -p python-3.14 linkup-app --region us-east-1
```

### 3. Create Environment

```bash
eb create linkup-prod
```

### 4. Configure Environment Variables

```bash
eb setenv DJANGO_ENVIRONMENT=production \
  SECRET_KEY=your-secret-key \
  DEBUG=False \
  ALLOWED_HOSTS=.elasticbeanstalk.com
```

### 5. Add RDS and ElastiCache

In AWS Console:
1. Create RDS PostgreSQL instance
2. Create ElastiCache Redis cluster
3. Update security groups to allow EB access

### 6. Update Environment Variables

```bash
eb setenv DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/dbname \
  REDIS_URL=redis://elasticache-endpoint:6379/0
```

### 7. Deploy

```bash
eb deploy
```

### 8. Run Migrations

```bash
eb ssh
source /var/app/venv/*/bin/activate
cd /var/app/current
python manage.py migrate
python manage.py createsuperuser
exit
```

## Option 2: EC2 (Manual)

### 1. Launch EC2 Instance

- Ubuntu 22.04 LTS
- t3.medium or larger
- Configure security groups (80, 443, 22)

### 2. Setup Application

Follow the same steps as DigitalOcean Droplet deployment.

### 3. Setup RDS

1. Create RDS PostgreSQL instance
2. Configure security group
3. Update DATABASE_URL

### 4. Setup ElastiCache

1. Create Redis cluster
2. Configure security group
3. Update REDIS_URL

### 5. Setup Load Balancer (Optional)

1. Create Application Load Balancer
2. Configure target groups
3. Add SSL certificate

## S3 for Static/Media Files

### 1. Create S3 Bucket

```bash
aws s3 mb s3://linkup-static
aws s3 mb s3://linkup-media
```

### 2. Install django-storages

```bash
pip install django-storages boto3
```

### 3. Configure Settings

Add to production.py:

```python
# AWS S3 Settings
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = 'linkup-static'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_DEFAULT_ACL = 'public-read'

# Static files
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

# Media files
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

## CloudFront CDN (Optional)

1. Create CloudFront distribution
2. Point to S3 bucket
3. Update STATIC_URL and MEDIA_URL

## Monitoring

### CloudWatch

- Enable detailed monitoring
- Set up alarms for CPU, memory, disk
- Configure log groups

### Application Logs

```bash
# View logs
eb logs

# Or SSH and check
eb ssh
sudo tail -f /var/log/web.stdout.log
```

## Auto Scaling

Configure in EB environment:
- Min instances: 2
- Max instances: 10
- Scaling triggers: CPU > 70%

## Backup Strategy

### RDS Automated Backups

- Enable automated backups (7-35 days)
- Configure backup window
- Enable Multi-AZ for high availability

### S3 Versioning

```bash
aws s3api put-bucket-versioning \
  --bucket linkup-media \
  --versioning-configuration Status=Enabled
```

## Cost Optimization

- Use Reserved Instances for predictable workloads
- Enable S3 Intelligent-Tiering
- Use CloudFront for static assets
- Monitor with AWS Cost Explorer

# Database Migration Guide: SQLite to PostgreSQL

This guide provides step-by-step instructions for migrating your LinkUp application data from SQLite (development) to PostgreSQL (production).

## Prerequisites

- PostgreSQL installed and running
- Access to create databases and users
- Backup of your current SQLite database
- Python environment with all dependencies installed

## Step 1: Backup Current Data

Before starting the migration, create a backup of your SQLite database:

```bash
# Copy the database file
cp db.sqlite3 db.sqlite3.backup

# Export data using Django's dumpdata
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission \
  -e sessions.session \
  > datadump.json
```

**Important Notes:**
- We exclude `contenttypes` and `auth.Permission` because they will be recreated by migrations
- We exclude `sessions.session` because sessions are temporary
- The `--natural-foreign` and `--natural-primary` flags ensure data can be loaded into a different database

## Step 2: Set Up PostgreSQL Database

### Create Database and User

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database
CREATE DATABASE linkup_db;

-- Create user
CREATE USER linkup_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE linkup_db TO linkup_user;

-- Grant schema privileges (PostgreSQL 15+)
\c linkup_db
GRANT ALL ON SCHEMA public TO linkup_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO linkup_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO linkup_user;

-- Exit
\q
```

### Configure Environment Variables

Create a `.env` file in your project root (or set environment variables):

```bash
# .env file
DJANGO_ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database configuration
DATABASE_URL=postgresql://linkup_user:your_secure_password@localhost:5432/linkup_db

# Redis configuration
REDIS_URL=redis://localhost:6379/0

# Security
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Step 3: Run Migrations on PostgreSQL

```bash
# Set environment to use production settings
export DJANGO_ENVIRONMENT=production

# Or on Windows
set DJANGO_ENVIRONMENT=production

# Run migrations to create tables
python manage.py migrate
```

This will create all the necessary tables in your PostgreSQL database.

## Step 4: Load Data into PostgreSQL

```bash
# Load the data dump
python manage.py loaddata datadump.json
```

**Troubleshooting:**
- If you encounter errors about missing content types, run migrations again
- If you get foreign key errors, ensure all related objects are in the dump
- For large datasets, consider using `--verbosity 2` to see progress

## Step 5: Verify Data Integrity

Run the verification script to ensure all data was migrated correctly:

```bash
python scripts/verify_migration.py
```

Or manually verify:

```bash
# Check user count
python manage.py shell
>>> from users.models import User
>>> User.objects.count()

# Check posts
>>> from feed.models import Post
>>> Post.objects.count()

# Check other models
>>> from jobs.models import Job
>>> Job.objects.count()
```

## Step 6: Test the Application

```bash
# Create a superuser if needed
python manage.py createsuperuser

# Run the development server with PostgreSQL
python manage.py runserver

# Test key functionality:
# - User login
# - Creating posts
# - Messaging
# - Job listings
```

## Step 7: Update Production Configuration

Once verified, update your production environment:

1. Set all required environment variables
2. Run `python manage.py collectstatic`
3. Start Gunicorn and Daphne servers
4. Monitor logs for any issues

## Rollback Instructions

If you need to rollback to SQLite:

```bash
# 1. Stop the application
# 2. Change environment back to development
export DJANGO_ENVIRONMENT=development

# 3. Restore SQLite backup
cp db.sqlite3.backup db.sqlite3

# 4. Restart application
python manage.py runserver
```

## Common Issues and Solutions

### Issue: "relation does not exist" errors

**Solution:** Run migrations again:
```bash
python manage.py migrate --run-syncdb
```

### Issue: Foreign key constraint violations

**Solution:** Load data in the correct order or use `--natural-foreign` flag in dumpdata.

### Issue: Duplicate key errors

**Solution:** Clear the PostgreSQL database and start fresh:
```bash
python manage.py flush
python manage.py migrate
python manage.py loaddata datadump.json
```

### Issue: Permission denied errors

**Solution:** Grant proper permissions to the PostgreSQL user:
```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO linkup_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO linkup_user;
```

## Performance Optimization

After migration, optimize PostgreSQL:

```sql
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum to reclaim storage
VACUUM ANALYZE;

-- Create indexes if needed (Django migrations should handle this)
```

## Data Validation Checklist

- [ ] All users migrated
- [ ] All posts and comments migrated
- [ ] All job listings migrated
- [ ] All connections/follows migrated
- [ ] All messages migrated
- [ ] Media files accessible
- [ ] User authentication works
- [ ] Admin panel accessible
- [ ] No error logs

## Additional Resources

- [Django Database Documentation](https://docs.djangoproject.com/en/stable/ref/databases/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [dj-database-url Documentation](https://github.com/jazzband/dj-database-url)

## Support

If you encounter issues not covered in this guide, check:
1. Application logs in `logs/django.log`
2. PostgreSQL logs
3. Django documentation for your specific version

# Design Document: Production Deployment Setup

## Overview

This design outlines the transformation of the Django LinkUp application from a development environment to a production-ready system. The solution implements a multi-layered approach to production readiness:

1. **Environment Separation**: Split settings into base, development, and production modules
2. **Database Migration**: Transition from SQLite to PostgreSQL with environment-based configuration
3. **Security Hardening**: Implement Django security best practices for production
4. **Static Asset Management**: Configure WhiteNoise for efficient static file serving
5. **WebSocket Infrastructure**: Set up Redis-backed Channel Layer for production WebSockets
6. **Dual Server Architecture**: Deploy both Gunicorn (WSGI) and Daphne (ASGI) for HTTP and WebSocket support
7. **Environment Variables**: Externalize all sensitive configuration using python-decouple
8. **Monitoring and Logging**: Implement production-grade logging and health checks
9. **Git Repository Hygiene**: Clean repository of sensitive data and configure proper .gitignore

The design maintains backward compatibility with the development environment while adding production capabilities. Developers can continue using SQLite locally while production uses PostgreSQL. The system uses environment variables to control behavior, making it deployable to various platforms (Heroku, DigitalOcean, AWS, Railway, Render, etc.).

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[Web Browser]
    end
    
    subgraph "Load Balancer / Reverse Proxy"
        LB[Nginx/Platform LB]
    end
    
    subgraph "Application Layer"
        Gunicorn[Gunicorn WSGI Server<br/>HTTP Requests]
        Daphne[Daphne ASGI Server<br/>WebSocket Connections]
    end
    
    subgraph "Django Application"
        Settings[Settings Module<br/>base/dev/prod]
        Apps[Django Apps<br/>users, feed, jobs, messaging, network]
        Channels[Django Channels<br/>WebSocket Routing]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL<br/>Primary Database)]
        Redis[(Redis<br/>Channel Layer & Cache)]
    end
    
    subgraph "Storage Layer"
        Static[Static Files<br/>WhiteNoise]
        Media[Media Files<br/>User Uploads]
    end
    
    Browser -->|HTTP/HTTPS| LB
    Browser -->|WebSocket| LB
    LB -->|HTTP| Gunicorn
    LB -->|WebSocket| Daphne
    Gunicorn --> Settings
    Daphne --> Settings
    Settings --> Apps
    Apps --> Channels
    Apps --> PostgreSQL
    Channels --> Redis
    Apps --> Redis
    Gunicorn --> Static
    Apps --> Media
```

### Settings Architecture

```mermaid
graph LR
    subgraph "Settings Modules"
        Base[settings/base.py<br/>Shared Configuration]
        Dev[settings/development.py<br/>Local Development]
        Prod[settings/production.py<br/>Production Environment]
    end
    
    subgraph "Environment"
        EnvVars[Environment Variables<br/>.env file]
    end
    
    EnvVars -->|Loads| Base
    Base -->|Inherits| Dev
    Base -->|Inherits| Prod
    
    Dev -->|SQLite, InMemory Cache| DevEnv[Development Environment]
    Prod -->|PostgreSQL, Redis| ProdEnv[Production Environment]
```

### Deployment Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Git as Git Repository
    participant Platform as Deployment Platform
    participant App as Application
    participant DB as PostgreSQL
    participant Redis as Redis
    
    Dev->>Git: Push code
    Git->>Platform: Trigger deployment
    Platform->>Platform: Install dependencies
    Platform->>Platform: Set environment variables
    Platform->>App: collectstatic
    Platform->>DB: Run migrations
    Platform->>App: Start Gunicorn (HTTP)
    Platform->>App: Start Daphne (WebSocket)
    App->>DB: Connect to database
    App->>Redis: Connect to Redis
    App->>Platform: Health check OK
    Platform->>App: Route traffic
```

## Components and Interfaces

### 1. Settings Module Restructuring

**Current Structure:**
```
professional_network/
    settings.py  # Single monolithic settings file
```

**New Structure:**
```
professional_network/
    settings/
        __init__.py          # Imports appropriate settings based on environment
        base.py              # Shared settings for all environments
        development.py       # Development-specific settings
        production.py        # Production-specific settings
```

**Component: settings/__init__.py**
- **Purpose**: Automatically load the correct settings module based on DJANGO_SETTINGS_MODULE
- **Interface**: Imports all settings from the appropriate module
- **Logic**: 
  ```python
  import os
  from decouple import config
  
  ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')
  
  if ENVIRONMENT == 'production':
      from .production import *
  else:
      from .development import *
  ```

**Component: settings/base.py**
- **Purpose**: Contains all shared configuration between environments
- **Contents**:
  - INSTALLED_APPS (common apps)
  - MIDDLEWARE (common middleware)
  - TEMPLATES configuration
  - AUTH_PASSWORD_VALIDATORS
  - Internationalization settings
  - CKEditor configuration
  - Custom middleware settings
  - AUTH_USER_MODEL
  - LOGIN/LOGOUT URLs
  - File upload limits
- **Interface**: Provides base configuration that other settings inherit

**Component: settings/development.py**
- **Purpose**: Development-specific overrides
- **Key Settings**:
  - DEBUG = True
  - ALLOWED_HOSTS = ['*']
  - SQLite database
  - InMemoryChannelLayer for Channels
  - Local memory cache
  - Relaxed security settings
  - django-browser-reload enabled
  - Detailed error pages
- **Interface**: Imports from base and overrides specific settings

**Component: settings/production.py**
- **Purpose**: Production-specific configuration
- **Key Settings**:
  - DEBUG = False (from environment variable)
  - ALLOWED_HOSTS from environment variable
  - PostgreSQL database (from DATABASE_URL)
  - RedisChannelLayer for Channels
  - Redis cache
  - Strict security settings (HTTPS, HSTS, secure cookies)
  - WhiteNoise for static files
  - Production logging configuration
  - Error reporting configuration
- **Interface**: Imports from base and overrides for production

### 2. Environment Variables Manager

**Component: Environment Configuration Loader**
- **Library**: python-decouple
- **Purpose**: Load and validate environment variables
- **Interface**:
  ```python
  from decouple import config, Csv
  
  # Required variables
  SECRET_KEY = config('SECRET_KEY')
  DEBUG = config('DEBUG', default=False, cast=bool)
  ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
  
  # Database
  DATABASE_URL = config('DATABASE_URL')
  
  # Redis
  REDIS_URL = config('REDIS_URL', default='redis://localhost:6379')
  ```

**Component: .env.example Template**
- **Purpose**: Document all required and optional environment variables
- **Contents**:
  ```
  # Django Core
  SECRET_KEY=your-secret-key-here
  DEBUG=False
  DJANGO_ENVIRONMENT=production
  ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
  
  # Database
  DATABASE_URL=postgresql://user:password@host:port/dbname
  
  # Redis
  REDIS_URL=redis://localhost:6379/0
  
  # Security
  CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  
  # Static/Media (optional, platform-dependent)
  STATIC_URL=/static/
  MEDIA_URL=/media/
  ```

### 3. Database Configuration Component

**Component: Database Connection Manager**
- **Purpose**: Configure database based on environment
- **Development Configuration**:
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.sqlite3',
          'NAME': BASE_DIR / 'db.sqlite3',
      }
  }
  ```

**Production Configuration**:
  ```python
  import dj_database_url
  
  DATABASES = {
      'default': dj_database_url.config(
          default=config('DATABASE_URL'),
          conn_max_age=600,
          conn_health_checks=True,
      )
  }
  ```

**Component: Database Migration Scripts**
- **Purpose**: Facilitate data migration from SQLite to PostgreSQL
- **Scripts**:
  1. `export_data.sh`: Dump data from SQLite using dumpdata
  2. `import_data.sh`: Load data into PostgreSQL using loaddata
  3. `verify_migration.py`: Verify data integrity after migration

### 4. Static Files Management

**Component: WhiteNoise Integration**
- **Purpose**: Serve static files efficiently in production
- **Configuration**:
  ```python
  MIDDLEWARE = [
      'django.middleware.security.SecurityMiddleware',
      'whitenoise.middleware.WhiteNoiseMiddleware',  # Add after SecurityMiddleware
      # ... other middleware
  ]
  
  STATIC_ROOT = BASE_DIR / 'staticfiles'
  STATIC_URL = '/static/'
  
  STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
  ```

**Component: Media Files Configuration**
- **Purpose**: Handle user-uploaded content
- **Configuration**:
  ```python
  MEDIA_URL = '/media/'
  MEDIA_ROOT = BASE_DIR / 'media'
  ```
- **Note**: For production at scale, consider cloud storage (S3, CloudFlare R2, etc.)

### 5. Redis and Channel Layer Configuration

**Component: Channel Layer Manager**
- **Purpose**: Configure Django Channels backend based on environment
- **Development Configuration**:
  ```python
  CHANNEL_LAYERS = {
      'default': {
          'BACKEND': 'channels.layers.InMemoryChannelLayer'
      }
  }
  ```

**Production Configuration**:
  ```python
  CHANNEL_LAYERS = {
      'default': {
          'BACKEND': 'channels_redis.core.RedisChannelLayer',
          'CONFIG': {
              'hosts': [config('REDIS_URL')],
              'capacity': 1500,
              'expiry': 10,
          },
      },
  }
  ```

**Component: Cache Configuration**
- **Purpose**: Configure caching backend
- **Production Configuration**:
  ```python
  CACHES = {
      'default': {
          'BACKEND': 'django_redis.cache.RedisCache',
          'LOCATION': config('REDIS_URL'),
          'OPTIONS': {
              'CLIENT_CLASS': 'django_redis.client.DefaultClient',
              'CONNECTION_POOL_KWARGS': {'max_connections': 50},
              'SOCKET_CONNECT_TIMEOUT': 5,
              'SOCKET_TIMEOUT': 5,
          }
      }
  }
  ```

### 6. Security Configuration Component

**Component: Security Settings Manager**
- **Purpose**: Enforce production security best practices
- **Configuration**:
  ```python
  # Core Security
  SECRET_KEY = config('SECRET_KEY')
  DEBUG = config('DEBUG', default=False, cast=bool)
  ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
  
  # HTTPS/SSL
  SECURE_SSL_REDIRECT = True
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  
  # HSTS
  SECURE_HSTS_SECONDS = 31536000  # 1 year
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  
  # Cookies
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SESSION_COOKIE_HTTPONLY = True
  CSRF_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = 'Lax'
  CSRF_COOKIE_SAMESITE = 'Lax'
  
  # CSRF
  CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv())
  
  # Headers
  SECURE_CONTENT_TYPE_NOSNIFF = True
  SECURE_BROWSER_XSS_FILTER = True
  X_FRAME_OPTIONS = 'DENY'
  SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
  ```

### 7. Logging Configuration Component

**Component: Production Logger**
- **Purpose**: Comprehensive logging for production monitoring
- **Configuration**:
  ```python
  LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'formatters': {
          'verbose': {
              'format': '[{levelname}] {asctime} {name} {module} {process:d} {thread:d} {message}',
              'style': '{',
          },
          'simple': {
              'format': '[{levelname}] {message}',
              'style': '{',
          },
      },
      'filters': {
          'require_debug_false': {
              '()': 'django.utils.log.RequireDebugFalse',
          },
      },
      'handlers': {
          'console': {
              'level': 'INFO',
              'class': 'logging.StreamHandler',
              'formatter': 'verbose',
          },
          'file': {
              'level': 'INFO',
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': BASE_DIR / 'logs' / 'django.log',
              'maxBytes': 1024 * 1024 * 10,  # 10 MB
              'backupCount': 5,
              'formatter': 'verbose',
          },
          'security_file': {
              'level': 'WARNING',
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': BASE_DIR / 'logs' / 'security.log',
              'maxBytes': 1024 * 1024 * 10,  # 10 MB
              'backupCount': 5,
              'formatter': 'verbose',
          },
          'mail_admins': {
              'level': 'ERROR',
              'class': 'django.utils.log.AdminEmailHandler',
              'filters': ['require_debug_false'],
          },
      },
      'loggers': {
          'django': {
              'handlers': ['console', 'file'],
              'level': 'INFO',
              'propagate': False,
          },
          'django.security': {
              'handlers': ['security_file', 'console', 'mail_admins'],
              'level': 'WARNING',
              'propagate': False,
          },
          'django.request': {
              'handlers': ['file', 'mail_admins'],
              'level': 'ERROR',
              'propagate': False,
          },
          'messaging': {
              'handlers': ['console', 'file'],
              'level': 'INFO',
              'propagate': False,
          },
      },
  }
  ```

### 8. Server Configuration Components

**Component: Gunicorn Configuration**
- **Purpose**: WSGI server for HTTP requests
- **Configuration File**: `gunicorn.conf.py`
  ```python
  import multiprocessing
  
  bind = "0.0.0.0:8000"
  workers = multiprocessing.cpu_count() * 2 + 1
  worker_class = "sync"
  worker_connections = 1000
  timeout = 30
  keepalive = 2
  
  # Logging
  accesslog = "-"
  errorlog = "-"
  loglevel = "info"
  
  # Process naming
  proc_name = "linkup_gunicorn"
  
  # Server mechanics
  daemon = False
  pidfile = None
  umask = 0
  user = None
  group = None
  tmp_upload_dir = None
  
  # SSL (if terminating SSL at application level)
  # keyfile = None
  # certfile = None
  ```

**Component: Daphne Configuration**
- **Purpose**: ASGI server for WebSocket connections
- **Command**: `daphne -b 0.0.0.0 -p 8001 professional_network.asgi:application`
- **Configuration**: Managed through environment variables and Django settings

**Component: Procfile (for Heroku/Platform deployment)**
- **Purpose**: Define process types for deployment platforms
- **Contents**:
  ```
  web: gunicorn professional_network.wsgi:application --config gunicorn.conf.py
  worker: daphne -b 0.0.0.0 -p $PORT professional_network.asgi:application
  release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
  ```

### 9. Health Check Component

**Component: Health Check Views**
- **Purpose**: Provide endpoints for monitoring and orchestration
- **File**: `core/health_views.py`
- **Endpoints**:
  1. `/health/` - Basic health check
  2. `/health/db/` - Database connectivity check
  3. `/health/redis/` - Redis connectivity check
  4. `/readiness/` - Readiness probe for deployment

**Interface**:
```python
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    """Basic health check"""
    return JsonResponse({'status': 'healthy'}, status=200)

def health_check_db(request):
    """Database connectivity check"""
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'healthy', 'database': 'connected'}, status=200)
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}, status=503)

def health_check_redis(request):
    """Redis connectivity check"""
    try:
        cache.set('health_check', 'ok', 10)
        value = cache.get('health_check')
        if value == 'ok':
            return JsonResponse({'status': 'healthy', 'redis': 'connected'}, status=200)
        else:
            return JsonResponse({'status': 'unhealthy', 'redis': 'disconnected'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'redis': 'disconnected', 'error': str(e)}, status=503)

def readiness_check(request):
    """Readiness probe - checks all dependencies"""
    checks = {
        'database': False,
        'redis': False,
    }
    
    try:
        connection.ensure_connection()
        checks['database'] = True
    except:
        pass
    
    try:
        cache.set('readiness_check', 'ok', 10)
        if cache.get('readiness_check') == 'ok':
            checks['redis'] = True
    except:
        pass
    
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503
    
    return JsonResponse({
        'status': 'ready' if all_ready else 'not_ready',
        'checks': checks
    }, status=status_code)
```

### 10. Git Configuration Component

**Component: .gitignore File**
- **Purpose**: Exclude sensitive and generated files from version control
- **Contents**:
  ```
  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  *.so
  .Python
  
  # Django
  *.log
  db.sqlite3
  db.sqlite3-journal
  /media/
  /staticfiles/
  /static/
  
  # Environment
  .env
  .env.local
  .env.*.local
  venv/
  env/
  ENV/
  
  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo
  *~
  .DS_Store
  
  # Testing
  .coverage
  htmlcov/
  .pytest_cache/
  
  # Logs
  logs/
  *.log
  
  # Node (for Tailwind)
  node_modules/
  npm-debug.log*
  yarn-debug.log*
  yarn-error.log*
  
  # Build
  build/
  dist/
  *.egg-info/
  ```

### 11. Error Page Templates

**Component: Custom Error Templates**
- **Purpose**: User-friendly error pages for production
- **Templates**:
  1. `templates/404.html` - Page not found
  2. `templates/500.html` - Server error
  3. `templates/403.html` - Permission denied

**Interface**: Django automatically uses these templates when DEBUG=False

## Data Models

No new data models are required for this feature. The existing models remain unchanged. However, the database backend changes from SQLite to PostgreSQL, which affects:

1. **Database Engine**: Switch from `django.db.backends.sqlite3` to `django.db.backends.postgresql`
2. **Connection Parameters**: Add host, port, user, password configuration
3. **Connection Pooling**: Enable `CONN_MAX_AGE` for persistent connections
4. **Data Migration**: Existing data must be exported from SQLite and imported to PostgreSQL

**Migration Process**:
1. Export data: `python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > datadump.json`
2. Set up PostgreSQL database
3. Run migrations on PostgreSQL: `python manage.py migrate`
4. Import data: `python manage.py loaddata datadump.json`
5. Verify data integrity

**Database Configuration Changes**:

Development (SQLite):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

Production (PostgreSQL):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

Alternative using DATABASE_URL:
```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas of redundancy:

1. **Security Settings Consolidation**: Requirements 3.1-3.10 all check individual security settings in production. These can be combined into a single comprehensive property that verifies all security settings are correctly configured.

2. **Gitignore Pattern Consolidation**: Requirements 6.2-6.8 all check individual .gitignore patterns. These can be combined into a single property that verifies all critical patterns are present.

3. **Dependency Consolidation**: Requirements 5.1-5.5 all check individual dependencies. These can be combined into a single property that verifies all required production dependencies are present.

4. **Logging Configuration Consolidation**: Requirements 9.1-9.3, 9.5-9.7 all check logging configuration aspects. These can be combined into a single property that verifies comprehensive logging setup.

5. **Error Page Consolidation**: Requirements 10.1-10.3 all check custom error pages. These can be combined into a single property.

6. **Environment Variable Loading**: Requirements 7.3-7.7 all check individual environment variables. These can be combined into a single property that verifies all required variables are loaded.

The following properties represent the unique, non-redundant validation requirements:

### Configuration Properties

**Property 1: Environment-based database configuration**
*For any* environment setting (production or development), when the application starts, the database configuration should match the environment: PostgreSQL with environment variables in production, SQLite in development.
**Validates: Requirements 1.1, 1.2, 1.3**

**Property 2: Settings module inheritance**
*For any* environment-specific settings module (development or production), it should import from base settings and override only environment-specific values, maintaining all shared configuration.
**Validates: Requirements 2.2, 2.4**

**Property 3: Production security configuration completeness**
*For any* production settings configuration, all security settings (DEBUG=False, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, secure cookies, CSRF protection, security headers) should be properly enabled and configured.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10**

**Property 4: Required production dependencies presence**
*For any* requirements.txt file, it should contain all required production dependencies (psycopg2-binary, gunicorn, daphne, whitenoise, python-decouple) with pinned versions.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.7**

**Property 5: Gitignore pattern completeness**
*For any* .gitignore file, it should contain all critical patterns (db.sqlite3, __pycache__, *.pyc, .env, media/, staticfiles/, logs/, IDE files) to prevent sensitive data from being committed.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8**

**Property 6: Environment variable loading with defaults**
*For any* required environment variable, the settings should load it from the environment with appropriate defaults for optional variables, and raise clear errors when required variables are missing.
**Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9**

**Property 7: Channel layer environment configuration**
*For any* environment setting, the CHANNEL_LAYERS configuration should use RedisChannelLayer with REDIS_URL in production and InMemoryChannelLayer in development.
**Validates: Requirements 8.1, 8.2, 8.3**

**Property 8: Production logging configuration completeness**
*For any* production logging configuration, it should include both file and console handlers, separate security logs, structured formatting with timestamps, rotating file handlers, and appropriate log levels.
**Validates: Requirements 9.1, 9.2, 9.3, 9.5, 9.6, 9.7**

### Runtime Behavior Properties

**Property 9: Database connection error handling**
*For any* invalid database credentials, when the application attempts to connect, it should log detailed error information and fail gracefully without exposing sensitive information.
**Validates: Requirements 1.4**

**Property 10: Redis connection error handling**
*For any* invalid Redis URL, when the application attempts to connect to Redis, it should log detailed error information without crashing the application.
**Validates: Requirements 8.4**

**Property 11: Media file upload storage**
*For any* valid media file upload, the file should be stored in the configured MEDIA_ROOT directory and be accessible via MEDIA_URL.
**Validates: Requirements 4.7**

**Property 12: Error logging with stack traces**
*For any* unhandled exception in production, the system should log the full stack trace to the error log file while displaying a user-friendly error page.
**Validates: Requirements 9.4**

**Property 13: Custom error page display**
*For any* HTTP error (404, 500, 403) in production mode (DEBUG=False), the system should display the corresponding custom error template without exposing sensitive debugging information.
**Validates: Requirements 10.1, 10.2, 10.3, 10.5**

### Health Check Properties

**Property 14: Health endpoint availability**
*For any* request to the /health/ endpoint, when all dependencies are healthy, the system should return a 200 OK response with status information.
**Validates: Requirements 15.1**

**Property 15: Database health check**
*For any* request to the /health/db/ endpoint, the system should verify database connectivity and return 200 if connected or 503 if disconnected.
**Validates: Requirements 15.2**

**Property 16: Redis health check**
*For any* request to the /health/redis/ endpoint, the system should verify Redis connectivity and return 200 if connected or 503 if disconnected.
**Validates: Requirements 15.3**

**Property 17: Health check failure status codes**
*For any* health check endpoint, when a dependency check fails, the system should return a 503 Service Unavailable status code with details about which check failed.
**Validates: Requirements 15.4**

**Property 18: Readiness probe comprehensive check**
*For any* request to the /readiness/ endpoint, the system should check all dependencies (database and Redis) and return 200 only when all are ready, or 503 with details about which dependencies are not ready.
**Validates: Requirements 15.5**

### Configuration Validation Properties (Examples)

The following are specific configuration checks that validate the setup is correct:

**Example 1: Static files configuration**
The production settings should configure WhiteNoise middleware, STATIC_ROOT, STATIC_URL, and CompressedManifestStaticFilesStorage.
**Validates: Requirements 4.1, 4.2, 4.3, 4.5**

**Example 2: Media files configuration**
The settings should configure MEDIA_URL and MEDIA_ROOT for user-uploaded content.
**Validates: Requirements 4.4**

**Example 3: Settings module structure**
The project should have settings/base.py, settings/development.py, and settings/production.py files with proper imports.
**Validates: Requirements 2.1, 2.3**

**Example 4: Connection pooling configuration**
The production database configuration should include CONN_MAX_AGE setting for connection pooling.
**Validates: Requirements 1.5**

**Example 5: .env.example file**
The project should include a .env.example file documenting all required environment variables.
**Validates: Requirements 7.1**

**Example 6: Redis connection pool settings**
The production CHANNEL_LAYERS configuration should include capacity and expiry settings for Redis connection pooling.
**Validates: Requirements 8.5**

**Example 7: Performance configuration**
The production settings should configure DATA_UPLOAD_MAX_MEMORY_SIZE, FILE_UPLOAD_MAX_MEMORY_SIZE, and compression settings.
**Validates: Requirements 11.2, 11.3, 11.6, 11.7**

**Example 8: Redis caching configuration**
The production CACHES configuration should use django_redis.cache.RedisCache with appropriate connection pool settings.
**Validates: Requirements 11.1**

**Example 9: Gunicorn configuration file**
The project should include gunicorn.conf.py with worker count, timeout, and logging configuration.
**Validates: Requirements 13.1, 13.4**

**Example 10: Procfile for platform deployment**
The project should include a Procfile with web (Gunicorn) and worker (Daphne) process definitions.
**Validates: Requirements 13.2, 13.3**

**Example 11: Reverse proxy configuration**
The production settings should configure SECURE_PROXY_SSL_HEADER for reverse proxy support.
**Validates: Requirements 13.6**

## Error Handling

### Database Connection Errors

**Scenario**: PostgreSQL database is unavailable or credentials are incorrect

**Handling**:
1. Django will raise `OperationalError` or `DatabaseError`
2. Application should log detailed error with connection parameters (excluding password)
3. Health check endpoints should return 503 status
4. Application should fail to start with clear error message
5. Logs should include: timestamp, error type, database host, port, and database name

**Implementation**:
```python
# In settings/production.py
import logging
logger = logging.getLogger(__name__)

try:
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
except Exception as e:
    logger.error(f"Database configuration error: {e}")
    raise
```

### Redis Connection Errors

**Scenario**: Redis is unavailable or REDIS_URL is incorrect

**Handling**:
1. For Channel Layer: WebSocket connections will fail gracefully
2. For Cache: Cache operations will fail but application continues
3. Health check endpoints should return 503 for Redis check
4. Logs should include: timestamp, error type, Redis URL (excluding password)
5. Application should start but log warnings about Redis unavailability

**Implementation**:
```python
# In health check view
def health_check_redis(request):
    try:
        cache.set('health_check', 'ok', 10)
        value = cache.get('health_check')
        if value == 'ok':
            return JsonResponse({'status': 'healthy', 'redis': 'connected'}, status=200)
        else:
            logger.warning("Redis health check failed: value mismatch")
            return JsonResponse({'status': 'unhealthy', 'redis': 'disconnected'}, status=503)
    except Exception as e:
        logger.error(f"Redis health check error: {e}")
        return JsonResponse({'status': 'unhealthy', 'redis': 'disconnected', 'error': str(e)}, status=503)
```

### Missing Environment Variables

**Scenario**: Required environment variable is not set

**Handling**:
1. python-decouple raises `UndefinedValueError`
2. Application should fail to start immediately
3. Error message should clearly state which variable is missing
4. Error message should reference .env.example file
5. No partial startup or degraded mode

**Implementation**:
```python
# In settings/production.py
from decouple import config, UndefinedValueError

try:
    SECRET_KEY = config('SECRET_KEY')
except UndefinedValueError:
    raise ImproperlyConfigured(
        "SECRET_KEY environment variable is required. "
        "Please set it in your environment or .env file. "
        "See .env.example for reference."
    )
```

### Static File Collection Errors

**Scenario**: collectstatic fails due to permissions or missing directories

**Handling**:
1. Django raises `CommandError`
2. Deployment should fail before starting the application
3. Error should indicate which directory has permission issues
4. Logs should include full path and permission details
5. Deployment platform should show clear error in build logs

### File Upload Errors

**Scenario**: Media file upload exceeds size limits or invalid file type

**Handling**:
1. Django raises `RequestDataTooBig` or validation error
2. Return 413 Payload Too Large or 400 Bad Request
3. Display user-friendly error message
4. Log the attempt with user ID, file size, and file type
5. Do not save partial files

**Implementation**:
```python
# In settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# In view
def handle_file_upload(request):
    try:
        uploaded_file = request.FILES['file']
        # Process file
    except RequestDataTooBig:
        logger.warning(f"File upload too large from user {request.user.id}")
        return JsonResponse({'error': 'File size exceeds 50MB limit'}, status=413)
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return JsonResponse({'error': 'File upload failed'}, status=400)
```

### HTTP Error Pages

**Scenario**: 404, 500, or 403 errors occur in production

**Handling**:
1. Django automatically uses custom templates when DEBUG=False
2. Templates should be in templates/404.html, templates/500.html, templates/403.html
3. Error pages should match application branding
4. No sensitive information (settings, stack traces) should be exposed
5. Error details logged to file but not shown to user
6. 500 errors should trigger admin email notification (if configured)

### Database Migration Errors

**Scenario**: Migration fails during deployment

**Handling**:
1. Django raises `MigrationError`
2. Deployment should stop before starting application
3. Database should remain in previous consistent state
4. Error should indicate which migration failed
5. Rollback instructions should be in deployment documentation
6. No partial migrations should be applied

### WebSocket Connection Errors

**Scenario**: WebSocket connection fails or Redis is unavailable

**Handling**:
1. Connection attempt returns error to client
2. Client should display "Unable to connect to real-time features"
3. Application continues to work for non-WebSocket features
4. Logs should include: timestamp, user ID, error type
5. Health check should indicate Redis unavailability

## Testing Strategy

### Dual Testing Approach

This feature requires both **unit tests** and **property-based tests** for comprehensive coverage:

- **Unit tests**: Verify specific configuration examples, file existence, and edge cases
- **Property tests**: Verify universal properties across different configurations and inputs

Both testing approaches are complementary and necessary. Unit tests catch concrete configuration bugs, while property tests verify general correctness across many scenarios.

### Property-Based Testing Configuration

**Library**: We will use **Hypothesis** for Python property-based testing

**Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: production-deployment-setup, Property {number}: {property_text}`

**Example Property Test**:
```python
from hypothesis import given, strategies as st
import pytest

# Feature: production-deployment-setup, Property 1: Environment-based database configuration
@given(environment=st.sampled_from(['production', 'development']))
def test_database_configuration_matches_environment(environment):
    """
    For any environment setting (production or development), 
    the database configuration should match the environment.
    """
    os.environ['DJANGO_ENVIRONMENT'] = environment
    
    if environment == 'production':
        # Verify PostgreSQL configuration
        assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
        assert 'HOST' in settings.DATABASES['default']
    else:
        # Verify SQLite configuration
        assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
```

### Unit Testing Strategy

**Focus Areas**:
1. **Configuration Validation**: Test that specific settings are correctly configured
2. **File Existence**: Verify required files (.gitignore, .env.example, Procfile) exist
3. **Health Check Endpoints**: Test health check responses with mocked dependencies
4. **Error Handling**: Test specific error scenarios (missing env vars, connection failures)
5. **Static File Collection**: Test collectstatic command succeeds
6. **Template Rendering**: Test custom error pages render correctly

**Example Unit Tests**:
```python
def test_production_debug_is_false():
    """Verify DEBUG is False in production settings"""
    from professional_network.settings.production import DEBUG
    assert DEBUG is False

def test_gitignore_excludes_sensitive_files():
    """Verify .gitignore contains critical patterns"""
    with open('.gitignore', 'r') as f:
        content = f.read()
    assert 'db.sqlite3' in content
    assert '.env' in content
    assert '__pycache__' in content

def test_health_endpoint_returns_200():
    """Test health check endpoint when healthy"""
    response = client.get('/health/')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_missing_secret_key_raises_error():
    """Test that missing SECRET_KEY raises clear error"""
    del os.environ['SECRET_KEY']
    with pytest.raises(ImproperlyConfigured) as exc_info:
        importlib.reload(settings)
    assert 'SECRET_KEY' in str(exc_info.value)
```

### Integration Testing

**Scenarios to Test**:
1. **Full Deployment Simulation**: Test complete deployment process locally
2. **Database Migration**: Test SQLite to PostgreSQL migration with sample data
3. **Static File Serving**: Test WhiteNoise serves static files correctly
4. **WebSocket Connections**: Test real-time messaging with Redis
5. **Health Checks**: Test all health check endpoints with real dependencies
6. **Error Pages**: Test custom error pages display in production mode

### Manual Testing Checklist

Before deployment, manually verify:
- [ ] Environment variables are set correctly
- [ ] PostgreSQL database is accessible
- [ ] Redis is accessible
- [ ] collectstatic runs successfully
- [ ] Migrations run successfully
- [ ] Gunicorn starts without errors
- [ ] Daphne starts without errors
- [ ] Health check endpoints return 200
- [ ] Static files load correctly
- [ ] Media file uploads work
- [ ] WebSocket connections work
- [ ] Custom error pages display
- [ ] Logs are being written
- [ ] HTTPS redirect works (if applicable)

### Continuous Integration

**CI Pipeline Steps**:
1. Install dependencies from requirements.txt
2. Run unit tests
3. Run property-based tests (100 iterations minimum)
4. Check code coverage (target: 80%+)
5. Run security checks (bandit, safety)
6. Verify .gitignore excludes sensitive files
7. Test collectstatic command
8. Test migrations on PostgreSQL
9. Generate test report

**CI Configuration Example** (.github/workflows/test.yml):
```yaml
name: Test Production Setup

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest hypothesis pytest-django pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          DEBUG: False
        run: |
          pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Test Organization

```
tests/
├── unit/
│   ├── test_settings_configuration.py
│   ├── test_environment_variables.py
│   ├── test_health_checks.py
│   └── test_error_pages.py
├── property/
│   ├── test_database_configuration.py
│   ├── test_security_settings.py
│   ├── test_environment_loading.py
│   └── test_health_check_behavior.py
├── integration/
│   ├── test_full_deployment.py
│   ├── test_database_migration.py
│   └── test_websocket_with_redis.py
└── conftest.py  # Shared fixtures
```

### Property Test Examples

Each correctness property should be implemented as a property-based test:

```python
# Feature: production-deployment-setup, Property 3: Production security configuration completeness
@pytest.mark.django_db
def test_production_security_settings_complete():
    """
    For any production settings configuration, all security settings should be enabled.
    """
    from professional_network.settings.production import (
        DEBUG, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS,
        SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE,
        SECURE_CONTENT_TYPE_NOSNIFF, SECURE_BROWSER_XSS_FILTER,
        X_FRAME_OPTIONS
    )
    
    assert DEBUG is False
    assert SECURE_SSL_REDIRECT is True
    assert SECURE_HSTS_SECONDS >= 31536000
    assert SESSION_COOKIE_SECURE is True
    assert CSRF_COOKIE_SECURE is True
    assert SECURE_CONTENT_TYPE_NOSNIFF is True
    assert SECURE_BROWSER_XSS_FILTER is True
    assert X_FRAME_OPTIONS == 'DENY'

# Feature: production-deployment-setup, Property 9: Database connection error handling
@given(invalid_url=st.text(min_size=1, max_size=100))
def test_database_connection_error_handling(invalid_url, caplog):
    """
    For any invalid database credentials, the application should log errors and fail gracefully.
    """
    os.environ['DATABASE_URL'] = invalid_url
    
    with pytest.raises((OperationalError, DatabaseError, ImproperlyConfigured)):
        # Attempt to connect
        connection.ensure_connection()
    
    # Verify error was logged
    assert any('database' in record.message.lower() for record in caplog.records)

# Feature: production-deployment-setup, Property 14: Health endpoint availability
@pytest.mark.django_db
def test_health_endpoint_always_responds():
    """
    For any request to /health/, the system should return a response.
    """
    client = Client()
    response = client.get('/health/')
    
    assert response.status_code in [200, 503]
    assert 'status' in response.json()
```

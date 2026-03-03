"""
Base Django settings for professional_network project.
Shared configuration for all environments.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Application definition

INSTALLED_APPS = [
    # Local apps
    'linkup',  # Admin customization (Must be first to override template)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',  # Django REST framework for API
    'tailwind',
    'django_browser_reload',
    'ckeditor',
    'ckeditor_uploader',
    # Channels for real-time features
    'channels',
    'core',
    'users',
    'feed',
    'network',
    'jobs',
    'theme',
    'messaging',
    'ai_agents',  # AI agents app
]

# CKEditor upload settings
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_ALLOW_NONIMAGE_FILES = False
CKEDITOR_BASEPATH = "/static/ckeditor/ckeditor/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 200,
        'width': '100%'
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this line
    'core.middleware.SecurityHeadersMiddleware',
    'core.performance.PerformanceMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.SessionSecurityMiddleware',
    'ai_agents.middleware.CorrelationIdMiddleware',  # Add correlation IDs to all requests
    'ai_agents.middleware.AgentAuthenticationMiddleware',  # AI agent authentication
    'ai_agents.middleware.AgentRateLimitMiddleware',  # AI agent rate limiting
    'core.middleware.RateLimitMiddleware',
    'core.middleware.RequestValidationMiddleware',
    'core.middleware.FileUploadSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

ROOT_URLCONF = 'professional_network.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'professional_network.wsgi.application'
ASGI_APPLICATION = 'professional_network.asgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
AUTH_USER_MODEL = 'users.User'
LOGIN_REDIRECT_URL = 'feed'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'

# Tailwind
TAILWIND_APP_NAME = 'theme'
NPM_BIN_PATH = "npm"

# Performance Settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Centralized Logging Configuration
# Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {funcName} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            'format': '{"level": "{levelname}", "time": "{asctime}", "logger": "{name}", "module": "{module}", "function": "{funcName}", "message": "{message}"}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file_authentication': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'authentication.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_communication': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'communication.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_rate_limit': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'rate_limit.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_validation': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'validation.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_system': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'system.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_all_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'ai_agents.authentication': {
            'handlers': ['console', 'file_authentication', 'file_all_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai_agents.communication': {
            'handlers': ['console', 'file_communication', 'file_all_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai_agents.rate_limit': {
            'handlers': ['console', 'file_rate_limit', 'file_all_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai_agents.validation': {
            'handlers': ['console', 'file_validation', 'file_all_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai_agents.system': {
            'handlers': ['console', 'file_system', 'file_all_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'file_system'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file_system'],
        'level': 'INFO',
    },
}

# File ke end me add karo
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True


# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
}


# AI Agent System Health Monitoring Configuration
# Requirements: 20.7
AI_AGENT_HEALTH_THRESHOLDS = {
    # Maximum number of active agents before triggering alert
    'max_active_agents': 10000,
    
    # Maximum messages per minute before triggering alert
    'max_messages_per_minute': 10000,
    
    # Maximum average message latency in milliseconds before triggering alert
    'max_avg_latency_ms': 5000,
    
    # Maximum WebSocket connections before triggering alert
    'max_websocket_connections': 10000,
    
    # Maximum API requests per minute before triggering alert
    'max_api_requests_per_minute': 50000,
}

# Alert notification configuration
AI_AGENT_ALERT_CONFIG = {
    # Enable/disable alerting
    'enabled': True,
    
    # Alert check interval in seconds (how often to check thresholds)
    'check_interval': 60,
    
    # Notification channels (email, slack, webhook, etc.)
    'notification_channels': ['log'],  # Default to logging only
    
    # Email configuration for alerts (if email channel enabled)
    'email': {
        'enabled': False,
        'recipients': [],  # List of email addresses
        'subject_prefix': '[AI Agent Platform Alert]',
    },
    
    # Slack configuration for alerts (if slack channel enabled)
    'slack': {
        'enabled': False,
        'webhook_url': '',
        'channel': '#alerts',
    },
    
    # Webhook configuration for custom integrations
    'webhook': {
        'enabled': False,
        'url': '',
        'method': 'POST',
        'headers': {},
    },
}

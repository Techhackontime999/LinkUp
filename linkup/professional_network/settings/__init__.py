"""
Settings module initialization.
Loads appropriate settings based on DJANGO_ENVIRONMENT variable.
"""
import os

# Determine which settings to use
ENVIRONMENT = os.environ.get('DJANGO_ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    from .production import *
else:
    from .development import *

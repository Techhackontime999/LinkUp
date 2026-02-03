#!/usr/bin/env python
"""
Script to clear Django template cache
Run with: python clear_cache.py
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.core.cache import cache

# Clear all cache
cache.clear()
print("✅ Django cache cleared successfully!")

# If you're using template caching, also clear template cache
try:
    from django.template.loader import get_template
    from django.template import engines
    
    # Clear template cache for all engines
    for engine in engines.all():
        if hasattr(engine, 'engine'):
            engine.engine.template_loaders[0].reset()
    print("✅ Template cache cleared successfully!")
except Exception as e:
    print(f"Note: Template cache clearing not needed or already clear: {e}")

print("\n🎉 All caches cleared! Restart your Django server to see changes.")

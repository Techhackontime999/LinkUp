#!/usr/bin/env python3
"""
Clear rate limit cache to reset all rate limits.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.core.cache import cache

print("=" * 60)
print("CLEARING RATE LIMIT CACHE")
print("=" * 60)

# Clear all rate limit keys
keys_cleared = 0
try:
    # Try to get all keys (works with some cache backends)
    all_keys = cache.keys('rate_limit_*')
    for key in all_keys:
        cache.delete(key)
        keys_cleared += 1
    print(f"✓ Cleared {keys_cleared} rate limit keys")
except:
    # If keys() is not supported, clear entire cache
    cache.clear()
    print("✓ Cleared entire cache (including rate limits)")

print("\n" + "=" * 60)
print("✅ RATE LIMITS RESET")
print("=" * 60)
print("\nRate limits have been reset. You can now:")
print("  • Make requests without hitting the limit")
print("  • The new limits are:")
print("    - Default: 120 requests/minute")
print("    - Auth: 10 requests/minute")
print("    - API: 200 requests/minute")
print("    - Upload: 20 requests/minute")
print("    - Message: 60 requests/minute")
print("    - Search: 40 requests/minute")

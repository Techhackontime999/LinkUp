#!/usr/bin/env python3
"""
Script to check if Redis is running and provide setup instructions.
"""
import sys

try:
    import redis
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)
    r.ping()
    print("✓ Redis is running and accessible!")
    print("✓ Real-time messaging should work properly.")
    sys.exit(0)
except ImportError:
    print("✗ Redis Python client not installed.")
    print("\nTo install: pip install redis")
    sys.exit(1)
except redis.ConnectionError:
    print("✗ Redis server is not running.")
    print("\n=== Setup Instructions ===")
    print("\n1. Install Redis:")
    print("   - Ubuntu/Debian: sudo apt-get install redis-server")
    print("   - macOS: brew install redis")
    print("   - Windows: Download from https://redis.io/download")
    print("\n2. Start Redis:")
    print("   - Ubuntu/Debian: sudo systemctl start redis-server")
    print("   - macOS: brew services start redis")
    print("   - Or run manually: redis-server")
    print("\n3. Verify Redis is running:")
    print("   redis-cli ping")
    print("   (should return 'PONG')")
    print("\n=== Alternative: Use In-Memory Channel Layer ===")
    print("\nFor development without Redis, update settings.py:")
    print("""
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}
""")
    print("\nNote: In-memory layer doesn't support multiple workers.")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error connecting to Redis: {e}")
    sys.exit(1)

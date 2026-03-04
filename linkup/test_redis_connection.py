"""
Quick test to check if Redis is running and accessible.
"""
import sys

try:
    import redis
    
    # Try to connect to Redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Test connection
    if r.ping():
        print("✅ SUCCESS: Redis is running and accessible!")
        print(f"   Host: localhost")
        print(f"   Port: 6379")
        
        # Test set/get
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"   Test write/read: {value}")
        r.delete('test_key')
        
        print("\n✅ Redis is ready for WebSocket support!")
    else:
        print("❌ ERROR: Redis is not responding")
        sys.exit(1)
        
except redis.ConnectionError:
    print("❌ ERROR: Cannot connect to Redis")
    print("\nRedis is not running. Please start Redis:")
    print("  - Docker: docker run -d -p 6379:6379 redis:latest")
    print("  - Memurai: net start Memurai")
    print("  - WSL: sudo service redis-server start")
    sys.exit(1)
    
except ImportError:
    print("❌ ERROR: redis package not installed")
    print("\nInstall it with: pip install redis")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

#!/usr/bin/env python3
"""
LinkUp Version Checker
Displays current version and system information
"""

import os
import sys
import django
from pathlib import Path

def get_version():
    """Get LinkUp version from VERSION file"""
    version_file = Path(__file__).parent / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return "Unknown"

def check_system():
    """Check system requirements"""
    print("🔍 LinkUp System Check")
    print("=" * 50)
    
    # Version
    version = get_version()
    print(f"📦 LinkUp Version: {version}")
    
    # Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"🐍 Python Version: {python_version}")
    
    # Check Python version requirement
    if sys.version_info >= (3, 10):
        print("✅ Python version requirement met (3.10+)")
    else:
        print("❌ Python 3.10+ required")
        return False
    
    # Django version
    try:
        print(f"🌐 Django Version: {django.get_version()}")
    except Exception as e:
        print(f"❌ Django not properly installed: {e}")
        return False
    
    # Check if in LinkUp directory
    if Path('manage.py').exists():
        print("✅ LinkUp project directory detected")
    else:
        print("❌ Not in LinkUp project directory")
        return False
    
    # Check database
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')
        django.setup()
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
    except Exception as e:
        print(f"⚠️  Database connection issue: {e}")
    
    # Check static files
    static_dir = Path('staticfiles')
    if static_dir.exists():
        print("✅ Static files directory exists")
    else:
        print("⚠️  Static files not collected (run collectstatic)")
    
    print("\n🎉 LinkUp v1.0.0 - Professional Network Platform")
    print("👨‍💻 Founded by: Techhackontime999")
    print("📧 Support: amitkumarkh010102006@gmail.com")
    print("🔗 Repository: https://github.com/Techhackontime999/LinkUp.git")
    
    return True

if __name__ == "__main__":
    try:
        success = check_system()
        if success:
            print("\n✅ System check completed successfully!")
        else:
            print("\n❌ System check failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 System check cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
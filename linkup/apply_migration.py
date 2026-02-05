#!/usr/bin/env python3
"""
Apply the database migration for the updated_at field
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings.development')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

def apply_migration():
    """Apply the database migration"""
    try:
        print("🔄 Applying database migration for updated_at field...")
        
        # Apply the migration
        execute_from_command_line(['manage.py', 'migrate', 'messaging'])
        
        print("✅ Migration applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    if success:
        print("\n💡 The updated_at field has been added to the Message model.")
        print("You can now run the async context tests.")
    else:
        print("\n⚠️  Migration failed. Please check the error above.")
    
    sys.exit(0 if success else 1)
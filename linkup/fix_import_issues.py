#!/usr/bin/env python3
"""
Fix remaining import issues in messaging system
"""
import os
import re

def fix_sync_to_async_imports():
    """Fix incorrect sync_to_async imports"""
    files_to_fix = [
        'messaging/read_receipt_manager.py',
        'messaging/offline_queue_manager.py', 
        'messaging/message_sync_manager.py'
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"Fixing imports in {file_path}...")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace incorrect imports
            content = re.sub(
                r'from django\.db import sync_to_async',
                'from channels.db import database_sync_to_async',
                content
            )
            
            # Replace decorator usage
            content = re.sub(
                r'@sync_to_async',
                '@database_sync_to_async',
                content
            )
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Fixed imports in {file_path}")
        else:
            print(f"⚠️  File not found: {file_path}")

def main():
    """Run all fixes"""
    print("🔧 Fixing Import Issues")
    print("=" * 30)
    
    try:
        fix_sync_to_async_imports()
        print("\n✅ All import issues fixed!")
        print("\n💡 Next steps:")
        print("1. Restart Django server")
        print("2. Test WebSocket messaging")
        
    except Exception as e:
        print(f"❌ Error fixing imports: {e}")

if __name__ == "__main__":
    main()
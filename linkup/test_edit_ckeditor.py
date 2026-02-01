#!/usr/bin/env python3
"""
Test script to verify CKEditor is properly configured for edit post modal.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.conf import settings
from pathlib import Path

def test_ckeditor_configuration():
    """Test CKEditor configuration and file availability."""
    
    print("=" * 60)
    print("Testing CKEditor Configuration for Edit Post Modal")
    print("=" * 60)
    
    # Check if CKEditor is in INSTALLED_APPS
    print("\n1. Checking INSTALLED_APPS...")
    if 'ckeditor' in settings.INSTALLED_APPS:
        print("   ✓ CKEditor is installed")
    else:
        print("   ✗ CKEditor is NOT installed")
        return False
    
    if 'ckeditor_uploader' in settings.INSTALLED_APPS:
        print("   ✓ CKEditor Uploader is installed")
    else:
        print("   ✗ CKEditor Uploader is NOT installed")
        return False
    
    # Check CKEditor settings
    print("\n2. Checking CKEditor settings...")
    if hasattr(settings, 'CKEDITOR_UPLOAD_PATH'):
        print(f"   ✓ CKEDITOR_UPLOAD_PATH: {settings.CKEDITOR_UPLOAD_PATH}")
    else:
        print("   ✗ CKEDITOR_UPLOAD_PATH not configured")
    
    if hasattr(settings, 'CKEDITOR_CONFIGS'):
        print(f"   ✓ CKEDITOR_CONFIGS is configured")
    else:
        print("   ✗ CKEDITOR_CONFIGS not configured")
    
    # Check if CKEditor static files exist
    print("\n3. Checking CKEditor static files...")
    static_root = Path(settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') else Path('staticfiles')
    ckeditor_js = static_root / 'ckeditor' / 'ckeditor' / 'ckeditor.js'
    
    if ckeditor_js.exists():
        print(f"   ✓ CKEditor JavaScript found at: {ckeditor_js}")
    else:
        print(f"   ✗ CKEditor JavaScript NOT found at: {ckeditor_js}")
        print(f"   Looking in: {static_root}")
    
    # Check template file
    print("\n4. Checking template modifications...")
    template_path = Path('feed/templates/feed/index.html')
    
    if template_path.exists():
        with open(template_path, 'r') as f:
            content = f.read()
            
        checks = [
            ('editPostContent textarea', 'id="editPostContent"' in content),
            ('CKEditor initialization', 'CKEDITOR.replace' in content),
            ('CKEditor getData', 'editCKEditor.getData()' in content),
            ('CKEditor script load', 'ckeditor.js' in content),
        ]
        
        for check_name, result in checks:
            if result:
                print(f"   ✓ {check_name} found")
            else:
                print(f"   ✗ {check_name} NOT found")
    else:
        print(f"   ✗ Template not found at: {template_path}")
    
    print("\n" + "=" * 60)
    print("Configuration Test Complete!")
    print("=" * 60)
    
    print("\n📝 Next Steps:")
    print("1. Start the Django development server")
    print("2. Navigate to the feed page")
    print("3. Click the 3-dot menu on any of your posts")
    print("4. Click 'Edit Post'")
    print("5. Verify that CKEditor loads in the modal with rich text editing")
    print("\n✨ The content field should now have formatting toolbar!")
    
    return True

if __name__ == '__main__':
    test_ckeditor_configuration()

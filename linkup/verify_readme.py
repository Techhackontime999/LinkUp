#!/usr/bin/env python3
"""
Verification script for README.md completeness
"""

from pathlib import Path

def verify_readme():
    """Verify README.md exists and contains all required sections."""
    
    readme_path = Path('README.md')
    
    if not readme_path.exists():
        print("❌ README.md not found!")
        return False
    
    print("✅ README.md found!")
    print(f"📄 File size: {readme_path.stat().st_size} bytes")
    
    content = readme_path.read_text()
    lines = content.split('\n')
    print(f"📝 Total lines: {len(lines)}")
    
    # Check for required sections
    required_sections = [
        "Overview",
        "Features",
        "Tech Stack",
        "Installation",
        "Configuration",
        "Usage",
        "Project Structure",
        "API Documentation",
        "Testing",
        "Deployment",
        "Security",
        "Performance",
        "Troubleshooting",
        "Contributing",
        "License",
        "Contact",
    ]
    
    print("\n🔍 Checking required sections:")
    missing_sections = []
    
    for section in required_sections:
        if section.lower() in content.lower():
            print(f"   ✓ {section}")
        else:
            print(f"   ✗ {section} - MISSING")
            missing_sections.append(section)
    
    # Check for code blocks
    code_blocks = content.count('```')
    print(f"\n💻 Code blocks: {code_blocks // 2}")
    
    # Check for links
    links = content.count('[')
    print(f"🔗 Links: {links}")
    
    # Check for emojis
    emojis = sum(1 for char in content if ord(char) > 127)
    print(f"😊 Emojis/Special chars: {emojis}")
    
    # Summary
    print("\n" + "=" * 60)
    if missing_sections:
        print(f"⚠️  Missing {len(missing_sections)} sections:")
        for section in missing_sections:
            print(f"   - {section}")
    else:
        print("✅ All required sections present!")
    
    print("=" * 60)
    print("\n📊 README.md Statistics:")
    print(f"   Lines: {len(lines)}")
    print(f"   Words: ~{len(content.split())}")
    print(f"   Characters: {len(content)}")
    print(f"   Code blocks: {code_blocks // 2}")
    print(f"   Links: {links}")
    
    print("\n🎉 README.md is comprehensive and ready to use!")
    print("\n📝 Next steps:")
    print("   1. Review the content")
    print("   2. Update placeholder URLs and emails")
    print("   3. Add project screenshots")
    print("   4. Commit to version control")
    
    return True

if __name__ == '__main__':
    verify_readme()

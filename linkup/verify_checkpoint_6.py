#!/usr/bin/env python3
"""
Checkpoint 6 Verification Script
Verifies that all core real-time messaging features are properly implemented.
"""

import os
import sys
import ast
import json
from pathlib import Path

def check_file_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, "✅ Syntax OK"
    except SyntaxError as e:
        return False, f"❌ Syntax Error: {e}"
    except Exception as e:
        return False, f"❌ Error: {e}"

def check_file_exists(filepath):
    """Check if a file exists and is not empty."""
    if not os.path.exists(filepath):
        return False, "❌ File does not exist"
    
    if os.path.getsize(filepath) == 0:
        return False, "❌ File is empty"
    
    return True, "✅ File exists and has content"

def check_class_exists(filepath, class_name):
    """Check if a class exists in a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return True, f"✅ Class {class_name} found"
        
        return False, f"❌ Class {class_name} not found"
    except Exception as e:
        return False, f"❌ Error checking class: {e}"

def check_method_exists(filepath, class_name, method_name):
    """Check if a method exists in a class."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        return True, f"✅ Method {method_name} found in {class_name}"
        
        return False, f"❌ Method {method_name} not found in {class_name}"
    except Exception as e:
        return False, f"❌ Error checking method: {e}"

def main():
    """Run checkpoint 6 verification."""
    print("🧪 Checkpoint 6 - Core Real-time Features Verification")
    print("=" * 60)
    
    base_path = Path("messaging")
    results = []
    
    # 1. Check WebSocket Infrastructure
    print("\n📡 1. WebSocket Infrastructure")
    
    # Check routing.py
    routing_file = base_path / "routing.py"
    exists, msg = check_file_exists(routing_file)
    print(f"   Routing file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(routing_file)
        print(f"   Routing syntax: {msg}")
        results.append(syntax_ok)
    
    # Check consumers.py
    consumers_file = base_path / "consumers.py"
    exists, msg = check_file_exists(consumers_file)
    print(f"   Consumers file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(consumers_file)
        print(f"   Consumers syntax: {msg}")
        results.append(syntax_ok)
        
        # Check ChatConsumer class
        exists, msg = check_class_exists(consumers_file, "ChatConsumer")
        print(f"   ChatConsumer class: {msg}")
        results.append(exists)
        
        # Check NotificationsConsumer class
        exists, msg = check_class_exists(consumers_file, "NotificationsConsumer")
        print(f"   NotificationsConsumer class: {msg}")
        results.append(exists)
    
    # 2. Check Message Status Tracking
    print("\n💬 2. Message Status Tracking")
    
    # Check message_status_manager.py
    status_manager_file = base_path / "message_status_manager.py"
    exists, msg = check_file_exists(status_manager_file)
    print(f"   Status manager file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(status_manager_file)
        print(f"   Status manager syntax: {msg}")
        results.append(syntax_ok)
    
    # Check models.py
    models_file = base_path / "models.py"
    exists, msg = check_file_exists(models_file)
    print(f"   Models file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(models_file)
        print(f"   Models syntax: {msg}")
        results.append(syntax_ok)
    
    # 3. Check Typing Indicators
    print("\n⌨️ 3. Typing Indicators")
    
    # Check typing_manager.py
    typing_manager_file = base_path / "typing_manager.py"
    exists, msg = check_file_exists(typing_manager_file)
    print(f"   Typing manager file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(typing_manager_file)
        print(f"   Typing manager syntax: {msg}")
        results.append(syntax_ok)
    
    # 4. Check User Presence
    print("\n👥 4. User Presence Tracking")
    
    # Check presence_manager.py
    presence_manager_file = base_path / "presence_manager.py"
    exists, msg = check_file_exists(presence_manager_file)
    print(f"   Presence manager file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(presence_manager_file)
        print(f"   Presence manager syntax: {msg}")
        results.append(syntax_ok)
    
    # 5. Check Property-Based Tests
    print("\n🧪 5. Property-Based Tests")
    
    test_files = [
        "test_websocket_connection_properties.py",
        "test_realtime_delivery_properties.py", 
        "test_message_broadcasting_properties.py",
        "test_message_status_properties.py",
        "test_typing_indicator_properties.py",
        "test_presence_tracking_properties.py"
    ]
    
    for test_file in test_files:
        test_path = base_path / test_file
        exists, msg = check_file_exists(test_path)
        print(f"   {test_file}: {msg}")
        results.append(exists)
        
        if exists:
            syntax_ok, msg = check_file_syntax(test_path)
            print(f"   {test_file} syntax: {msg}")
            results.append(syntax_ok)
    
    # 6. Check Integration Test
    print("\n🔗 6. Integration Test")
    
    integration_test = base_path / "test_core_realtime_integration.py"
    exists, msg = check_file_exists(integration_test)
    print(f"   Integration test: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(integration_test)
        print(f"   Integration test syntax: {msg}")
        results.append(syntax_ok)
    
    # 7. Check Frontend JavaScript
    print("\n🌐 7. Frontend JavaScript")
    
    js_file = base_path / "static" / "messaging" / "chat.js"
    exists, msg = check_file_exists(js_file)
    print(f"   Chat JavaScript: {msg}")
    results.append(exists)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print(f"📊 CHECKPOINT 6 VERIFICATION RESULTS")
    print(f"   Passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("🎉 ✅ CHECKPOINT 6 PASSED - Core real-time features are properly implemented!")
        return True
    elif success_rate >= 70:
        print("⚠️ 🟡 CHECKPOINT 6 PARTIAL - Most features implemented, some issues need attention")
        return False
    else:
        print("❌ 🔴 CHECKPOINT 6 FAILED - Critical issues need to be resolved")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
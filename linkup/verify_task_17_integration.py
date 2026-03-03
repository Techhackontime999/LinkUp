#!/usr/bin/env python3
"""
Task 17 - Complete System Integration Verification Script
Verifies that all AI agent platform components are properly integrated.
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

def check_string_in_file(filepath, search_string):
    """Check if a string exists in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if search_string in content:
            return True, f"✅ Found '{search_string}'"
        return False, f"❌ '{search_string}' not found"
    except Exception as e:
        return False, f"❌ Error: {e}"

def main():
    """Run Task 17 complete system integration verification."""
    print("🧪 Task 17 - Complete System Integration Verification")
    print("=" * 70)
    
    base_path = Path("ai_agents")
    results = []
    
    # 1. Check Django Models
    print("\n📦 1. Django Models")
    
    models_file = base_path / "models.py"
    exists, msg = check_file_exists(models_file)
    print(f"   Models file: {msg}")
    results.append(exists)
    
    if exists:
        syntax_ok, msg = check_file_syntax(models_file)
        print(f"   Models syntax: {msg}")
        results.append(syntax_ok)
        
        # Check all re
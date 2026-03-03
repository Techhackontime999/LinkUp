#!/usr/bin/env python
"""
Test script to verify that ai_agents module can be imported without errors.
"""
import sys
import os

# Add the linkup directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'linkup'))

print("Testing imports...")

try:
    print("1. Importing ai_agents.services...")
    from ai_agents import services
    print("   ✓ services.py imported successfully")
    
    print("2. Importing ai_agents.routing...")
    from ai_agents import routing
    print("   ✓ routing.py imported successfully")
    
    print("3. Importing ai_agents.middleware...")
    from ai_agents import middleware
    print("   ✓ middleware.py imported successfully")
    
    print("\n✓ All imports successful! The syntax errors have been fixed.")
    sys.exit(0)
    
except SyntaxError as e:
    print(f"\n✗ Syntax Error: {e}")
    print(f"   File: {e.filename}")
    print(f"   Line: {e.lineno}")
    sys.exit(1)
    
except IndentationError as e:
    print(f"\n✗ Indentation Error: {e}")
    print(f"   File: {e.filename}")
    print(f"   Line: {e.lineno}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ Import Error: {e}")
    sys.exit(1)

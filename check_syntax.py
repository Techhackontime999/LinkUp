#!/usr/bin/env python
"""Quick syntax check for interaction_logger_extensions.py"""
import py_compile
import sys

try:
    py_compile.compile('linkup/ai_agents/interaction_logger_extensions.py', doraise=True)
    print("✓ interaction_logger_extensions.py - No syntax errors")
    
    # Also check if we can import it
    sys.path.insert(0, 'linkup')
    import ai_agents.interaction_logger_extensions
    print("✓ interaction_logger_extensions.py - Import successful")
    
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f"✗ Syntax error in interaction_logger_extensions.py:")
    print(e)
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

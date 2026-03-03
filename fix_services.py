#!/usr/bin/env python3
"""
Script to fix the corrupted services.py file by removing duplicate code after line 2850.
"""

# Read the file
with open('linkup/ai_agents/services.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Original file has {len(lines)} lines")

# Keep only the first 2850 lines (everything before the corruption)
clean_lines = lines[:2850]

print(f"Keeping first {len(clean_lines)} lines")

# Write the clean version back
with open('linkup/ai_agents/services.py', 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print("File fixed successfully!")
print(f"Removed {len(lines) - len(clean_lines)} corrupted lines")

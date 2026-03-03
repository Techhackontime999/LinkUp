#!/bin/bash
# Quick test script to verify Django can import all modules

cd ~/LinkUp/linkup

echo "Testing Django check..."
python manage.py check --deploy 2>&1 | head -20

echo ""
echo "If you see 'System check identified no issues', the fixes worked!"

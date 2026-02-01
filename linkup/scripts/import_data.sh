#!/bin/bash
# Import data into PostgreSQL database

echo "Importing data into PostgreSQL database..."

# Check if data dump file is provided
if [ -z "$1" ]; then
    echo "Usage: ./import_data.sh <path_to_datadump.json>"
    exit 1
fi

DUMP_FILE=$1

if [ ! -f "$DUMP_FILE" ]; then
    echo "Error: File $DUMP_FILE not found"
    exit 1
fi

# Ensure we're using production settings
export DJANGO_ENVIRONMENT=production

# Run migrations first
echo "Running migrations..."
python manage.py migrate

# Load data
echo "Loading data from $DUMP_FILE..."
python manage.py loaddata "$DUMP_FILE"

echo "Data import completed!"
echo "Run verification script to check data integrity: python scripts/verify_migration.py"

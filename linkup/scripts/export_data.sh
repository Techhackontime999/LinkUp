#!/bin/bash
# Export data from SQLite database

echo "Exporting data from SQLite database..."

# Create backup directory if it doesn't exist
mkdir -p backups

# Backup the SQLite database
cp db.sqlite3 backups/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Export data using dumpdata
python manage.py dumpdata \
  --natural-foreign \
  --natural-primary \
  -e contenttypes \
  -e auth.Permission \
  -e sessions.session \
  > backups/datadump_$(date +%Y%m%d_%H%M%S).json

echo "Data exported successfully to backups/"
echo "Latest dump: backups/datadump_$(date +%Y%m%d_%H%M%S).json"

#!/bin/sh
set -e

export DJANGO_ENVIRONMENT=production
export DJANGO_SETTINGS_MODULE=professional_network.settings

python manage.py migrate --noinput

exec daphne -b 0.0.0.0 -p 8000 professional_network.asgi:application

#!/bin/sh
set -e

python manage.py migrate --noinput

# Create superuser from environment variables (Render free tier workaround)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" 2>/dev/null || true
fi

exec daphne -b 0.0.0.0 -p 8000 professional_network.asgi:application

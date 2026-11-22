#!/bin/sh
set -e

echo "[*] Applying database migrations..."
python manage.py migrate --noinput

echo "[*] Ensuring database seed data..."
python seed_data.py || true

echo "[*] Starting Gunicorn on port ${PORT:-8080}..."
exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 smart_library.wsgi:application

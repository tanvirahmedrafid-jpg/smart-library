#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Enter django project directory
cd public

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Seed database with initial data (users, books, settings)
python seed_data.py || true

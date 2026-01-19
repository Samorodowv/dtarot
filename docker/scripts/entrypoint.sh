#!/bin/bash
# Django application entrypoint script

set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo "Database is up - continuing"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  echo "Redis is unavailable - sleeping"
  sleep 1
done
echo "Redis is up - continuing"

# Navigate to Django project directory
cd /app/tarot_project

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Load initial data if needed
echo "Loading tarot cards if needed..."
python manage.py load_cards || echo "Cards already loaded or command failed"

# Create superuser if needed (only in development)
if [ "$DEBUG" = "True" ]; then
    echo "Creating superuser for development..."
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create logs directory
mkdir -p /app/logs

# Set up monitoring
echo "Setting up monitoring..."
python -c "
from tarot_readings.monitoring import setup_monitoring
setup_monitoring()
print('Monitoring setup completed')
" || echo "Monitoring setup failed"

# Execute the main command
echo "Starting application..."
exec "$@"
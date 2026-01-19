# Multi-stage build for Django Tarot application
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=tarot_project.settings

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        git \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy and set up scripts
COPY docker/scripts/entrypoint.sh /entrypoint.sh
COPY docker/scripts/wait-for-it.sh /wait-for-it.sh
RUN chmod +x /entrypoint.sh /wait-for-it.sh

# Create necessary directories
RUN mkdir -p logs staticfiles media \
    && chown -R app:app /app

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Production stage
FROM base as production

# Switch to app user
USER app

# Collect static files
RUN python tarot_project/manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/tarot/api/health/ || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "tarot_project/manage.py", "runserver", "0.0.0.0:8000"]

# Development stage  
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-django pytest-mock pytest-celery freezegun

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Default command for development
CMD ["python", "tarot_project/manage.py", "runserver", "0.0.0.0:8000"]

# Celery worker stage
FROM base as celery-worker

# Switch to app user
USER app

# Health check for Celery worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD celery -A tarot_project inspect ping || exit 1

# Command for Celery worker
CMD ["celery", "-A", "tarot_project", "worker", "--loglevel=info", "--concurrency=2"]

# Celery beat stage
FROM base as celery-beat

# Switch to app user
USER app

# Command for Celery beat
CMD ["celery", "-A", "tarot_project", "beat", "--loglevel=info"]
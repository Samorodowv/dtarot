# Docker Deployment Guide

This guide explains how to run the Django Tarot project using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB of available RAM
- At least 5GB of available disk space

## Quick Start

1. **Clone and setup environment:**
```bash
cd dtarot
cp .env.docker .env
# Edit .env with your actual credentials
```

2. **Start development environment:**
```bash
make dev-setup
```

3. **Access the application:**
- Web: http://localhost:8000/tarot/
- Admin: http://localhost:8000/tarot/admin/ (admin/admin123)
- Flower: http://localhost:5555/

## Environment Configuration

### Required Environment Variables

Copy `.env.docker` to `.env` and configure:

```env
# Database
POSTGRES_PASSWORD=your_secure_database_password
DATABASE_URL=postgresql://tarot_user:your_secure_database_password@db:5432/tarot_db

# Redis
REDIS_PASSWORD=your_secure_redis_password
REDIS_URL=redis://:your_secure_redis_password@redis:6379/0

# Django
SECRET_KEY=your-very-long-and-random-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# API Credentials
GIGACHAT_API_CREDENTIALS=your-gigachat-credentials

# Monitoring (Optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
```

## Services Architecture

The Docker setup includes the following services:

### Core Services
- **web**: Django application (port 8000)
- **db**: PostgreSQL 15 database (port 5432)
- **redis**: Redis cache and session store (port 6379)
- **celery_worker**: Background task processing
- **celery_beat**: Scheduled task management

### Optional Services
- **nginx**: Reverse proxy and load balancer (port 80/443)
- **flower**: Celery monitoring (port 5555, development only)

## Deployment Modes

### Development Mode

```bash
# Start all services in development mode
make up

# Or manually:
docker-compose up -d
```

Features:
- Code hot-reloading
- Debug mode enabled
- Flower monitoring available
- SQLite fallback if PostgreSQL fails

### Production Mode

```bash
# Start all services in production mode
make up-prod

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Features:
- Nginx reverse proxy
- Resource limits
- Security headers
- Optimized static file serving
- Error tracking with Sentry

## Management Commands

### Using Makefile (Recommended)

```bash
# View all available commands
make help

# Service management
make up              # Start development environment
make up-prod         # Start production environment
make down            # Stop all services
make logs            # View logs from all services
make status          # Show service status

# Django management
make migrate         # Run database migrations
make collectstatic   # Collect static files
make loaddata        # Load tarot cards data
make superuser       # Create Django superuser

# Development tools
make shell           # Open shell in web container
make shell-db        # Open PostgreSQL shell
make shell-redis     # Open Redis shell
make test            # Run tests
make monitor         # Open Flower monitoring

# Maintenance
make backup          # Backup database
make clean           # Remove all containers and images
make health          # Check service health
```

### Using Docker Compose Directly

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Execute commands in containers
docker-compose exec web python tarot_project/manage.py migrate
docker-compose exec web python tarot_project/manage.py createsuperuser
docker-compose exec web pytest

# Access shells
docker-compose exec web bash
docker-compose exec db psql -U tarot_user -d tarot_db
docker-compose exec redis redis-cli
```

## Volumes and Data Persistence

### Persistent Data
- **postgres_data**: Database files
- **redis_data**: Redis persistence files
- **static_volume**: Collected static files
- **media_volume**: User-uploaded files

### Development Mounts
- `./tarot_project`: Django source code (hot-reload)
- `./tarot_cards`: Tarot card images
- `./logs`: Application logs

## Health Checks and Monitoring

### Built-in Health Checks

All services include health checks:

```bash
# Check overall application health
curl http://localhost:8000/tarot/api/health/

# Check service status
docker-compose ps
```

### Monitoring Endpoints

```bash
# Application metrics
curl http://localhost:8000/tarot/api/metrics/

# Nginx status (production only)
curl http://localhost:8080/nginx_status

# Flower monitoring (development only)
open http://localhost:5555/
```

## Troubleshooting

### Common Issues

1. **Database connection failed**
```bash
# Check database logs
docker-compose logs db

# Restart database service
docker-compose restart db
```

2. **Redis connection failed**
```bash
# Check Redis logs
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

3. **Static files not loading**
```bash
# Collect static files
make collectstatic

# Check Nginx configuration
docker-compose logs nginx
```

4. **Celery tasks not processing**
```bash
# Check worker logs
docker-compose logs celery_worker

# Monitor tasks in Flower
make monitor
```

### Performance Issues

1. **Slow database queries**
```bash
# Check database performance
docker-compose exec db psql -U tarot_user -d tarot_db -c "SELECT * FROM pg_stat_activity;"
```

2. **High memory usage**
```bash
# Check container resource usage
docker stats

# View service resource limits
docker-compose config
```

### Log Analysis

```bash
# View real-time logs
make logs

# View specific service logs
docker-compose logs -f web
docker-compose logs -f celery_worker

# Export logs for analysis
docker-compose logs web > web.log
```

## Security Considerations

### Production Security

1. **Use strong passwords** for all services
2. **Configure SSL/TLS** with proper certificates
3. **Set up firewall rules** to restrict access
4. **Enable security headers** in Nginx
5. **Regularly update** Docker images
6. **Monitor logs** for suspicious activity

### Environment Variables

Never commit secrets to version control:
- Use `.env` files (added to `.gitignore`)
- Use Docker secrets in production
- Rotate credentials regularly

## Backup and Recovery

### Database Backup

```bash
# Create backup
make backup

# Restore from backup
make restore BACKUP_FILE=backup_20241201_120000.sql
```

### Full System Backup

```bash
# Backup volumes
docker run --rm -v dtarot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v dtarot_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz -C /data .
```

## Scaling and Performance

### Horizontal Scaling

```bash
# Scale Celery workers
docker-compose up -d --scale celery_worker=3

# Scale web instances (with load balancer)
docker-compose up -d --scale web=2
```

### Resource Optimization

Edit `docker-compose.prod.yml` to adjust resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
```

## Updating the Application

1. **Pull latest code:**
```bash
git pull origin main
```

2. **Rebuild images:**
```bash
make build
```

3. **Update services:**
```bash
make down
make up-prod
make migrate
```

4. **Verify deployment:**
```bash
make health
make status
```
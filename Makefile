# Makefile for Docker Compose management

.PHONY: help build up down logs shell test clean migrate collectstatic loaddata backup restore

# Default target
help:
	@echo "Available commands:"
	@echo "  build           Build all Docker images"
	@echo "  up              Start all services in development mode"
	@echo "  up-prod         Start all services in production mode"
	@echo "  down            Stop all services"
	@echo "  logs            View logs from all services"
	@echo "  logs-web        View logs from web service only"
	@echo "  shell           Open shell in web container"
	@echo "  shell-db        Open PostgreSQL shell"
	@echo "  shell-redis     Open Redis shell"
	@echo "  test            Run tests in web container"
	@echo "  migrate         Run Django migrations"
	@echo "  collectstatic   Collect static files"
	@echo "  loaddata        Load initial tarot cards data"
	@echo "  superuser       Create Django superuser"
	@echo "  backup          Backup database"
	@echo "  restore         Restore database from backup"
	@echo "  clean           Remove all containers, volumes, and images"
	@echo "  monitor         Open Flower monitoring (development only)"

# Build images
build:
	docker-compose build

# Development mode
up:
	docker-compose up -d
	@echo "Services started in development mode"
	@echo "Web: http://localhost:8000/tarot/"
	@echo "Flower: http://localhost:5555/"
	@echo "View logs: make logs"

# Production mode
up-prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "Services started in production mode"
	@echo "Web: http://localhost/"
	@echo "View logs: make logs"

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f web

# Shell access
shell:
	docker-compose exec web bash

shell-db:
	docker-compose exec db psql -U tarot_user -d tarot_db

shell-redis:
	docker-compose exec redis redis-cli

# Django management
migrate:
	docker-compose exec web python tarot_project/manage.py migrate

collectstatic:
	docker-compose exec web python tarot_project/manage.py collectstatic --noinput

loaddata:
	docker-compose exec web python tarot_project/manage.py load_cards

superuser:
	docker-compose exec web python tarot_project/manage.py createsuperuser

# Testing
test:
	docker-compose exec web pytest

test-coverage:
	docker-compose exec web pytest --cov=tarot_readings --cov-report=html

# Database operations
backup:
	docker-compose exec db pg_dump -U tarot_user tarot_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

restore:
	@echo "Usage: make restore BACKUP_FILE=backup_file.sql"
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Please specify BACKUP_FILE"; exit 1; fi
	docker-compose exec -T db psql -U tarot_user tarot_db < $(BACKUP_FILE)

# Monitoring
monitor:
	@echo "Opening Flower monitoring..."
	@echo "URL: http://localhost:5555/"
	@which open >/dev/null && open http://localhost:5555/ || echo "Please open http://localhost:5555/ in your browser"

# Health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/tarot/api/health/ | python -m json.tool || echo "Health check failed"

# Clean up
clean:
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -f

# Reset everything (dangerous!)
reset: clean
	docker volume prune -f
	@echo "All Docker resources cleaned up!"

# Quick development setup
dev-setup: build up migrate loaddata
	@echo "Development environment set up!"
	@echo "Creating superuser..."
	@echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | docker-compose exec -T web python tarot_project/manage.py shell
	@echo "Admin: admin/admin123"

# Production deployment
prod-deploy: build up-prod migrate collectstatic loaddata
	@echo "Production environment deployed!"

# Show status
status:
	docker-compose ps
	@echo ""
	@echo "Service URLs:"
	@echo "  Web Application: http://localhost:8000/tarot/"
	@echo "  Health Check: http://localhost:8000/tarot/api/health/"
	@echo "  Metrics: http://localhost:8000/tarot/api/metrics/"
	@echo "  Flower (dev): http://localhost:5555/"
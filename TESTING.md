# Testing Guide

This document describes how to run tests and monitoring for the Django Tarot project.

## Running Tests

### Prerequisites

1. Ensure you have the test environment set up:
```bash
cd tarot_project
source ../.venv/bin/activate  # Activate virtual environment
```

2. Install test dependencies (already included in requirements.txt):
```bash
pip install pytest pytest-django pytest-mock pytest-celery freezegun
```

### Test Configuration

Tests use pytest with Django integration. Configuration is in:
- `pytest.ini` - Main pytest configuration
- `tests/conftest.py` - Test fixtures and setup

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api           # API tests only
pytest -m celery        # Celery task tests only

# Run tests in specific files
pytest tests/unit/test_models.py
pytest tests/integration/test_views.py

# Run with coverage report
pytest --cov=tarot_readings --cov-report=html

# Run tests matching a pattern
pytest -k "test_reading"
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
  - Models: `/tests/unit/test_models.py`
  - Services: `/tests/unit/test_services.py`
  - Tasks: `/tests/unit/test_tasks.py`

- **Integration Tests**: Test component interactions
  - Views: `/tests/integration/test_views.py`

- **API Tests**: Test API endpoints
  - Status API: `/tests/api/test_status_api.py`

### Test Environment

Tests use:
- SQLite in-memory database for speed
- Mock objects for external services (GigaChat API)
- Celery eager mode for synchronous task execution
- Redis mock for cache testing

## Monitoring

### Health Check Endpoint

Check application health:
```bash
curl http://localhost:8000/tarot/api/health/
```

Response includes:
- Overall status (healthy/degraded/unhealthy)
- Database connectivity
- Cache functionality
- Celery task system
- GigaChat API configuration

### Metrics Endpoint

Get application metrics:
```bash
curl http://localhost:8000/tarot/api/metrics/
```

Provides:
- Daily reading count
- Average interpretation time
- Error counts by type
- Performance statistics

### Monitoring Configuration

Monitoring is controlled by environment variables:
```env
MONITORING_ENABLED=true
SLOW_REQUEST_THRESHOLD=5.0    # Log requests slower than 5 seconds
SLOW_QUERY_THRESHOLD=1.0      # Log queries slower than 1 second
```

### Sentry Integration

Error tracking with Sentry:
```env
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
ENVIRONMENT=production
APP_VERSION=1.0.0
```

### Log Files

Application logs are written to:
- Console output (development)
- `logs/tarot.log` (production)

Log levels:
- INFO: Normal operations
- WARNING: Slow requests/queries
- ERROR: Application errors
- DEBUG: Detailed debugging (development only)

## Performance Monitoring

### Middleware

`PerformanceMonitoringMiddleware` automatically tracks:
- Request duration
- Database query count
- Slow requests (>5 seconds)
- Slow queries (>1 second)

### Custom Tracking

Use `MonitoringUtils` for custom metrics:
```python
from tarot_readings.monitoring import MonitoringUtils

# Track events
MonitoringUtils.track_reading_creation()
MonitoringUtils.track_interpretation_time(reading_id, duration)
MonitoringUtils.track_error("api_error", "GigaChat timeout")

# Get statistics
stats = MonitoringUtils.get_daily_stats()
health = MonitoringUtils.health_check()
```

## Troubleshooting

### Common Test Issues

1. **Database permissions**: Ensure test database can be created
2. **Redis connection**: Check Redis is running for cache tests
3. **Missing fixtures**: Run `python manage.py load_cards` if card tests fail

### Monitoring Issues

1. **Health check fails**: Check database and Redis connectivity
2. **Missing metrics**: Verify monitoring is enabled in settings
3. **Sentry not working**: Check DSN configuration and network access

### Performance Issues

1. **Slow tests**: Use `pytest -x` to stop on first failure
2. **Memory usage**: Monitor test database size with large datasets
3. **Redis cleanup**: Tests should clean up cache keys automatically
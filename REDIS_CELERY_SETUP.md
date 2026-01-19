# Redis and Celery Setup Guide

## 1. Install Redis

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server
```

### Start Redis:
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Test Redis:
```bash
redis-cli ping
# Should return: PONG
```

## 2. Configure Redis (Optional - Production)

Edit `/etc/redis/redis.conf`:
```
# Security
bind 127.0.0.1
requirepass your_redis_password_here

# Performance
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
```

## 3. Environment Variables

Update `.env` file:
```env
# Redis
REDIS_URL=redis://localhost:6379/0
# With password: REDIS_URL=redis://:password@localhost:6379/0
```

## 4. Start Celery Worker

In project directory:
```bash
# Start worker
celery -A tarot_project worker --loglevel=info

# Start beat scheduler (for periodic tasks)
celery -A tarot_project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Start flower (optional - for monitoring)
celery -A tarot_project flower
```

## 5. Production Setup

### Systemd Service for Celery Worker

Create `/etc/systemd/system/celery-tarot.service`:
```ini
[Unit]
Description=Celery Worker for Tarot App
After=network.target redis.service

[Service]
Type=forking
User=nikolay
Group=nikolay
EnvironmentFile=/home/nikolay/projects/dtarot/.env
WorkingDirectory=/home/nikolay/projects/dtarot/tarot_project
ExecStart=/home/nikolay/projects/dtarot/.venv/bin/celery -A tarot_project worker --loglevel=info --pidfile=/var/run/celery-tarot.pid --detach
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Systemd Service for Celery Beat

Create `/etc/systemd/system/celerybeat-tarot.service`:
```ini
[Unit]
Description=Celery Beat for Tarot App
After=network.target redis.service

[Service]
Type=simple
User=nikolay
Group=nikolay
EnvironmentFile=/home/nikolay/projects/dtarot/.env
WorkingDirectory=/home/nikolay/projects/dtarot/tarot_project
ExecStart=/home/nikolay/projects/dtarot/.venv/bin/celery -A tarot_project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-tarot celerybeat-tarot
sudo systemctl start celery-tarot celerybeat-tarot
```

## 6. Test Async Processing

```python
# In Django shell
python manage.py shell

from tarot_readings.tasks import interpret_reading
result = interpret_reading.delay(1)  # reading_id = 1
print(result.status)
```

## 7. Monitoring

### Check Redis:
```bash
redis-cli info
redis-cli monitor
```

### Check Celery:
```bash
sudo systemctl status celery-tarot
sudo journalctl -u celery-tarot -f
```

### Flower Web Interface:
```bash
# Install flower
pip install flower

# Start flower
celery -A tarot_project flower

# Access at http://localhost:5555
```

## Key Benefits

1. **Performance**: Non-blocking interpretation generation
2. **Reliability**: Redis-based session storage and rate limiting
3. **Scalability**: Separate worker processes for heavy tasks
4. **Monitoring**: Task status tracking and retry mechanisms
5. **Caching**: Efficient card data caching
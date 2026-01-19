# Django Tarot Reading Application

A Django-based tarot reading website with AI-powered interpretations using the GigaChat API. Deployed at catsupremacy.ru/tarot.

## 🚀 Quick Start

### Development Setup

1. **Create and activate virtual environment:**
```bash
uv venv
source .venv/bin/activate  # On Linux/Mac
```

2. **Install dependencies:**
```bash
uv pip install -r tarot_project/requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your actual values, especially:
# - SECRET_KEY (generate new one)
# - GIGACHAT_API_CREDENTIALS
```

4. **Run migrations:**
```bash
cd tarot_project
python manage.py migrate
```

5. **Load tarot cards data:**
```bash
python manage.py load_cards
python manage.py update_english_names
```

6. **Collect static files:**
```bash
python manage.py collectstatic
```

7. **Run development server:**
```bash
python manage.py runserver
```

## 🔧 Production Deployment

### Apply Code Changes

1. **Restart Gunicorn Service**
   ```bash
   sudo systemctl restart gunicorn_tarot
   ```

2. **Check Service Status**
   ```bash
   sudo systemctl status gunicorn_tarot
   ```

3. **View Logs for Errors**
   ```bash
   sudo journalctl -u gunicorn_tarot -n 50 --no-pager
   ```

4. **Restart Nginx** (only if nginx config changed)
   ```bash
   sudo systemctl restart nginx
   ```

### Static Files Update
```bash
cd tarot_project
python manage.py collectstatic --noinput
```

## 📁 Project Structure

- **Project Directory:** `/home/nikolay/projects/dtarot/tarot_project`
- **Gunicorn Socket:** `127.0.0.1:8001`
- **Nginx Configuration:** `/etc/nginx/sites-available/tarot`
- **Static Files:** `/tarot_project/staticfiles/`
- **Database:** SQLite3 (migrate to PostgreSQL for production)

## 🔑 Environment Variables

Key variables in `.env`:
- `SECRET_KEY`: Django secret key (generate new for production)
- `GIGACHAT_API_CREDENTIALS`: Your GigaChat API credentials
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Comma-separated list (e.g., localhost,127.0.0.1,catsupremacy.ru)
- `DATABASE_URL`: Database connection string

## 🛠 Common Issues

### 502 Bad Gateway
Check Gunicorn logs:
```bash
sudo journalctl -u gunicorn_tarot -n 100 --no-pager
```

### Static Files Not Updating
```bash
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn_tarot
```

### Permission Issues
```bash
sudo chown -R nikolay:nikolay /home/nikolay/projects/dtarot
```

### Check Nginx Logs
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/catsupremacy.ru.error.log
```

## 🔒 Security Notes

1. **Never commit `.env` file** - it contains sensitive credentials
2. Always use `DEBUG=False` in production
3. Generate new `SECRET_KEY` for production
4. Keep GigaChat API credentials secure
5. Use HTTPS in production (already configured via Nginx)

## 📋 Requirements

- Python 3.8+
- Django 5.1
- Gunicorn
- Nginx
- SQLite3 (dev) / PostgreSQL (production recommended)
- GigaChat API access
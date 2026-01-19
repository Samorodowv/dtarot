# PostgreSQL Setup Guide

## 1. Install PostgreSQL

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### Start PostgreSQL service:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## 2. Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE tarot_db;
CREATE USER tarot_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE tarot_db TO tarot_user;
ALTER USER tarot_user CREATEDB;
\q
```

## 3. Update Environment Variables

Add to `.env` file:
```env
# Database - PostgreSQL
DATABASE_URL=postgres://tarot_user:secure_password_here@localhost:5432/tarot_db

# Alternative format:
# DATABASE_NAME=tarot_db
# DATABASE_USER=tarot_user
# DATABASE_PASSWORD=secure_password_here
# DATABASE_HOST=localhost
# DATABASE_PORT=5432
```

## 4. Migration Steps

1. **Backup current SQLite data:**
```bash
python manage.py dumpdata > data_backup.json
```

2. **Update settings to use PostgreSQL:**
```bash
# Settings will automatically use DATABASE_URL from .env
```

3. **Run migrations:**
```bash
python manage.py migrate
```

4. **Load data:**
```bash
python manage.py loaddata data_backup.json
# OR load cards manually:
python manage.py load_cards
python manage.py update_english_names
```

## 5. Test Connection

```bash
python manage.py dbshell
# Should connect to PostgreSQL
```

## Production Considerations

- Use connection pooling (consider django-db-pool)
- Set up regular backups with pg_dump
- Configure PostgreSQL for production (postgresql.conf, pg_hba.conf)
- Consider read replicas for scaling
- Monitor connection limits and performance
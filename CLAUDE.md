# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based tarot reading website that provides AI-powered interpretations using the GigaChat API. The application is deployed at catsupremacy.ru/tarot and serves Russian-speaking users.

## Development Commands

### Basic Django Commands
```bash
cd tarot_project
python manage.py runserver              # Start development server
python manage.py makemigrations         # Create new migrations
python manage.py migrate                # Apply migrations
python manage.py collectstatic          # Collect static files
python manage.py createsuperuser        # Create admin user
```

### Custom Management Commands
```bash
python manage.py load_cards             # Load tarot cards into database
python manage.py update_english_names   # Update English names for cards
```

### Production Deployment
```bash
sudo systemctl restart gunicorn_tarot   # Restart Gunicorn service
sudo systemctl status gunicorn_tarot    # Check service status
sudo journalctl -u gunicorn_tarot -n 50 --no-pager  # View logs
```

### Testing Commands
```bash
pytest                                  # Run all tests
pytest -v                               # Run with verbose output
pytest -m unit                          # Run unit tests only
pytest --cov=tarot_readings             # Run with coverage
```

### Monitoring & Health Checks
```bash
curl /tarot/api/health/                  # Application health check
curl /tarot/api/metrics/                 # Application metrics
```

### Docker Commands
```bash
make dev-setup                          # Quick development setup
make up                                  # Start development environment
make up-prod                             # Start production environment
make down                                # Stop all services
make logs                                # View logs
make shell                               # Access web container shell
make test                                # Run tests in container
make migrate                             # Run database migrations
make health                              # Check service health
```

## Architecture & Key Components

### Django Application Structure
The project follows Django's standard architecture with a single main app `tarot_readings`:

1. **Models** (`tarot_readings/models.py`):
   - `Card`: Stores 78 tarot cards with Russian/English names, suits, meanings
   - `Reading`: User reading sessions with age, gender, question
   - `CardPosition`: Links cards to readings with position (0-4) and orientation

2. **Views** (`tarot_readings/views.py`):
   - `GetReadingView`: Main form handling, rate limiting, promo codes
   - `ReadingResultView`: Displays interpretation results
   - Uses class-based views with CreateView/DetailView patterns

3. **GigaChat Integration** (`tarot_readings/gigachat_interpreter.py`):
   - `TarotInterpreter` class handles AI interpretation
   - Hardcoded API credentials (security concern)
   - Constructs prompts with card positions and meanings
   - Returns Russian-language interpretations

### Key Business Logic

1. **Rate Limiting**:
   - One free reading per hour per session
   - Tracked via `last_reading_time` in Django sessions
   - Promo code "tarot25" bypasses cooldown

2. **Card Selection**:
   - Randomly selects 5 cards from 78 total
   - 50% chance for each card to be reversed
   - Positions: Current Situation (0), Obstacle (1), Past (2), Future (3), Possible Outcome (4)

3. **Static Files**:
   - Card images in `tarot_cards/` directory
   - Collected to `staticfiles/` for production
   - Served by Nginx at `/tarot/static/`

### Production Configuration

- **URL Structure**: Site mounted at `/tarot` subdirectory via `FORCE_SCRIPT_NAME`
- **Security**: DEBUG=False, CSRF protection enabled
- **Database**: SQLite3 (consider PostgreSQL for production)
- **Sessions**: Django session middleware for rate limiting

### Important Notes

1. **API Credentials**: GigaChat credentials are hardcoded in `gigachat_interpreter.py:11`
2. **Language**: Primary interface language is Russian
3. **Dependencies**: No requirements.txt file exists - use `pip freeze` to check installed packages
4. **Static Files**: Run `collectstatic` after modifying card images or CSS
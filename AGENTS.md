# Repository Guidelines

## Project Structure & Module Organization
- `tarot_project/` is the Django workspace: `manage.py`, project settings in `tarot_project/`, and the main app in `tarot_readings/`.
- `tarot_project/tests/` contains pytest suites; `tarot_project/pytest.ini` defines markers and settings.
- Static assets live in `tarot_project/static/`; collected assets go to `tarot_project/staticfiles/`.
- Card imagery/data is in `tarot_cards/` (top level) and `tarot_project/tarot_cards/`.
- Docker configs are in `docker/` with `docker-compose*.yml` at the repo root.

## Build, Test, and Development Commands
- `uv venv && source .venv/bin/activate` to create/enter the local venv.
- `uv pip install -r tarot_project/requirements.txt` to install dependencies.
- `python tarot_project/manage.py migrate` and `python tarot_project/manage.py load_cards` to prep the database.
- `python tarot_project/manage.py runserver` to run locally.
- `make up`, `make test`, `make migrate` for container-based workflows (see `Makefile`).

## Coding Style & Naming Conventions
- Python: 4-space indentation, PEP 8 style, `snake_case` for functions/variables, `CamelCase` for classes.
- Django conventions apply: keep models in `tarot_readings/models.py`, views in `tarot_readings/views.py`, templates under app `templates/`.
- No formatter or linter is enforced; keep changes focused and consistent with nearby code.

## Testing Guidelines
- Framework: pytest with `pytest-django` (see `TESTING.md`).
- Run all tests with `pytest`; filter by markers like `pytest -m unit` or `pytest -m integration`.
- Test files follow `test_*.py` naming under `tarot_project/tests/`.

## Commit & Pull Request Guidelines
- This checkout does not include Git history; use concise, imperative commit messages (e.g., `Add metrics endpoint`).
- PRs should describe the change, list test commands run, and include screenshots for UI/template updates.

## Configuration & Security Notes
- Copy `.env.example` to `.env` and keep secrets local; never commit `.env`.
- Production settings and deployment details are documented in `README.md` and `DOCKER.md`.

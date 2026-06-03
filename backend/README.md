# MetricLens AI — Backend API

FastAPI service for time-series server-load forecasting and integer-programming
based resource-resizing recommendations. Layered architecture
(Controller → Service → Repository) with a pure, dependency-free `core`
(forecaster + optimizer).

## Live Link

> Updated automatically after deployment. `scripts/deploy.sh deploy` prints the
> Cloud Run URL once the rolling update completes.

- **Live API (Cloud Run)**: https://metriclens-backend-f2ei3uwvfq-uc.a.run.app
- Interactive docs: https://metriclens-backend-f2ei3uwvfq-uc.a.run.app/docs (Swagger UI)

## Tech stack

- **Framework**: FastAPI · **ASGI**: uvicorn
- **ORM**: SQLAlchemy 2.0 (async) · **Driver**: asyncpg · **DB**: PostgreSQL 15 (Cloud SQL)
- **Core**: standard-library forecaster (STL-style) + exact integer-programming resizer

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# Run (defaults to a local Postgres DSN; override via env):
METRICLENS_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/metriclens" \
  uvicorn app.main:app --reload --port 8080
```

## Quality gate

```bash
ruff check .      # lint + static analysis
pytest -q         # 27 unit + integration tests (no live DB required)
```

## API surface

See [../docs/03_api_specification.md](../docs/03_api_specification.md). Endpoints:
`/api/v1/hosts`, `/api/v1/hosts/{id}/metrics`, `/api/v1/hosts/{id}/forecast`,
`/api/v1/hosts/{id}/recommendation`, plus `/health` and `/health/db`.

## Container

Multi-stage `Dockerfile` (python:3.12-slim) producing a non-root (uid 10001)
image that honours Cloud Run's `$PORT`.

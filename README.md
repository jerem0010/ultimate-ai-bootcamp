

## Backend v0.1 — local setup

Requires Python 3.12+, uv, Docker Compose.

```bash
uv sync
cp -n .env.example .env
docker compose -f infrastructure/postgres/compose.yaml up -d --wait
# On a fresh installation only, create the separate test database:
docker exec ultimate-ai-postgres createdb -U ai_user ai_tasks_test
uv run --env-file .env python -m app.migrate
uv run --env-file .env python -m app.migrate --test
```

Run API and worker in separate terminals:

```bash
uv run --env-file .env uvicorn app.main:app --reload
uv run --env-file .env python -m app.worker
```

Run tests: `uv run --env-file .env python -m pytest -q`.

API docs: http://127.0.0.1:8000/docs. `/health` checks liveness; `/ready` checks PostgreSQL and Redis. POST `/tasks` creates a task; GET `/tasks/{task_id}` retrieves it; GET `/tasks` supports status filtering and cursor pagination.

FastAPI persists tasks in PostgreSQL; Redis delivers messages and caches responses. The worker reserves, atomically claims, executes, persists and acknowledges tasks. Recovery reconciles abandoned tasks and missing messages.

Limitations: simulated AI, one active worker per database/queue deployment, at-least-once delivery (external calls may repeat), no authentication or tenant isolation. Readiness does not check the worker or external providers. Tests use a separate PostgreSQL database; do not run them against production.

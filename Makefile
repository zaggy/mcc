.PHONY: dev lint format typecheck test install

install:
	uv sync --all-extras

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	uv run ruff check app/ tests/

format:
	uv run ruff format app/ tests/
	uv run ruff check --fix app/ tests/

typecheck:
	uv run mypy app/

test:
	uv run pytest tests/ -v --tb=short

test-cov:
	uv run pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

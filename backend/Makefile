# FinAdvisor Backend — Makefile
# Usage: make <target>
# Requires: Python 3.11+, PostgreSQL running, .env configured

.PHONY: install dev test migrate migrate-down lint clean

# ── Install dependencies ──────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

# ── Run dev server ────────────────────────────────────────────────────────────
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Run tests ─────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

# ── Run migrations (upgrade to head) ─────────────────────────────────────────
migrate:
	alembic upgrade head

# ── Rollback last migration ───────────────────────────────────────────────────
migrate-down:
	alembic downgrade -1

# ── Auto-generate a new migration from model changes ─────────────────────────
# Usage: make migration MSG="add financial profiles table"
migration:
	alembic revision --autogenerate -m "$(MSG)"

# ── Clean up __pycache__ ──────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true

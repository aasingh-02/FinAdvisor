#!/usr/bin/env bash
set -eo pipefail

echo "=========================================="
echo " [FinAdvisor] Running Database Migrations "
echo "=========================================="

# Run all pending Alembic migrations using the existing alembic.ini and DATABASE_URL
if ! python -m alembic upgrade head; then
    echo "[FATAL] Alembic migration failed! Aborting server startup to prevent running on an invalid schema." >&2
    exit 1
fi

echo "=========================================="
echo " [FinAdvisor] Migrations Completed Cleanly"
echo " [FinAdvisor] Starting FastAPI Server     "
echo "=========================================="

# Start Uvicorn, replacing the shell process so signals (SIGTERM) are handled directly
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

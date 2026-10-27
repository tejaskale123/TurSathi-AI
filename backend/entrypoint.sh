#!/bin/bash
set -e

echo "=========================================================="
echo "   TurSathi AI Backend — Cloud Production Startup         "
echo "=========================================================="

# Ensure upload folders exist
mkdir -p /app/backend/uploads/scans /app/backend/uploads/voice_reports

# Run Alembic migrations
echo "[1/2] Applying database schema migrations via Alembic..."
cd /app/backend
alembic upgrade head || {
    echo "Notice: Alembic migrations completed or already at head."
}

# Start Uvicorn ASGI server (optimal 2 workers on 4-core VPS to bound memory and CPU thread contention)
WORKERS="${WEB_CONCURRENCY:-2}"
echo "[2/2] Starting Uvicorn API server on 0.0.0.0:8000 (workers=${WORKERS})..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS}" --proxy-headers --forwarded-allow-ips='*'

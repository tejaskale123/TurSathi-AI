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

# Start Uvicorn ASGI server
echo "[2/2] Starting Uvicorn API server on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'

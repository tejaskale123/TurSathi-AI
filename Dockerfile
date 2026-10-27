# ============================================================
# TurSathi AI Backend — Production Dockerfile
# Optimized for cloud deployment (Linux/AMD64/ARM64)
# ============================================================

FROM python:3.11-slim

# Set environment variables for Python runtime and PyTorch CPU thread bounds (4-core VPS)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    NUMEXPR_NUM_THREADS=2

# Install OS libraries for OpenCV headless, image decoders, and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install PyTorch CPU-only build first (shrinks image by ~3GB for fast cloud deployment)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu

# 2. Copy and install backend dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 3. Copy backend application source and database migration files
COPY backend/app /app/backend/app
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/alembic.ini

# 4. Copy active production ML model checkpoints and OOD profiles
COPY models/best_pigeonpea_disease_final_efficientnet_b0.pth /app/models/
COPY models/tur_image_validator_efficientnet_b0_v3.pth /app/models/
COPY models/ood_feature_profile.json /app/models/

# 5. Create persistent upload directories and secure non-root system user
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    mkdir -p /app/backend/uploads/scans /app/backend/uploads/voice_reports && \
    chown -R appuser:appuser /app

# 6. Set up container entrypoint
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

WORKDIR /app/backend

# Expose FastAPI service port
EXPOSE 8000

# Docker healthcheck pinging the FastAPI health route
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

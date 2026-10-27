#!/usr/bin/env bash
# ==============================================================================
# TurSathi AI — Universal VPS Deployment & One-Click Update Script
#
# Safety Guarantees:
# 1. Backs up secret .env files before any git operation.
# 2. Preserves persistent models/ and backend/uploads/ from git clean.
# 3. Pulls latest remote commits and rebuilds Docker containers.
# 4. Performs automated healthcheck verification on /health.
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

if [[ ! -d "$ROOT_DIR/.git" && -d "$SCRIPT_DIR/../.git" ]]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

cd "$ROOT_DIR"
echo -e "${BLUE}[INFO]${NC} Running TurSathi AI VPS update in: $ROOT_DIR"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
[[ "$CURRENT_BRANCH" == "HEAD" || -z "$CURRENT_BRANCH" ]] && CURRENT_BRANCH="main"

echo -e "${BLUE}[INFO]${NC} Target git branch: $CURRENT_BRANCH"

# 1. Back up secret .env files so git reset never deletes API keys or database passwords
TEMP_ROOT_ENV=""
TEMP_BACKEND_ENV=""

if [[ -f "$ROOT_DIR/.env" ]]; then
  TEMP_ROOT_ENV="$(mktemp)"
  cp "$ROOT_DIR/.env" "$TEMP_ROOT_ENV"
  echo -e "${BLUE}[INFO]${NC} Backed up root .env"
fi

if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  TEMP_BACKEND_ENV="$(mktemp)"
  cp "$ROOT_DIR/backend/.env" "$TEMP_BACKEND_ENV"
  echo -e "${BLUE}[INFO]${NC} Backed up backend/.env"
fi

# 2. Fetch and hard reset to remote branch
echo -e "${BLUE}[INFO]${NC} Fetching and syncing latest code from origin/$CURRENT_BRANCH..."
git fetch origin "$CURRENT_BRANCH"
git reset --hard "origin/$CURRENT_BRANCH"

# Safety: Exclude .env, uploads, and model checkpoints from clean
git clean -fd -e backend/.env -e .env -e "backend/uploads/*" -e "models/*"

# 3. Restore preserved .env files
if [[ -n "$TEMP_ROOT_ENV" && -f "$TEMP_ROOT_ENV" ]]; then
  cp "$TEMP_ROOT_ENV" "$ROOT_DIR/.env"
  rm -f "$TEMP_ROOT_ENV"
  echo -e "${GREEN}[OK]${NC} Restored root .env"
fi

if [[ -n "$TEMP_BACKEND_ENV" && -f "$TEMP_BACKEND_ENV" ]]; then
  cp "$TEMP_BACKEND_ENV" "$ROOT_DIR/backend/.env"
  rm -f "$TEMP_BACKEND_ENV"
  echo -e "${GREEN}[OK]${NC} Restored backend/.env"
fi

# 4. Rebuild and launch Docker containers
DOCKER_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
  else
    echo -e "${RED}[ERROR] Neither 'docker compose' nor 'docker-compose' found.${NC}"
    exit 1
  fi
fi

echo -e "${BLUE}[INFO]${NC} Rebuilding and restarting containers via $DOCKER_CMD..."
$DOCKER_CMD build --pull
$DOCKER_CMD up -d

# 5. Automated health check verification
PORT="${PORT:-8000}"
if [[ -f "$ROOT_DIR/.env" ]]; then
  ENV_PORT=$(grep -E '^PORT=' "$ROOT_DIR/.env" | cut -d '=' -f2 | tr -d ' "\r' || true)
  [[ -n "$ENV_PORT" ]] && PORT="$ENV_PORT"
fi

HEALTH_URL="http://localhost:${PORT}/health"
echo -e "${BLUE}[INFO]${NC} Probing health endpoint at $HEALTH_URL..."

IS_HEALTHY=0
for ((i=1; i<=20; i++)); do
  if curl -s -f "$HEALTH_URL" >/dev/null 2>&1; then
    IS_HEALTHY=1
    break
  fi
  sleep 2
done

if [[ "$IS_HEALTHY" -eq 1 ]]; then
  echo -e "${GREEN}[OK] Update successful! TurSathi AI backend is healthy and serving.${NC}"
  echo -e "${GREEN}[OK] Running commit: $(git log -1 --pretty=format:'%h - %s')${NC}"
else
  echo -e "${RED}[ERROR] Healthcheck failed after 40 seconds. Displaying last 35 container log lines:${NC}"
  $DOCKER_CMD logs --tail 35
  exit 1
fi

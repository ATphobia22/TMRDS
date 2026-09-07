#!/usr/bin/env bash
# TMRDS deploy — production path for research-advisory clinical stack
# Steward: Anthony John Tucker, Mount Vernon, Indiana 47620
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "[TMRDS] Preparing data directories..."
mkdir -p data/{vector_store,research,ehr_vault,dicom_storage,logs,migrations,audit}
mkdir -p engines frontend static

export TMRDS_ENV="${TMRDS_ENV:-development}"
export TMRDS_HOST="${TMRDS_HOST:-0.0.0.0}"
export TMRDS_PORT="${TMRDS_PORT:-8000}"
export TMRDS_AUDIT_LOG="${TMRDS_AUDIT_LOG:-data/audit/access.jsonl}"
export TMRDS_SESSION_TIMEOUT_MIN="${TMRDS_SESSION_TIMEOUT_MIN:-15}"

if [[ -f requirements.txt ]]; then
  echo "[TMRDS] Ensuring Python dependencies..."
  python3 -m pip install -q -r requirements.txt || true
fi

if command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1; then
  if [[ -f docker-compose.yml ]]; then
    echo "[TMRDS] Starting containers..."
    docker compose up -d --build || docker-compose up -d --build || true
  fi
fi

echo "[TMRDS] Starting API gateway on ${TMRDS_HOST}:${TMRDS_PORT}..."
exec python3 -m uvicorn api.main:app --host "$TMRDS_HOST" --port "$TMRDS_PORT" --proxy-headers

#!/usr/bin/env bash
# TMRDS deployment helper — builds an immutable image or starts an explicitly local API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "[TMRDS] Preparing runtime data directories..."
mkdir -p data/{vector_store,research,ehr_vault,dicom_storage,logs,migrations,audit}

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "[TMRDS] Building and starting the Compose stack..."
  docker compose up -d --build
  echo "[TMRDS] Compose services requested. Verify health with: docker compose ps"
  exit 0
fi

if [[ "${TMRDS_LOCAL_API:-false}" != "true" ]]; then
  echo "[TMRDS] Docker Compose is unavailable. Set TMRDS_LOCAL_API=true only for an intentional local run." >&2
  exit 2
fi

export TMRDS_ENV="${TMRDS_ENV:-development}"
export TMRDS_HOST="${TMRDS_HOST:-127.0.0.1}"
export TMRDS_PORT="${TMRDS_PORT:-8000}"
export TMRDS_AUDIT_LOG="${TMRDS_AUDIT_LOG:-data/audit/access.jsonl}"
export TMRDS_SESSION_TIMEOUT_MIN="${TMRDS_SESSION_TIMEOUT_MIN:-15}"

if ! python3 -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "[TMRDS] Runtime dependencies are missing. Install from requirements-runtime.txt in a managed virtual environment." >&2
  exit 2
fi

echo "[TMRDS] Starting local API gateway on ${TMRDS_HOST}:${TMRDS_PORT}..."
exec python3 -m uvicorn api.main:app --host "$TMRDS_HOST" --port "$TMRDS_PORT" --proxy-headers

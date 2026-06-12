#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required before starting the API." >&2
  exit 1
fi

exec uvicorn app.main:app --app-dir apps/api --host "${HOST}" --port "${PORT}"

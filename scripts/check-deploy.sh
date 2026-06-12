#!/usr/bin/env bash
set -euo pipefail

required_env=(
  DATABASE_URL
  SELF_URL
  S3_ACCESS_KEY_ID
  S3_SECRET_ACCESS_KEY
  S3_BUCKET
  S3_PREFIX
  S3_ENDPOINT
  MCTAI_AUTH_URL
  MCTAI_AUTH_APP_TOKEN
  MCTAI_AUTH_JWKS_URL
  ANTHROPIC_API_KEY
  CLAUDE_MODEL
)

missing=()
for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    missing+=("${name}")
  fi
done

if (( ${#missing[@]} > 0 )); then
  printf 'Missing required deployment environment variables:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi

if [[ "${DATABASE_URL}" != postgresql*://* ]]; then
  echo "DATABASE_URL must be a PostgreSQL connection string." >&2
  exit 1
fi

if [[ "${S3_PREFIX}" != */ ]]; then
  echo "S3_PREFIX must end with a trailing slash." >&2
  exit 1
fi

if ! command -v "${TEXLIVE_COMMAND:-pdflatex}" >/dev/null 2>&1; then
  echo "TeX Live command '${TEXLIVE_COMMAND:-pdflatex}' was not found on PATH." >&2
  echo "Install TeX Live before deploying compile support." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found on PATH." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found on PATH." >&2
  exit 1
fi

echo "Deployment preflight passed."

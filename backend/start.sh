#!/usr/bin/env sh
# Production entrypoint: migrate, make sure teams/coach exist, then serve.
set -e

echo "[start] applying database migrations"
alembic upgrade head

echo "[start] bootstrapping teams and coach account"
python -m app.bootstrap

echo "[start] launching API on port ${PORT:-8000}"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips '*'

#!/bin/sh
set -eu

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

"$PY" -m pip install -r requirements.txt
"$PY" manage.py migrate --noinput
if [ "${VERCEL_ENV:-}" = "production" ]; then
  "$PY" manage.py import_directory
  "$PY" manage.py ensure_superuser
fi
if [ -n "${R2_ACCOUNT_ID:-}" ] && [ -n "${R2_BUCKET_NAME:-}" ] && [ -n "${R2_ACCESS_KEY_ID:-}" ] && [ -n "${R2_SECRET_ACCESS_KEY:-}" ]; then
  "$PY" manage.py sync_uploads_to_r2
fi
npm ci
npm run build

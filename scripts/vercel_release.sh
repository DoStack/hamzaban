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
fi
npm ci
npm run build

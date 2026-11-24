#!/usr/bin/env sh
set -e

if [ -z "$OVERCUT_JWT_SECRET" ]; then
  OVERCUT_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  export OVERCUT_JWT_SECRET
  echo "OVERCUT_JWT_SECRET unset: generated an ephemeral secret (sessions reset on restart)." >&2
fi

exec uvicorn backend.api.main:app --host 0.0.0.0 --port 7860

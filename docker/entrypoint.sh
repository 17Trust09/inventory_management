#!/bin/sh
set -e

echo "⏳ Warte auf PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432})..."
python - <<'PY'
import os
import socket
import time

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
deadline = time.time() + 60

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("✅ PostgreSQL erreichbar.")
            break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit("❌ PostgreSQL nicht erreichbar.")
PY

echo "🧩 Migrationen anwenden..."
python manage.py migrate --noinput

if [ "${DJANGO_COLLECTSTATIC:-true}" = "true" ]; then
  echo "📦 Collectstatic..."
  python manage.py collectstatic --noinput
fi

exec "$@"

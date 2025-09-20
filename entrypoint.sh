#!/usr/bin/env bash
set -euo pipefail

# Warten bis Postgres bereit ist (bei sqlite o.ä. wird geskippt)
if [[ -n "${DATABASE_URL:-}" ]]; then
  python - <<'PY'
import os, sys, socket
from urllib.parse import urlparse

u = urlparse(os.environ.get("DATABASE_URL", ""))
scheme = (u.scheme or "").lower()
# psycopg URLs sind z.B. 'postgresql' oder 'postgresql+psycopg'
if not scheme.startswith("postgres"):
    # keine DB-Wartezeit nötig (z.B. sqlite)
    sys.exit(0)

host, port = u.hostname, u.port or 5432
for i in range(60):
    s = socket.socket()
    s.settimeout(1.5)
    try:
        s.connect((host, port))
        print("DB reachable")
        sys.exit(0)
    except Exception:
        pass
print("DB not reachable in time", file=sys.stderr)
sys.exit(1)
PY
fi

# Migrationen
python manage.py migrate --noinput

# Collectstatic nur optional (Standard: off, weil im Dockerfile erledigt)
if [[ "${RUN_COLLECTSTATIC:-0}" == "1" ]]; then
  python manage.py collectstatic --noinput
fi

# Start-Befehl von CMD
exec "$@"

#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Wait for PostgreSQL if DATABASE_URL points to Postgres.
# Skips waiting for SQLite or when DATABASE_URL is unset.
# ------------------------------------------------------------------------------
if [[ -n "${DATABASE_URL:-}" ]]; then
  python - <<'PY'
import os, sys, socket
from urllib.parse import urlparse

u = urlparse(os.environ.get("DATABASE_URL", ""))
scheme = (u.scheme or "").lower()
if not scheme.startswith(("postgres", "postgis")):
    sys.exit(0)

host, port = u.hostname or "localhost", u.port or 5432
for i in range(60):
    try:
        s = socket.create_connection((host, port), timeout=1.5)
        s.close()
        print("DB reachable")
        sys.exit(0)
    except Exception:
        pass
print("DB not reachable in time", file=sys.stderr)
sys.exit(1)
PY
fi

# ------------------------------------------------------------------------------
# Optional: compile .po -> .mo for i18n (requires gettext in the image).
# Enable by setting RUN_COMPILEMESSAGES=1 (disabled by default).
# ------------------------------------------------------------------------------
if [[ "${RUN_COMPILEMESSAGES:-0}" == "1" ]]; then
  # Compile all available locales under ./locale/
  # (ignore failures so a missing locale does not block startup)
  echo "Compiling translation messages..."
  find ./locale -name '*.po' >/dev/null 2>&1 && django-admin compilemessages || true
fi

# ------------------------------------------------------------------------------
# Apply database migrations
# ------------------------------------------------------------------------------
echo "Applying migrations..."
python manage.py migrate --noinput

# ------------------------------------------------------------------------------
# Static files handling with WhiteNoise (Manifest storage).
# - If RUN_COLLECTSTATIC=1: always collect (safe & idempotent).
# - Otherwise: auto-heal if the manifest file is missing.
#   This covers situations where a volume hides the baked-in staticfiles.
# ------------------------------------------------------------------------------
collect_needed=0
if [[ "${RUN_COLLECTSTATIC:-0}" == "1" ]]; then
  collect_needed=1
else
  # Probe if the manifest exists according to settings.STATIC_ROOT
  if ! python - <<'PY'
import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()
from django.conf import settings

root = getattr(settings, "STATIC_ROOT", None) or "/app/staticfiles"
manifest = os.path.join(root, "staticfiles.json")
sys.exit(0 if os.path.exists(manifest) else 1)
PY
  then
    echo "Staticfiles manifest missing -> will run collectstatic."
    collect_needed=1
  fi
fi

if [[ "$collect_needed" == "1" ]]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

# ------------------------------------------------------------------------------
# Hand over to CMD (e.g. gunicorn ...)
# ------------------------------------------------------------------------------
exec "$@"

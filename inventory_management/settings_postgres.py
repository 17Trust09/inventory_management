"""
Ersatz-/Overlay-Settings für PostgreSQL.
Starte Django mit:
  export DJANGO_SETTINGS_MODULE=inventory_management.settings_postgres
oder in .env:
  DJANGO_SETTINGS_MODULE=inventory_management.settings_postgres
"""

from .settings import *  # noqa

# Wichtig: psycopg2-binary installieren (siehe requirements-postgres.txt)
# und eine DB anlegen (siehe docker-compose.postgres.yml oder eigenes Setup).

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "inventorydb"),
        "USER": os.environ.get("POSTGRES_USER", "inventory"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "inventory"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
        "CONN_MAX_AGE": 60,  # persistente Verbindungen
        "OPTIONS": {
            # für bessere Performance, wenn SSL nicht nötig:
            # "sslmode": os.environ.get("POSTGRES_SSLMODE", "prefer"),
        },
    }
}

# Optional: Caches (in‑Memory). Für Production Redis nutzen.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "inventory-cache",
        "TIMEOUT": 60,
    }
}

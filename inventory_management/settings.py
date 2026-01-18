from pathlib import Path
import os
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Basis
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# .env laden
load_dotenv(BASE_DIR / ".env")

# Home Assistant (nur aus ENV; keine Hardcodes)
HA_API_TOKEN = os.getenv('HA_API_TOKEN', '')  # Long-Lived Token in .env
HA_URL = os.getenv('HA_URL', 'http://homeassistant.local:8123')

# QR-/Deeplink-Basis-URL (optional). Wenn leer, baut die App absolute URLs dynamisch
# aus der aktuellen Request (via ThreadLocalMiddleware). Für feste Hostnamen/Reverse-Proxy:
# INVENTORY_BASE_URL in .env setzen, z.B. http://raspi.tailnet-xyz.ts.net:8000
INVENTORY_BASE_URL = os.getenv('INVENTORY_BASE_URL', '')

# Optionale HA-Integrationstoggles
HA_VERIFY_SSL = os.getenv('HA_VERIFY_SSL', 'true').lower() == 'true'
HA_TIMEOUT = int(os.getenv('HA_TIMEOUT', '6'))

# Optionaler Key für kleine API-Routen (/api/feedback/summary, /api/health/ha)
FEEDBACK_API_KEY = os.getenv('FEEDBACK_API_KEY', '')

# ──────────────────────────────────────────────────────────────────────────────
# Django Core
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-default-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# Optional, wenn hinter Proxy/HTTPS:
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if os.getenv('USE_SECURE_PROXY', 'false').lower() == 'true' else None
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'false').lower() == 'true'

# ──────────────────────────────────────────────────────────────────────────────
# Apps
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'inventory.apps.InventoryConfig',
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# ──────────────────────────────────────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # NEU: macht aktuelle Request global (ThreadLocal) verfügbar → dynamische Deeplinks
    'inventory.middleware.ThreadLocalMiddleware',
]

ROOT_URLCONF = 'inventory_management.urls'

# ──────────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                # NEU: aktive Overviews global verfügbar (für Navbar/Sidebar)
                'inventory.context_processors.active_overviews',
            ],
        },
    },
]

WSGI_APPLICATION = 'inventory_management.wsgi.application'

# ──────────────────────────────────────────────────────────────────────────────
# Datenbank
#   Per ENV steuerbar:
#     DB_ENGINE=postgres|sqlite|mysql
# ──────────────────────────────────────────────────────────────────────────────
DB_ENGINE = os.getenv('DB_ENGINE', 'postgres').lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('MYSQL_DATABASE', 'inventorydb'),
            'USER': os.getenv('MYSQL_USER', 'inventory'),
            'PASSWORD': os.getenv('MYSQL_PASSWORD', 'inventory'),
            'HOST': os.getenv('MYSQL_HOST', '127.0.0.1'),
            'PORT': int(os.getenv('MYSQL_PORT', '3306')),
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }
else:
    # Default: PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'inventorydb'),
            'USER': os.getenv('POSTGRES_USER', 'inventory'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'inventory'),
            'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
            'PORT': int(os.getenv('POSTGRES_PORT', '5432')),
            'CONN_MAX_AGE': int(os.getenv('POSTGRES_CONN_MAX_AGE', '60')),
        }
    }

# ──────────────────────────────────────────────────────────────────────────────
# Auth & i18n
# ──────────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'de'

# ──────────────────────────────────────────────────────────────────────────────
# Versionierung (mit Patch Notes synchron halten)
# ──────────────────────────────────────────────────────────────────────────────
INVENTORY_VERSION = "1.0.4"
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# Static/Media
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
STATICFILES_DIRS = []

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ──────────────────────────────────────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login-Redirect: auf modulare Dashboards
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = os.getenv('LOGIN_REDIRECT_URL', 'dashboards')

# Proxy-Support (X-Forwarded-Host)
USE_X_FORWARDED_HOST = True

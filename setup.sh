#!/usr/bin/env bash
# inventory_management – Automatisches Setup-Skript
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="${SUDO_USER:-$USER}"
APP_PORT="${PORT:-18000}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERR]${NC}   $1"; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    err "Bitte mit sudo ausfuehren: sudo bash setup.sh"
fi

# ── 1. System-Pakete ──────────────────────────────────────────────────────────
info "Installiere System-Pakete..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv postgresql postgresql-client libpq-dev git curl wget 2>/dev/null || true
ok "System-Pakete installiert"

# ── 2. PostgreSQL ─────────────────────────────────────────────────────────────
info "Richte PostgreSQL ein..."
DB_PASSWORD=*** openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)
DB_NAME="${DB_NAME:-inventorydb}"
DB_USER="${DB_USER:-inventory}"

systemctl enable postgresql 2>/dev/null || true
systemctl start postgresql 2>/dev/null || true

su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\" | grep -q 1" 2>/dev/null || \
    su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';\""

su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\" | grep -q 1" 2>/dev/null || \
    su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};\""

su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\"" 2>/dev/null || true
ok "DB=${DB_NAME} User=${DB_USER}"

# ── 3. Python-Venv ────────────────────────────────────────────────────────────
info "Richte Python-Umgebung ein..."
cd "${APP_DIR}"
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install --upgrade pip -q

if [ -f requirements.txt ]; then
    pip install -r requirements.txt -q || true
fi
# Fallback: minimale Dependencies
pip install django djangorestframework django-crispy-forms crispy-bootstrap5 \
    psycopg2-binary python-decouple pillow qrcode python-barcode -q 2>/dev/null || true
ok "Python-Dependencies installiert"

# ── 4. .env ───────────────────────────────────────────────────────────────────
info "Erstelle .env..."
if [ ! -f .env ]; then
    SECRET_KEY=*** openssl rand -base64 32)
    FEEDBACK_KEY=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 20)

    cat > .env <<ENVEOF
DJANGO_SECRET_KEY=${SECK...ENVEOF
    chown "${APP_USER}:${APP_USER}" .env 2>/dev/null || true
    echo "  API-Key: ${FEEDBACK_KEY}"
else
    warn ".env existiert bereits"
fi

# ── 5. Migrationen + Superuser ────────────────────────────────────────────────
info "Migrationen..."
source "${APP_DIR}/venv/bin/activate"
cd "${APP_DIR}"
python manage.py migrate --noinput
ok "Migrationen abgeschlossen"

info "Superuser anlegen..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin')
    print('Superuser admin/admin erstellt')
else:
    print('Superuser existiert bereits')
" 2>&1 | tail -1

python manage.py collectstatic --noinput 2>/dev/null || true
ok "Admin eingerichtet"

# ── 6. Systemd-Service ────────────────────────────────────────────────────────
info "Richte systemd-Service ein..."
SERVICE_NAME="inventory_app"

cat > /etc/systemd/system/${SERVICE_NAME}.service <<SRVEOF
[Unit]
Description=Inventory Management Django App
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PATH=${APP_DIR}/venv/bin:/usr/bin
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/manage.py runserver 0.0.0.0:${APP_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SRVEOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME} --quiet
systemctl restart ${SERVICE_NAME}
sleep 3

if systemctl is-active --quiet ${SERVICE_NAME}; then
    ok "Service ${SERVICE_NAME} laeuft auf Port ${APP_PORT}"
else
    err "Service gestartet nicht: journalctl -u ${SERVICE_NAME} -n 20"
fi

# ── 7. Test ───────────────────────────────────────────────────────────────────
IP=$(hostname -I | awk '{print $1}')
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${APP_PORT}/ 2>/dev/null || echo "000")

echo ""
echo "==========================================="
echo "  Setup abgeschlossen!"
echo "==========================================="
echo ""
echo "  Web-App:        http://${IP}:${APP_PORT}"
echo "  Admin-Login:    admin / admin"
echo ""
echo "  Naechste Schritte:"
echo "    1. Admin-Passwort aendern: http://${IP}:${APP_PORT}/admin/"
echo "    2. INVENTORY_BASE_URL in .env anpassen"
echo "    3. DJANGO_DEBUG=false setzen"
echo "    4. API-Key aus .env in ESP config.h eintragen"
echo ""

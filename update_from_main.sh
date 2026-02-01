#!/bin/bash
set -euo pipefail

LOG_DIR="backup"
LOG_FILE="${LOG_DIR}/update_$(date +%Y-%m-%d_%H-%M-%S).log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

function run_step {
  local label=$1
  shift
  echo -e "\n🔹 ${label}"
  "$@"
}

function maybe_sudo {
  if command -v sudo &> /dev/null; then
    sudo "$@"
  else
    "$@"
  fi
}

# 📊 Funktion: Fortschrittsanzeige
function progress_bar {
  local step=$1
  local total=10
  local done=$((step * 10 / total))
  local remain=$((total - done))
  local bar=$(printf "%0.s█" $(seq 1 $done))
  local space=$(printf "%0.s░" $(seq 1 $remain))
  echo -ne "\r[$bar$space] $((step * 100 / total))%"
  sleep 0.3
}

echo "🔄 Starte Update-Prozess vom main-Branch..."

# 🔁 Gehe in den Ordner, wo dieses Skript liegt
cd "$(dirname "$0")"

# 🔧 .env lesen (optional) für UPDATE_REPO_URL_MAIN
function read_env_value {
  local key="$1"
  local value=""
  if [ -f ".env" ]; then
    value=$(awk -F= -v k="$key" '$1==k { $1=""; sub(/^=/,""); print; exit }' .env | tr -d '\r')
    value="${value%\"}"
    value="${value#\"}"
  fi
  echo "$value"
}

REPO_URL="$(read_env_value "UPDATE_REPO_URL_MAIN")"
REPO_URL="${REPO_URL:-https://github.com/17Trust09/inventory_management}"
REBOOT_AFTER_UPDATE="$(read_env_value "REBOOT_AFTER_UPDATE")"
REBOOT_AFTER_UPDATE="${REBOOT_AFTER_UPDATE:-true}"
UPDATE_SERVICE_NAME="$(read_env_value "UPDATE_SERVICE_NAME")"

# 🗂️ Schritt 1: Backup vorbereiten
backup_dir="backup/$(date +%Y-%m-%d_%H-%M-%S)"
maybe_sudo mkdir -p "$backup_dir"
echo -n "📦 [1/7] Erstelle Backup-Verzeichnis... "
progress_bar 1
echo -e "\n➡️ Backup-Ordner: $backup_dir"

# 🧠 Schritt 2: DB sichern
echo -n "🗃️ [2/7] Backup der Datenbank... "
maybe_sudo cp ./db.sqlite3 "$backup_dir/db.sqlite3"
progress_bar 2 && echo " ✅"

# 🖼️ Schritt 3: Medien sichern
echo -n "🖼️ [3/7] Backup vom media-Ordner... "
maybe_sudo cp -r ./media "$backup_dir/media"
progress_bar 3 && echo " ✅"

# 📁 Schritt 4: Wechsle in Projektordner
echo -n "📂 [4/7] Wechsle in Projektordner... "
progress_bar 4 && echo " ✅"

# 🌱 Schritt 5: Git Pull vom main-Branch
echo -n "⬇️ [5/7] Git Pull vom main-Branch... "
if [ ! -d ".git" ]; then
  echo -e "\nℹ️ Git-Repo nicht gefunden – initialisiere Repository..."
  run_step "Git init" git init
  run_step "Git remote setzen" git remote add origin "$REPO_URL" || git remote set-url origin "$REPO_URL"
  run_step "Git fetch" git fetch origin main
  run_step "Git checkout main" git checkout -b main
  run_step "Git reset" git reset --hard origin/main
else
  run_step "Git remote prüfen" git remote get-url origin || git remote add origin "$REPO_URL"
  run_step "Git remote setzen" git remote set-url origin "$REPO_URL"
  run_step "Git checkout main" git checkout main || git checkout -b main
  run_step "Git pull" git pull origin main
fi
maybe_sudo chmod +x update_from_dev.sh
maybe_sudo chmod +x update_from_main.sh
progress_bar 5 && echo " ✅"

# 🐍 Schritt 6: venv aktivieren & Pakete installieren
echo -n "🐍 [6/7] Aktiviere venv und installiere requirements... "
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    run_step "Requirements installieren" pip install -r requirements.txt
    progress_bar 6 && echo " ✅"
else
    echo -e "\n⚠️ venv nicht gefunden! Bitte manuell aktivieren."
fi

# ⚙️ Schritt 7: Migration durchführen
echo -n "⚙️ [7/7] Migration prüfen... "
run_step "Migrationen ausführen" python manage.py migrate
progress_bar 7 && echo " ✅"

# ✅ Abschluss
echo -e "\n✅ Update abgeschlossen."
if [ -n "${UPDATE_SERVICE_NAME}" ]; then
  run_step "Service neu starten (${UPDATE_SERVICE_NAME})" maybe_sudo systemctl restart "$UPDATE_SERVICE_NAME"
fi
if [ "${REBOOT_AFTER_UPDATE}" = "true" ]; then
  echo "🔁 Reboot wird ausgeführt..."
  sleep 2
  maybe_sudo reboot
else
  echo "ℹ️ Reboot übersprungen (REBOOT_AFTER_UPDATE=false)."
fi

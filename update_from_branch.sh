#!/bin/bash
set -euo pipefail

BRANCH_NAME="${1:-}"
if [ -z "$BRANCH_NAME" ]; then
  echo "Usage: $0 <branch-name>" >&2
  exit 1
fi

cd "$(dirname "$0")"

LOG_DIR="backup"
LOG_FILE="${LOG_DIR}/update_${BRANCH_NAME//\//_}_$(date +%Y-%m-%d_%H-%M-%S).log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

function run_step {
  local label=$1
  shift
  echo -e "\n🔹 ${label}"
  "$@"
}

function maybe_sudo {
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    "$@"
  fi
}

function read_env_value {
  local key="$1"
  local value=""
  if [ -f ".env" ]; then
    value=$(grep -E "^${key}=" .env | head -n 1 | cut -d= -f2- | tr -d '\r' || true)
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
  fi
  echo "$value"
}

REPO_URL="$(read_env_value "UPDATE_REPO_URL_MAIN")"
REPO_URL="${REPO_URL:-https://github.com/17Trust09/inventory_management}"
UPDATE_SERVICE_NAME="$(read_env_value "UPDATE_SERVICE_NAME")"
REBOOT_AFTER_UPDATE="$(read_env_value "REBOOT_AFTER_UPDATE")"
REBOOT_AFTER_UPDATE="${REBOOT_AFTER_UPDATE:-false}"

if [ ! -d ".git" ]; then
  run_step "Git init" git init
  run_step "Git remote setzen" git remote add origin "$REPO_URL" || git remote set-url origin "$REPO_URL"
else
  run_step "Git remote prüfen" git remote get-url origin || git remote add origin "$REPO_URL"
  run_step "Git remote setzen" git remote set-url origin "$REPO_URL"
fi

run_step "Git fetch (${BRANCH_NAME})" git fetch origin "$BRANCH_NAME"
run_step "Remote-Tracking aktualisieren (${BRANCH_NAME})" git fetch origin "$BRANCH_NAME:refs/remotes/origin/$BRANCH_NAME"
run_step "Branch auf origin/${BRANCH_NAME} setzen" git checkout -B "$BRANCH_NAME" "origin/$BRANCH_NAME"

if [ -f "venv/bin/activate" ]; then
  echo "🐍 Aktiviere venv..."
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

run_step "Migrationen ausführen" python manage.py migrate

if [ -n "$UPDATE_SERVICE_NAME" ]; then
  run_step "Service neu starten (${UPDATE_SERVICE_NAME})" maybe_sudo systemctl restart "$UPDATE_SERVICE_NAME"
else
  echo "ℹ️ Kein UPDATE_SERVICE_NAME in .env gesetzt; Service-Restart übersprungen."
fi

if [ "$REBOOT_AFTER_UPDATE" = "true" ]; then
  echo "🔁 Reboot wird ausgeführt..."
  maybe_sudo reboot
else
  echo "ℹ️ Reboot übersprungen (REBOOT_AFTER_UPDATE=${REBOOT_AFTER_UPDATE})."
fi

echo "✅ Branch-Update abgeschlossen: ${BRANCH_NAME}"

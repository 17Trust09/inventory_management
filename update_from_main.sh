#!/bin/bash

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

# 🗂️ Backup-Verzeichnis vorbereiten
mkdir -p backup

progress_bar 1
echo "📦 Erstelle Backup unter: backup/2025-07-26_09-28-54"
mkdir -p backup/2025-07-26_09-28-54

# 📂 DB-Backup
progress_bar 2
cp ./inventory_management/db.sqlite3 backup/2025-07-26_09-28-54/db.sqlite3 && echo "✅ DB-Backup gespeichert."

# 📂 Medien-Backup
progress_bar 3
cp -r ./inventory_management/media backup/2025-07-26_09-28-54/media && echo "✅ Medienordner gesichert."

# 🔁 In Projektordner wechseln
cd inventory_management || {
    echo "❌ Ordner 'inventory_management' nicht gefunden!"
    exit 1
}

# 🔄 Main-Branch aktivieren & aktualisieren
progress_bar 5
echo "📥 Wechsel auf main-Branch und ziehe Änderungen..."
git checkout main && git pull origin main
# 🔐 Stelle sicher, dass beide Update-Skripte ausführbar bleiben
sudo chmod +x update_from_dev.sh
sudo chmod +x update_from_main.sh


# ♻️ venv aktivieren
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ venv aktiviert."
else
    echo "⚠️ venv nicht gefunden! Bitte manuell prüfen."
fi

# 📦 Pakete aktualisieren
progress_bar 6
echo "📦 Installiere/aktualisiere Pakete aus requirements.txt..."
pip install -r requirements.txt

# 🔄 Migration
progress_bar 7
echo "⚙️ Führe Migrationscheck durch..."
python manage.py migrate

# ✅ Abschluss
progress_bar 8
echo -e "\n✅ Update vom main-Branch abgeschlossen. Starte nun den Pi neu..."
sleep 3
sudo reboot
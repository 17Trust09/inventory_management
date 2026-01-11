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

# 🔁 Gehe in den Ordner, wo dieses Skript liegt
cd "$(dirname "$0")"

# 🗂️ Schritt 1: Backup vorbereiten
backup_dir="backup/$(date +%Y-%m-%d_%H-%M-%S)"
sudo mkdir -p "$backup_dir"
echo -n "📦 [1/7] Erstelle Backup-Verzeichnis... "
progress_bar 1
echo -e "\n➡️ Backup-Ordner: $backup_dir"

# 🧠 Schritt 2: DB sichern
echo -n "🗃️ [2/7] Backup der Datenbank... "
sudo cp ./db.sqlite3 "$backup_dir/db.sqlite3"
progress_bar 2 && echo " ✅"

# 🖼️ Schritt 3: Medien sichern
echo -n "🖼️ [3/7] Backup vom media-Ordner... "
sudo cp -r ./media "$backup_dir/media"
progress_bar 3 && echo " ✅"

# 📁 Schritt 4: Wechsle in Projektordner
echo -n "📂 [4/7] Wechsle in Projektordner... "
progress_bar 4 && echo " ✅"

# 🌱 Schritt 5: Git Pull vom main-Branch
echo -n "⬇️ [5/7] Git Pull vom main-Branch... "
git checkout main && git pull origin main &> /dev/null
sudo chmod +x update_from_dev.sh
sudo chmod +x update_from_main.sh
progress_bar 5 && echo " ✅"

# 🐍 Schritt 6: venv aktivieren & Pakete installieren
echo -n "🐍 [6/7] Aktiviere venv und installiere requirements... "
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    pip install -r requirements.txt &> /dev/null
    progress_bar 6 && echo " ✅"
else
    echo -e "\n⚠️ venv nicht gefunden! Bitte manuell aktivieren."
fi

# ⚙️ Schritt 7: Migration durchführen
echo -n "⚙️ [7/7] Migration prüfen... "
python manage.py migrate &> /dev/null
progress_bar 7 && echo " ✅"

# ✅ Abschluss
echo -e "\n✅ Update abgeschlossen. Raspberry Pi wird jetzt neu gestartet..."
sleep 2
sudo reboot

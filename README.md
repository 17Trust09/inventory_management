# 🧰 Django Inventory Management System

Ein lokales Inventarsystem mit Benutzerrollen, QR-Code-Unterstützung, Tag-Zugriff und Standortverwaltung. Entwickelt für kleine Werkstätten, Bastelzimmer oder Lagerbereiche.

---

## 🚀 Lokales Setup

```bash
git clone https://github.com/17Trust09/inventory_management.git
cd inventory_management
python -m venv venv
venv\Scripts\activate     # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## 🌱 Branch-Strategie

- `main`: nur getesteter und stabiler Code.
- `dev`: aktiver Entwicklungsstand.
- `feature/*`: einzelne Features/To-dos.

### 🔀 Wechseln und Pushen zu einem Branch

```bash
git checkout dev
git pull origin dev

# Änderungen hinzufügen
git add .
git commit -m "Fix: QR-Code bei Änderung regenerieren"

# In aktuellen Branch pushen
git push origin dev
```

### 📌 Neuen Feature-Branch erstellen

```bash
git checkout -b feature/qr-code-listing
git push -u origin feature/qr-code-listing
```

---

## 🧼 Dateien und Ordner ignorieren (Git)

Bearbeite deine `.gitignore`:

```gitignore
media/
db.sqlite3
__pycache__/
*.pyc
```

### 🧹 Medien und DB aus Git entfernen (aber behalten)

```bash
git rm --cached -r media/
git rm --cached db.sqlite3
git commit -m "Remove tracked media folder and db file"
git push
```

📝 **Die Dateien bleiben lokal erhalten, werden aber nicht mehr zu Git gepusht.**

---

## 💾 Datenbank-Backup (lokal)

```bash
copy db.sqlite3 db_backup.sqlite3
```

Auf Linux/Mac:

```bash
cp db.sqlite3 db_backup.sqlite3
```

---

## 🔄 Datenbank bei Änderungen abgleichen

Wenn du von einem Branch pullst, bei dem sich das Datenbankschema verändert hat:

1. Backup machen: `cp db.sqlite3 db_backup.sqlite3`
2. Neue Datenbank erzeugen: `python manage.py migrate`
3. Optional: Daten aus Backup manuell wiederherstellen oder mit `dumpdata/loaddata`.

> 💡 Langfristig empfiehlt sich die Umstellung auf PostgreSQL o. ä.

---

## 📦 GitHub-Repo

🔗 https://github.com/17Trust09/inventory_management

---

**Letzte Änderung:** 2025-07-26  
**Maintainer:** 17Trust09  

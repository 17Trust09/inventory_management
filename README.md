# 📦 Lagerverwaltungssystem – Django-basiertes Inventarsystem

Dieses Projekt ist ein voll funktionsfähiges Inventarverwaltungssystem mit:
- QR- und Barcode-Unterstützung
- Benutzerrollen & Tags
- Dark Mode & Weboberfläche
- Home-Assistant-Integration
- Foto-Upload, Wartungsdaten & Bestandswarnung

---

## 🚀 Lokales Setup (Entwicklung)

1. Repository clonen:
```bash
git clone https://github.com/17Trust09/inventory_management.git
cd inventory_management
```

2. Virtuelle Umgebung einrichten:
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

3. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

4. Migrations durchführen:
```bash
python manage.py migrate
```

5. Lokalen Dev-Server starten:
```bash
python manage.py runserver
```

---

## 🔁 Git-Workflow & Branch-Strategie

> Der `main`-Branch ist **stabil** und wird nur nach Review aktualisiert.  
> Neue Entwicklungen erfolgen in **eigenen Feature-Branches** und werden über `dev` integriert.

### 🔴 Branch-Übersicht:

| Branch         | Zweck                                   |
|----------------|------------------------------------------|
| `main`         | stabiler Produktionscode                |
| `dev`          | Entwicklungszweig (Sammelbecken)        |
| `feature/*`    | neue Funktionen (z. B. `feature/qr`)     |
| `bugfix/*`     | Fehlerbehebungen                        |
| `test/*`       | experimentelle Zweige                   |

---

### 🛠 Feature-Branch erstellen und pushen

```bash
# Neuen Branch erstellen
git checkout -b feature/<beschreibung>

# Änderungen speichern
git add .
git commit -m "Feature: <kurze Beschreibung>"

# Branch auf GitHub pushen
git push origin feature/<beschreibung>
```

Beispiel:
```bash
git checkout -b feature/form-fix
git add .
git commit -m "Fix: verschachtelte Formulare entfernt"
git push origin feature/form-fix
```

---

### 🔃 Pull Request Workflow

1. Auf GitHub einen Pull Request von `feature/*` nach `dev` öffnen.
2. Änderungen testen.
3. Wenn `dev` stabil ist, Merge in `main`.

---

## 🧪 Testen

Du kannst Funktionen lokal über z. B. folgende Seiten testen:

- `/dashboard/`
- `/add-item/`
- `/edit-item/<id>/`
- `/admin/`

---

## 🧰 Tools & Versionen

- **Python:** 3.10+
- **Django:** 4.x
- **Datenbank:** SQLite (Standard) oder PostgreSQL
- **Frontend:** Bootstrap + Custom Dark Theme
- **QR/Barcode:** Pillow, qrcode, python-barcode

---

## 📌 To-dos (Kurzfassung)

- [ ] QR-Code bei Namens-/Ortänderung automatisch neu generieren
- [ ] Geräteausgabe-Modus (Ausleihen/Rückgabe)
- [ ] Item-Historie
- [ ] Admin-QR-Code-Übersicht
- [ ] Kommentarsystem

Vollständige Liste: [TODO.md folgt]

---

## 👤 Maintainer

**17Trust09**  
GitHub: [@17Trust09](https://github.com/17Trust09)


---

## 🌿 Weitere Branch-Typen pushen

Neben `feature/*` kannst du natürlich auch andere Branches nutzen:

### 🔧 Bugfix-Branch:
```bash
git checkout -b bugfix/<beschreibung>
# Beispiel:
git checkout -b bugfix/image-upload
git add .
git commit -m "Bugfix: Bild-Upload korrigiert"
git push origin bugfix/image-upload
```

### 🧪 Test-Branch:
```bash
git checkout -b test/<zweck>
# Beispiel:
git checkout -b test/qr-experiment
git push origin test/qr-experiment
```

### 🧬 Dev-Branch direkt anlegen (wenn nicht vorhanden):
```bash
git checkout -b dev
git push origin dev
```

Anschließend kannst du beliebige Feature- oder Fix-Branches auf `dev` mergen.

---



---

## 🛡️ Backup & Datenbanksicherung (empfohlen vor jedem Pull)

Wenn du dein Projekt bereits auf einem Host geklont und benutzt hast (z. B. auf dem Raspberry Pi), solltest du vor einem Update/Pull **ein Backup machen**.

### 🔁 Git-Projekt sichern (inkl. Datenbank)

```bash
# 1. Projektordner sichern
cp -r inventory_management inventory_management_backup_$(date +%Y%m%d)

# 2. Datenbank separat sichern (Standard: db.sqlite3)
cp inventory_management/db.sqlite3 db_backup_$(date +%Y%m%d).sqlite3
```

### 📂 Alternative mit Versionsverwaltung (empfohlen):
```bash
# Repository sichern (inkl. .git-Verlauf)
cd ..
cp -r inventory_management inventory_management_backup
```

---

## 🔄 Nach einem Pull – bestehende Datenbank übernehmen

Wenn du z. B. auf `dev` oder `main` einen neuen Stand holst:

```bash
git checkout dev
git pull origin dev
```

Stelle sicher, dass die **alte Datenbank** (`db.sqlite3`) erhalten bleibt:

### ✅ So behältst du deine Daten:

1. Vorher sichern:
```bash
cp db.sqlite3 db_backup_before_pull.sqlite3
```

2. Nach dem `pull`, aber vor dem Start:
```bash
# Migrationen prüfen/anwenden
python manage.py makemigrations
python manage.py migrate
```

3. Wenn sich das Datenmodell geändert hat, bleiben **alle bestehenden Daten erhalten**, **sofern keine Felder gelöscht wurden**.

---

## 🧠 Empfehlung: Daten aus alter DB übernehmen (z. B. bei Strukturänderung)

Wenn du auf ein neues Repo oder Branch wechselst, aber deine alten Einträge behalten willst:

1. Alte Datenbank umbenennen:
```bash
mv db.sqlite3 db_OLD.sqlite3
```

2. Neue Struktur anlegen:
```bash
python manage.py migrate
```

3. Dann kannst du Tools wie `sqlitebrowser` oder `python manage.py dbshell` nutzen, um Daten zu übertragen (z. B. per SQL oder Export/Import)

---


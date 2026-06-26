# 📦 Lagerverwaltungssystem – Django-basiertes Inventarsystem

Voll funktionsfähiges Inventarverwaltungssystem mit Dashboard, Barcode/NFC-Unterstützung, Ausleihsystem, Admin-Frontend und **ESP32-LED-Regalanzeige**.

---

## 📋 Hauptfunktionen

| Funktion | Beschreibung |
|---|---|
| **Dashboard** | Modulare Overviews mit Filter, Sortierung, Export |
| **Items** | Equipment + Verbrauchsmaterial mit Mengenverwaltung |
| **Barcode & QR** | Automatische Generierung von Barcodes/QR-Codes pro Item |
| **NFC-Tags** | NFC-Token für schnellen Zugriff per Smartphone |
| **Standorte** | Lagerorte (Reihe/Fach/Spalte) mit optionaler HA-Verknüpfung |
| **Ausleihe** | Borrow/Return-System mit Mengenverfolgung |
| **Admin** | Eigenes Admin-Frontend (User, Tags, Kategorien, Einstellungen) |
| **Home Assistant** | HA-Integration für Status-Badge, Benachrichtigungen |
| **Feedback** | Internes Feedback-Board mit Voting |
| **Backup** | Automatisierte DB-Backups mit Aufbewahrungsfrist |
| **🔴 ESP-LED** | Markierte Items per WS2812B-LED-Streifen im Regal anzeigen |

---

## 🚀 Installation & Betrieb

### Variante A: Docker auf Unraid (empfohlen)

Siehe [`docs/unraid-docker.md`](docs/unraid-docker.md) für die vollständige Anleitung.

Kurzzusammenfassung:

```bash
# 1. Projekt klonen
git clone https://github.com/17Trust09/inventory_management.git /mnt/data/appdata/inventory_management
cd /mnt/data/appdata/inventory_management

# 2. .env anlegen (siehe Beispiel unten)

# 3. Im Unraid Compose Manager einen Stack anlegen
#    → Siehe docs/unraid-docker.md für das compose-File

# 4. Stack starten → Migration läuft automatisch

# 5. Admin-User anlegen
docker exec -it inventory_app python manage.py createsuperuser
```

### Variante B: Direkt auf einem Server / Raspberry Pi

```bash
git clone https://github.com/17Trust09/inventory_management.git
cd inventory_management

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# DB einrichten (PostgreSQL oder SQLite)
# → settings.py: DB_ENGINE=postgres (default) oder DB_ENGINE=sqlite
cp .env.example .env  # und anpassen

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

---

## ⚙️ Konfiguration

### `.env` – Wichtige Variablen

```env
# ── Django ──
DJANGO_SECRET_KEY=dein-langer-zufaelliger-key
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=http://192.168.178.69:18000

# ── Datenbank ──
DB_ENGINE=postgres          # postgres | sqlite | mysql
POSTGRES_DB=inventorydb
POSTGRES_USER=inventory
POSTGRES_PASSWORD=inventory
POSTGRES_HOST=192.168.178.69
POSTGRES_PORT=15433

# ── Home Assistant (optional) ──
HA_API_TOKEN=
HA_URL=http://homeassistant.local:8123
HA_MARK_EVENT=inventory_item_marked

# ── API-Key für externe Zugriffe (ESP32, Health-Checks) ──
FEEDBACK_API_KEY=dein-api-key

# ── Basis-URL für generierte Links ──
INVENTORY_BASE_URL=http://192.168.178.69:18000
```

### Mark-Button aktivieren

Damit der "Markieren"-Button im Dashboard sichtbar ist, muss in den **Globalen Einstellungen** (Admin → Globale Einstellungen) die Option **"Markieren-Button anzeigen"** aktiviert werden.

---

## 🔴 ESP32 – Regal-LED-Anzeige

Zeigt mit WS2812B-LEDs an, **welcher Lagerort** (z. B. Schublade) markiert ist.
Items werden über den **StorageLocation-Baum** bis zum untersten Blattknoten verfolgt.

### Funktionsweise

1. Ein Item im Dashboard markieren
2. Django ermittelt den **untersten StorageLocation** (Blatt im Baum)
3. Eintrag in der `ItemMark`-Tabelle mit `location_id`
4. ESP32 pollt alle 3s `GET /api/marked-items/?key=...`
5. API liefert `location_id` → ESP mapped auf LED-Index via `position_map.h`
6. LED leuchtet auf

### Benötigte Hardware

| Komponente | Empfehlung | Preis |
|---|---|---|
| ESP32 Dev Board | ESP32-WROOM-32 (z. B. AZ-Delivery) | ~10 € |
| LED-Streifen | WS2812B (NeoPixel), 5V, 60 LEDs/m | ~15 €/m |
| Netzteil | 5V / 2A (60 LEDs), 5V / 10A (300 LEDs) | ~10-20 € |
| Kondensator | 1000 µF zwischen 5V und GND | ~1 € |
| Widerstand | 470 Ω auf Datenleitung (GPIO → DI) | ~0,10 € |

### Verdrahtung

```
ESP32                     WS2812B Streifen
─────                     ───────────────
GPIO 13 ──[470Ω]────────► DI (Daten-Eingang)
GND     ───────────────── GND
5V      ───────┐
                │
          ┌─────┴─────┐
          │  5V Netzteil │
          └───────────┘
              5V ────────► 5V (LED-Streifen)
              GND ──────── GND
```

> **⚠️ Wichtig:** Bei Strips > 1 m Länge Strom alle 2-3 Meter nachspeisen (5V+GND).

### Installation (PlatformIO)

```bash
# 1. PlatformIO installieren (einmalig)
pip install platformio

# 2. In das ESP32-Projekt wechseln
cd esp32-led-marker

# 3. Konfiguration anpassen (siehe nächster Abschnitt)

# 4. Kompilieren & flashen
pio run --target upload

# 5. Serielle Ausgabe beobachten
pio device monitor
```

### Konfiguration (`esp32-led-marker/src/config.h`)

```c++
// WLAN
const char* WLAN_SSID = "DEIN_WLAN";
const char* WLAN_PASS = "DEIN_PASSWORT";

// API
const char* API_URL = "http://192.168.178.69:18000/api/marked-items/";
const char* API_KEY="dein-api-key";  // = FEEDBACK_API_KEY aus .env

// LED-Streifen
const int   LED_PIN    = 13;      // GPIO
const int   NUM_LEDS   = 60;      // Anzahl LEDs
const int   BRIGHTNESS = 80;      // Helligkeit 0-255

// Timing
const int   POLL_INTERVAL_MS = 3000;   // Alle 3s API abfragen
const int   LED_TIMEOUT_SEC  = 300;    // LED nach 5 Min ohne Update aus

// Farbe
const uint32_t MARK_COLOR = strip.Color(0, 0, 255);  // Blau
```

### Position-Mapping (`esp32-led-marker/src/position_map.h`)

Jede **Schublade / jeder Lagerort** bekommt genau eine LED.
Das Mapping ist `location_id → LED-Index`:

```c++
const PositionEntry POSITION_MAP[] = {
    // {location_id, LED_Index}
    {1,  0},   // Schublade 1  → LED #0
    {2,  1},   // Schublade 2  → LED #1
    {3,  2},   // Schublade 3  → LED #2
    ...
};
```

So findest du die `location_id`:
- Via API: `curl "http://DEINE_IP:18000/api/marked-items/?key=KEY"` → Feld `location_id`
- Im Django-Admin: **Lagerorte** → ID-Spalte

### API-Referenz

```http
GET /api/marked-items/?key=dein-api-key

{
  "marks": [
    {
      "id": 42,
      "name": "Schraube M8",
      "location_id": 7,
      "location_name": "Schublade 1",
      "location_path": "Regal A > Schublade 1",
      "mark_id": 1,
      "marked_at": "2026-06-26T07:09:00+00:00",
      "is_active": true
    }
  ],
  "count": 1,
  "checked_at": "2026-06-26T07:09:03+00:00"
}
```

---

## 🧪 Test-Routen

| Route | Beschreibung |
|---|---|
| `/` | Startseite / Login |
| `/dashboard/` | Dashboard-Übersicht |
| `/dashboards/` | Dashboard-Selektor |
| `/add-equipment/` | Neues Equipment anlegen |
| `/add-verbrauch/` | Neues Verbrauchsmaterial anlegen |
| `/edit-item/<id>/` | Item bearbeiten |
| `/admin/` | Django-Superuser-Admin |
| `/manage/` | Eigenes Admin-Frontend |
| `/barcodes/` | Barcode-Übersicht |
| `/scan-barcode/` | Barcode-Scanner-Ansicht |
| `/borrow/<id>/` | Item ausleihen |
| `/feedback/` | Feedback-Board |
| `/api/marked-items/` | **ESP32-API**: markierte Items |
| `/api/health/system/` | System-Health-Check |
| `/patch-notes/` | Versionshinweise |

---

## 🧰 Git-Workflow

| Branch | Zweck |
|---|---|
| `main` | Stabiler Produktionscode |
| `dev` | Entwicklungszweig (Sammelbecken) |
| `feature/*` | Neue Funktionen |
| `bugfix/*` | Fehlerbehebungen |

```bash
# Neuen Feature-Branch anlegen
git checkout -b feature/mein-feature

# Änderungen committen
git add .
git commit -m "Feat: Kurzbeschreibung"

# Nach GitHub pushen
git push origin feature/mein-feature

# → Pull Request auf GitHub von feature/* nach dev öffnen
```

---

## 📌 To-Dos (Kurzfassung)

- [x] ESP32-LED-Anzeige (`feature/esp-led-marking`)
- [ ] Vollständige `TODO.md` mit Roadmap
- [ ] Gunicorn-Produktions-Setup

---

## 👤 Maintainer

**17Trust09** – [GitHub](https://github.com/17Trust09)

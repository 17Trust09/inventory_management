# ESP32 Regal-LED Anzeige

Zeigt mit WS2812B-LEDs an, welcher **Lagerort** (z. B. Schublade) markiert ist.
Items werden über den StorageLocation-Baum bis zum **untersten Blattknoten** verfolgt.

---

## 🔄 Funktionsweise

1. In der Lagerdatenbank wird ein Item markiert
2. Django ermittelt den **untersten StorageLocation** (Blatt im Baum)
3. Eintrag in `ItemMark`-Tabelle mit `location_id`
4. ESP pollt alle 3s `GET /api/marked-items/?key=...`
5. API liefert `location_id` jedes markierten Items
6. ESP mapped `location_id → LED` und leuchtet die passende LED

---

## 🔌 Hardware

| Komponente | Empfehlung | Preis |
|---|---|---|
| ESP32 Dev Board | ESP32-WROOM-32, z. B. AZ-Delivery | ~10 € |
| LED-Streifen | WS2812B (NeoPixel), 5V, 60 LEDs/m | ~15 €/m |
| Netzteil | 5V / 2A (60 LEDs), 5V / 10A (300 LEDs) | ~10–20 € |
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
          │ 5V Netzteil │
          └───────────┘
              5V ────────► 5V+ (LED-Streifen)
              GND ─────── GND
```

> **⚠️ Wichtig:** Bei Strips > 1 m Länge Strom **alle 2 m nachspeisen** (5V+GND), sonst werden hintere LEDs dunkler.

---

## ⚙️ Konfiguration

### 1. `src/config.h`

```c++
// WLAN
const char* WLAN_SSID = "DEIN_WLAN";
const char* WLAN_PASS = "DEIN_PASSWORT";

// API – URL zum Django-Endpoint
const char* API_URL = "http://192.168.178.69:18000/api/marked-items/";
const char* API_KEY=***  // = FEEDBACK_API_KEY aus .env

// LED-Streifen
const int   LED_PIN    = 13;       // GPIO (D13)
const int   NUM_LEDS   = 60;       // LEDs im Streifen
const int   BRIGHTNESS = 80;       // 0-255

// Timing
const int   POLL_INTERVAL_MS = 3000;   // Alle 3s API abfragen
const int   LED_TIMEOUT_SEC  = 300;    // LED nach 5 Min ohne Update aus

// Farbe
const uint32_t MARK_COLOR = strip.Color(0, 0, 255);  // Blau
```

### 2. `src/position_map.h` – Location-ID → LED

Jede **Schublade/jeder Lagerort** bekommt eine LED.  
Das Mapping ist `location_id → LED-Index`.

So findest du die IDs:

```bash
# Einfach die API abfragen (einmalig)
curl "http://DEINE_IP:18000/api/marked-items/?key=DEIN_KEY"

# Oder im Django-Admin: Lagerorte → ID-Spalte
```

Dann trägst du sie in `position_map.h` ein:

```c++
const PositionEntry POSITION_MAP[] = {
    // {location_id, LED_Index}
    {1,  0},   // Schublade 1 → LED #0
    {2,  1},   // Schublade 2 → LED #1
    {3,  2},   // Schublade 3 → LED #2
    ...
};
```

**Beispiel:** Wenn das Item in "Regal A > Schublade 3" liegt und Schublade 3 hat `id=7`, dann leuchtet `LED #6`.

---

## 🚀 Installation

### PlatformIO

```bash
# 1. PlatformIO installieren (einmalig)
pip install platformio

# 2. Ins Projektverzeichnis wechseln
cd esp32-led-marker

# 3. Kompilieren & auf ESP32 flashen
pio run --target upload

# 4. Serielle Ausgabe beobachten
pio device monitor
```

Erwartete Ausgabe:
```
===================================
  ESP32 Regal-LED Anzeige v1.0
===================================
💡 60 LEDs initialisiert (Pin 13)
🔗 Verbinde mit WLAN: MeinWLAN..
✅ Verbunden. IP: 192.168.1.42
📦 Markierte Items: 2
  location_id=7 (Schraube M8) → LED #6
```

---

## 📡 API-Referenz

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

| Feld | Typ | Beschreibung |
|---|---|---|
| `id` | int | Item-ID in der Django-DB |
| `name` | string | Item-Name |
| `location_id` | int | **StorageLocation-ID** → LED-Position |
| `location_name` | string | Name des Lagerorts (z. B. "Schublade 1") |
| `location_path` | string | Vollständiger Pfad im Baum (z. B. "Regal A > Schublade 1") |
| `mark_id` | int | ID der Markierung |
| `marked_at` | string | Zeitstempel (ISO 8601) |
| `is_active` | bool | Noch gültig? |

---

## 🚨 Fehlersuche

| Problem | Ursache | Lösung |
|---|---|---|
| WLAN keine Verbindung | Falsche SSID/Passwort | `config.h` prüfen |
| Keine LEDs | Falscher GPIO | `LED_PIN` prüfen |
| API 403 | Falscher Key | `API_KEY` = `FEEDBACK_API_KEY` aus `.env` |
| API 404 | URL falsch | `API_URL` prüfen (Port 18000?) |
| "hat keinen Lagerort" | Item hat keine `storage_location` | Item in Django zuordnen |
| "nicht in POSITION_MAP" | location_id fehlt im Mapping | Eintrag in `position_map.h` ergänzen |
| Hintere LEDs dunkel | Spannungsabfall | Strom nachspeisen |
| ESP startet neu | Netzteil zu schwach | 5V/2A+ Netzteil |

---

## 💡 Erweiterungen

- **Mehrere Farben:** Pro Item-Typ oder Kategorie andere Farbe
- **Pulsieren:** LEDs sanft pulsieren lassen
- **Mehrere ESPs:** Ein ESP pro Regal, jeder pollt unabhängig
- **MQTT:** Push statt Polling (fortgeschritten)
- **OLED:** Zeige Item-Namen statt nur LED (für Debug)

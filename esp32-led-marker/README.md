# ESP32 Regal-LED Anzeige

Zeigt mit WS2812B-LEDs an, wo ein markiertes Item im Regal liegt.

## Funktionsweise

1. In der Lagerdatenbank wird ein Item markiert → Eintrag in `ItemMark`-Tabelle
2. Der ESP pollt alle 3s `GET /api/marked-items/?key=...`
3. Antwort enthält Position (letter, number, shelf) jedes markierten Items
4. ESP leuchtet die entsprechende LED am Streifen auf

## Hardware

| Komponente | Empfehlung |
|---|---|
| ESP32 Dev Board | ESP32-WROOM-32 (~10€) |
| LED-Streifen | WS2812B (NeoPixel), 5V, 60 LEDs/m |
| Netzteil | 5V / 2A (für ~60 LEDs) |
| Kondensator | 1000µF zwischen 5V und GND (glättet Spannung) |
| Widerstand | 330-470Ω auf Datenleitung (D-Pin → LED DI) |

## Setup

### 1. Konfiguration anpassen

`src/config.h`:
- `WLAN_SSID` / `WLAN_PASS` – dein WLAN
- `API_URL` – IP der Django-App (z.B. `http://192.168.178.69:18000/api/marked-items/`)
- `API_KEY` – aus der `.env` der Django-App: `FEEDBACK_API_KEY=...`
- `LED_PIN` – GPIO des Daten-Pins
- `NUM_LEDS` – Anzahl LEDs in deinem Streifen
- `MARK_COLOR` – Farbe der Markierung (R, G, B)

### 2. Position-Mapping anpassen

`src/position_map.h`:
- Trage für jede Regalposition den passenden LED-Index ein
- Format: `{"Buchstabe", Spaltennummer, "Fach", LED_Index}`

### 3. Flashen mit PlatformIO

```bash
# PlatformIO installieren (einmalig)
pip install platformio

# In das Projektverzeichnis wechseln
cd esp32-led-marker

# Kompilieren & flashen
pio run --target upload

# Serielle Ausgabe beobachten
pio device monitor
```

## API-Response (Referenz)

```json
GET /api/marked-items/?key=geheim

{
  "marks": [
    {
      "id": 42,
      "name": "Schraube M8",
      "position": { "letter": "B", "number": 3, "shelf": "2" },
      "mark_id": 1,
      "marked_at": "2026-06-26T07:09:00+00:00",
      "is_active": true
    }
  ],
  "count": 1,
  "checked_at": "2026-06-26T07:09:03+00:00"
}
```

## Erweiterungen (Ideen)

- **Mehrere Farben:** Unterschiedliche Item-Typen in verschiedenen Farben
- **Pulsieren/Blinken:** Aktive Markierungen sanft pulsieren lassen
- **Mehrere ESPs:** Ein ESP pro Regal, jeder pollt unabhängig
- **MQTT:** Statt Polling per MQTT-Push von der Django-App (fortgeschritten)

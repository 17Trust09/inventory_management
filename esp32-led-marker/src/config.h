#ifndef CONFIG_H
#define CONFIG_H

// ═════════════════════════════════════════════════════════════════════════════
//  WLAN-Konfiguration
// ═════════════════════════════════════════════════════════════════════════════
const char* WLAN_SSID       = "DEIN_WLAN_NAME";
const char* WLAN_PASS       = "DEIN_WLAN_PASSWORT";

// ═════════════════════════════════════════════════════════════════════════════
//  API-Konfiguration (Django Lagerdatenbank)
// ═════════════════════════════════════════════════════════════════════════════
const char* API_URL = "http://192.168.178.69:18000/api/marked-items/";
const char* API_KEY = "DEIN_FEEDBACK_API_KEY";  // ← Aus .env: FEEDBACK_API_KEY

// ═════════════════════════════════════════════════════════════════════════════
//  LED-Konfiguration (WS2812B / NeoPixel)
// ═════════════════════════════════════════════════════════════════════════════
const int   LED_PIN          = 13;       // GPIO 13 (D13 auf den meisten ESP32-Boards)
const int   NUM_LEDS         = 60;       // Anzahl LEDs im Streifen
const int   BRIGHTNESS       = 80;       // Helligkeit 0-255 (80 = ~30%)

// ═════════════════════════════════════════════════════════════════════════════
//  Timing
// ═════════════════════════════════════════════════════════════════════════════
const int   POLL_INTERVAL_MS  = 3000;     // Alle 3 Sekunden API abfragen
const int   LED_TIMEOUT_SEC   = 300;      // LED nach 5 Minuten ohne Update aus

// ═════════════════════════════════════════════════════════════════════════════
//  Farben (RGB-Werte)
// ═════════════════════════════════════════════════════════════════════════════
const uint32_t MARK_COLOR = strip.Color(0, 0, 255);  // Blau – ändere auf z.B. (255, 100, 0) für Orange

#endif // CONFIG_H

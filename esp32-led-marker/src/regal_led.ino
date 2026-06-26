/*
 * ESP32 Regal-LED Anzeige
 * ========================
 *
 * Holt alle markierten Items von der Django-Lagerdatenbank (REST-API)
 * und leuchtet die entsprechende Position auf einem WS2812B-LED-Streifen.
 *
 * Konfiguration (Werte in config.h anpassen):
 *   - WLAN_SSID / WLAN_PASS
 *   - API_URL (URL zum /api/marked-items/-Endpoint)
 *   - API_KEY (optional)
 *   - NUM_LEDS (Anzahl LEDs im Streifen, z.B. 60)
 *   - LED_PIN (GPIO des Daten-Pins)
 *   - POLL_INTERVAL_MS (Abfrageintervall in ms)
 *   - LED_TIMEOUT_SEC (Sekunden, die eine LED leuchtet, bevor sie ausgeht)
 *
 * Hardware:
 *   - ESP32 Dev Board
 *   - WS2812B LED-Streifen (5V, Daten-Pin an LED_PIN)
 *   - Optional: 5V-Netzteil für den LED-Streifen
 *
 * LED-Position-Mapping:
 *   Der ESP muss wissen, welche LED zu welcher Position gehört.
 *   Anpassbar in position_map.h.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"
#include "position_map.h"

// ── Globale Zustände ──────────────────────────────────────────────────────────
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// Letzter bekannter Zustand der LEDs (damit wir nur ändern, wenn nötig)
bool ledState[NUM_LEDS] = {false};

// Zeitstempel, wann jede LED zuletzt aktualisiert wurde (für Auto-Timeout)
unsigned long ledTimestamps[NUM_LEDS] = {0};

// ── WiFi-Verbindung ───────────────────────────────────────────────────────────
void connectWiFi() {
    Serial.print("🔗 Verbinde mit WLAN: ");
    Serial.println(WLAN_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WLAN_SSID, WLAN_PASS);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.print("✅ Verbunden. IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println();
        Serial.println("❌ WLAN-Verbindung fehlgeschlagen. Neustart in 30s...");
        delay(30000);
        ESP.restart();
    }
}

// ── HTTP-Request ──────────────────────────────────────────────────────────────
bool fetchMarkedItems(JsonDocument &doc) {
    HTTPClient http;
    String url = String(API_URL) + "?key=" + String(API_KEY);
    http.begin(url);
    http.setTimeout(5000);  // 5s Timeout

    int code = http.GET();
    if (code != 200) {
        Serial.print("⚠️  HTTP-Fehler: ");
        Serial.println(code);
        http.end();
        return false;
    }

    DeserializationError err = deserializeJson(doc, http.getStream());
    if (err) {
        Serial.print("❌ JSON-Fehler: ");
        Serial.println(err.c_str());
        http.end();
        return false;
    }

    http.end();
    return true;
}

// ── Location-ID → LED-Index ─────────────────────────────────────────────────
int locationIdToLed(int locationId) {
    // Sucht in der position_map nach der passenden location_id
    for (size_t i = 0; i < POSITION_COUNT; i++) {
        if (POSITION_MAP[i].locationId == locationId) {
            return POSITION_MAP[i].ledIndex;
        }
    }
    return -1;  // Nicht gefunden
}

// ── Markierungs-Logik ─────────────────────────────────────────────────────────
void updateLEDs() {
    // Großer JSON-Puffer (16KB reichen für ~100 Items)
    StaticJsonDocument<16384> doc;

    if (!fetchMarkedItems(doc)) {
        Serial.println("⏳ Konnte API nicht erreichen – behalte alten Zustand.");
        return;
    }

    JsonArray marks = doc["marks"].as<JsonArray>();
    int count = doc["count"].as<int>();
    Serial.print("📦 Markierte Items: ");
    Serial.println(count);

    // Zuerst: Alle LEDs als "soll aus" markieren
    bool newState[NUM_LEDS];
    for (int i = 0; i < NUM_LEDS; i++) {
        newState[i] = false;
    }

    // Markierte Items durchgehen und LED-Positionen setzen
    unsigned long nowMs = millis();
    for (JsonObject mark : marks) {
        int locationId = mark["location_id"] | 0;
        if (locationId == 0) {
            const char *name = mark["name"] | "?";
            Serial.printf("  ⚠️  %s hat keinen Lagerort\n", name);
            continue;
        }

        int ledIdx = locationIdToLed(locationId);
        if (ledIdx >= 0 && ledIdx < NUM_LEDS) {
            newState[ledIdx] = true;
            ledTimestamps[ledIdx] = nowMs;
        } else {
            const char *name = mark["name"] | "?";
            Serial.printf("  ❓ location_id=%d (%s) nicht in POSITION_MAP\n", locationId, name);
        }
    }

    // LEDs aktualisieren (nur bei Änderung, um Flackern zu vermeiden)
    for (int i = 0; i < NUM_LEDS; i++) {
        if (newState[i] != ledState[i]) {
            ledState[i] = newState[i];
            if (newState[i]) {
                strip.setPixelColor(i, MARK_COLOR);
            } else {
                strip.setPixelColor(i, 0);  // Aus
            }
        } else if (newState[i] && (nowMs - ledTimestamps[i] > LED_TIMEOUT_SEC * 1000UL)) {
            // Auto-Timeout: LED nach X Sekunden ohne Update aus
            ledState[i] = false;
            strip.setPixelColor(i, 0);
        }
    }

    strip.show();
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n===================================");
    Serial.println("  ESP32 Regal-LED Anzeige v1.0");
    Serial.println("===================================");

    // LED-Streifen initialisieren
    strip.begin();
    strip.setBrightness(BRIGHTNESS);
    strip.show();  // Alle aus
    Serial.printf("💡 %d LEDs initialisiert (Pin %d)\n", NUM_LEDS, LED_PIN);

    // Start-Effekt: Alle LEDs kurz aufleuchten lassen
    for (int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, MARK_COLOR);
        strip.show();
        delay(5);
    }
    delay(200);
    for (int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, 0);
        strip.show();
        delay(5);
    }

    // WiFi
    connectWiFi();
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    // Prüfen, ob WiFi noch da ist
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("🔄 WLAN verloren – reconnect...");
        connectWiFi();
    }

    // Markierungen abrufen und LEDs aktualisieren
    updateLEDs();

    // Warten bis zum nächsten Poll
    delay(POLL_INTERVAL_MS);
}

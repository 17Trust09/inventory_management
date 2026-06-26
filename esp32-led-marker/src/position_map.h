#ifndef POSITION_MAP_H
#define POSITION_MAP_H

/*
 * POSITION_MAP: Übersetzt Regal-Position (Buchstabe + Zahl + Fach)
 * in einen LED-Index auf dem WS2812B-Streifen.
 *
 * Layout-Beispiel für ein Regal mit 4 Reihen (A-D) und 5 Spalten (1-5):
 *   A1 A2 A3 A4 A5   → LEDs 0-4
 *   B1 B2 B3 B4 B5   → LEDs 5-9
 *   C1 C2 C3 C4 C5   → LEDs 10-14
 *   D1 D2 D3 D4 D5   → LEDs 15-19
 *
 * shelf = Fachnummer (0 = Hauptfach, 1 = Oberfach, etc.)
 * letter = Regalreihe (A, B, C, ...)
 * number = Spaltennummer (1, 2, 3, ...)
 *
 * ⚠️  WICHTIG: Dieses Mapping muss zu deinem Regal-Layout passen!
 *     Ändere die Einträge entsprechend deiner tatsächlichen Anordnung.
 */

struct PositionEntry {
    const char *letter;     // Regalreihe (z.B. "A", "B")
    int         number;     // Spalte (z.B. 1, 2, 3, ...)
    const char *shelf;      // Fach (z.B. "0", "1", "2", oder "" für Hauptfach)
    int         ledIndex;   // Index auf dem LED-Streifen (0-basiert)
};

// ═══════════════════════════════════════════════════════════════════════════════════
//  BEISPIEL-Mapping für ein Regal (A-D, 1-5, 0 Fächer)
//  Passe dies an dein tatsächliches Regal an!
// ═══════════════════════════════════════════════════════════════════════════════════
const PositionEntry POSITION_MAP[] = {
    // ─── Regalreihe A ───
    {"A", 1, "",  0},
    {"A", 2, "",  1},
    {"A", 3, "",  2},
    {"A", 4, "",  3},
    {"A", 5, "",  4},
    // ─── Regalreihe B ───
    {"B", 1, "",  5},
    {"B", 2, "",  6},
    {"B", 3, "",  7},
    {"B", 4, "",  8},
    {"B", 5, "",  9},
    // ─── Regalreihe C ───
    {"C", 1, "", 10},
    {"C", 2, "", 11},
    {"C", 3, "", 12},
    {"C", 4, "", 13},
    {"C", 5, "", 14},
    // ─── Regalreihe D ───
    {"D", 1, "", 15},
    {"D", 2, "", 16},
    {"D", 3, "", 17},
    {"D", 4, "", 18},
    {"D", 5, "", 19},
};

// Anzahl der Einträge automatisch ermitteln
const size_t POSITION_COUNT = sizeof(POSITION_MAP) / sizeof(POSITION_MAP[0]);

#endif // POSITION_MAP_H

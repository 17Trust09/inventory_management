#ifndef POSITION_MAP_H
#define POSITION_MAP_H

/*
 * POSITION_MAP: Übersetzt eine StorageLocation-ID (location_id)
 * in einen LED-Index auf dem WS2812B-Streifen.
 *
 * Jede Schublade/jeder Lagerort bekommt GENAU EINE LED.
 * Das Mapping ist 1:1: location_id → LED-Index.
 *
 * So ermittelst du die location_id:
 *   1. In der Django-App: Admin → Lagerorte
 *   2. Dort siehst du die ID jeder StorageLocation
 *   3. Oder: Rufe /api/marked-items/ auf → "location_id" im JSON
 *
 * Beispiel für ein Regal mit 20 Schubladen:
 *   Schublade ID 1  → LED #0
 *   Schublade ID 2  → LED #1
 *   ...
 *   Schublade ID 20 → LED #19
 *
 * ⚠️  WICHTIG: location_id ≠ LED-Index!
 *     Du musst die IDs deiner Lagerorte hier eintragen.
 */

struct PositionEntry {
    int  locationId;   // ID des StorageLocation (aus der Django-DB)
    int  ledIndex;     // Index auf dem LED-Streifen (0-basiert)
};

// ═══════════════════════════════════════════════════════════════════════════════════
//  BEISPIEL-Mapping – Passe dies an DEINE StorageLocation-IDs an!
//
//  So findest du die IDs:
//    curl "http://192.168.178.69:18000/api/marked-items/?key=dein-key"
//    → Im JSON steht "location_id": 7 für jede Markierung
// ═══════════════════════════════════════════════════════════════════════════════════
const PositionEntry POSITION_MAP[] = {
    // {location_id, LED_Index}
    {1,  0},   // Schublade 1  → LED #0
    {2,  1},   // Schublade 2  → LED #1
    {3,  2},   // Schublade 3  → LED #2
    {4,  3},   // Schublade 4  → LED #3
    {5,  4},   // Schublade 5  → LED #4
    {6,  5},   // Schublade 6  → LED #5
    {7,  6},   // Schublade 7  → LED #6
    {8,  7},   // Schublade 8  → LED #7
    {9,  8},   // Schublade 9  → LED #8
    {10, 9},   // Schublade 10 → LED #9
};

// Anzahl der Einträge automatisch ermitteln
const size_t POSITION_COUNT = sizeof(POSITION_MAP) / sizeof(POSITION_MAP[0]);

#endif // POSITION_MAP_H

#ifndef POSITION_MAP_H
#define POSITION_MAP_H

/*
 * POSITION_MAP: Übersetzt eine StorageLocation-ID (location_id)
 * in einen oder mehrere LED-Indizes auf dem WS2812B-Streifen.
 *
 * Jeder Lagerort kann 1, 2, 3 oder mehr LEDs bekommen,
 * um die Markierung optisch stärker hervorzuheben.
 *
 * Mapping: location_id → ledStart (erste LED) + ledCount (Anzahl)
 *
 * So ermittelst du die location_id:
 *   1. In der Django-App: Admin → Lagerorte
 *   2. Dort siehst du die ID jeder StorageLocation
 *   3. Oder: Rufe /api/marked-items/ auf → "location_id" im JSON
 *
 * Beispiel für ein Regal mit Schubladen (3 LEDs pro Schublade):
 *   Schublade ID 1  → LEDs 0,1,2
 *   Schublade ID 2  → LEDs 3,4,5
 *   ...
 *
 * ⚠️  WICHTIG: location_id ≠ LED-Index!
 *     Du musst die IDs deiner Lagerorte hier eintragen.
 *     Achte darauf, dass sich die LED-Bereiche nicht überschneiden!
 */

struct PositionEntry {
    int  locationId;   // ID des StorageLocation (aus der Django-DB)
    int  ledStart;     // Erster LED-Index (0-basiert)
    int  ledCount;     // Anzahl LEDs für diesen Lagerort (1 = eine LED, 3 = drei nebeneinander)
};

// ═══════════════════════════════════════════════════════════════════════════════════
//  BEISPIEL-Mapping – Passe dies an DEINE StorageLocation-IDs an!
//
//  So findest du die IDs:
//    curl "http://192.168.178.69:18000/api/marked-items/?key=dein-key"
//    → Im JSON steht "location_id": 7 für jede Markierung
// ═══════════════════════════════════════════════════════════════════════════════════
const PositionEntry POSITION_MAP[] = {
    // {location_id, ledStart, ledCount}
    {1,  0,  3},   // Schublade 1  → LEDs 0,1,2
    {2,  3,  3},   // Schublade 2  → LEDs 3,4,5
    {3,  6,  1},   // Schublade 3  → LED  6
    {4,  7,  1},   // Schublade 4  → LED  7
    {5,  8,  1},   // Schublade 5  → LED  8
    {6,  9,  1},   // Schublade 6  → LED  9
    {7,  10, 1},   // Schublade 7  → LED 10
    {8,  11, 1},   // Schublade 8  → LED 11
    {9,  12, 1},   // Schublade 9  → LED 12
    {10, 13, 1},   // Schublade 10 → LED 13
};

// Anzahl der Einträge automatisch ermitteln
const size_t POSITION_COUNT = sizeof(POSITION_MAP) / sizeof(POSITION_MAP[0]);

#endif // POSITION_MAP_H

PATCH_NOTES = [
    {
        "version": "1.0.1",
        "date": "2026-01-18",
        "title": "Bestand per Plus/Minus im Dashboard",
        "changes": [
            "Schnellanpassung der Bestände im Dashboard per Plus/Minus-Buttons ergänzt.",
            "Dashboard-Option für Schnellbestand aktiviert/deaktiviert.",
        ],
    },
    {
        "version": "1.0.0",
        "date": "2024-03-21",
        "title": "Patch-Notes eingeführt",
        "changes": [
            "Neue Patch-Notes-Seite mit Versionsübersicht erstellt.",
            "Struktur für zukünftige Einträge vorbereitet.",
        ],
    },
]

CURRENT_VERSION = PATCH_NOTES[0]["version"] if PATCH_NOTES else "unbekannt"

# Hinweis: Der neueste Eintrag muss immer oben stehen.
# Bei Änderungen bitte INVENTORY_VERSION in settings.py und diese Liste aktualisieren.

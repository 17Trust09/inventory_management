PATCH_NOTES = [
    {
        "version": "1.0.5",
        "date": "2026-02-10",
        "title": "Hotspots & geplante Exporte",
        "changes": [
            "Hotspot-Übersicht für Lagerbewegungen ergänzt (Top-Items & Lagerorte).",
            "Geplante Exporte mit Download-Übersicht und manuellem Ausführen hinzugefügt.",
        ],
    },
    {
        "version": "1.0.4",
        "date": "2026-02-10",
        "title": "Historie erweitert & Export-Optionen",
        "changes": [
            "Historie/Timeline mit Filtern für Aktion, Benutzer und Zeitraum ergänzt.",
            "Delta-Anzeige für Bestandsänderungen sowie Rollback-Bestätigung hinzugefügt.",
            "Export-Dialog mit Spaltenauswahl und neue Lagerbewegungs-Übersicht ergänzt.",
        ],
    },
    {
        "version": "1.0.3",
        "date": "2026-02-10",
        "title": "Historie, Rollback & Exporte gestartet",
        "changes": [
            "Timeline/Historie für Artikel ergänzt (inkl. Lagerbewegungen).",
            "Rollback-Funktion für Admins vorbereitet.",
            "CSV/Excel-Export im Overview-Dashboard hinzugefügt.",
        ],
    },
    {
        "version": "1.0.2",
        "date": "2026-01-25",
        "title": "Dashboard ohne Reload bei Plus/Minus",
        "changes": [
            "Bestands-Plus/Minus aktualisiert den Wert jetzt ohne kompletten Seiten-Reload.",
            "Fallback bleibt erhalten, falls der Browser kein AJAX unterstützt.",
        ],
    },
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

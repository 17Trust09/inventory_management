from barcode import Code128
from barcode.writer import ImageWriter
import os


def generate_barcode_text(item_id):
    """Generiert den Barcode-Text basierend auf der Item-ID."""
    barcode = Code128(str(item_id), writer=ImageWriter())
    return barcode  # Gibt den Barcode-Text zurück


def generate_barcode_image(self):
    """Generiert ein Barcode-Bild basierend auf dem Barcode-Text und speichert es als Datei."""
    if not self.barcode:
        print("Kein Barcode gefunden!")  # Debugging-Ausgabe
        return

    if not os.path.exists('barcodes'):
        os.makedirs('barcodes')

    try:
        barcode = Code128(self.barcode, writer=ImageWriter())
        barcode.save(f'barcodes/barcode_{self.barcode}')
        print(f"Barcode-Bild wurde erfolgreich erstellt für {self.barcode}")  # Debugging-Ausgabe
    except Exception as e:
        print(f"Fehler bei der Barcode-Generierung: {e}")  # Debugging-Ausgabe
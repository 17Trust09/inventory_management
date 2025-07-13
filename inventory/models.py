from django.db import models
from django.contrib.auth.models import User
from barcode import Code128
from barcode.writer import ImageWriter
import os
import uuid


class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")  # Beschreibung für genauere Suche
    quantity = models.IntegerField()
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location_letter = models.CharField(max_length=1, verbose_name="Schrank", null=True, blank=True)
    location_number = models.IntegerField(verbose_name="Schublade", null=True, blank=True)
    location_shelf = models.CharField(max_length=50, verbose_name="Fach", null=True, blank=True)  # Neues Feld
    low_quantity = models.IntegerField(default=3, verbose_name="Mindestbestand")
    order_link = models.URLField(max_length=500, null=True, blank=True, verbose_name="Bestell-Link")
    barcode = models.CharField(max_length=50, unique=True, blank=True)
    barcode_text = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  # Neues Feld für Aktivstatus

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generiere den Barcode nur, wenn er nicht vorhanden ist
        if not self.barcode:
            self.barcode = str(uuid.uuid4())[:12]  # Barcode auf 12 Zeichen kürzen
            while InventoryItem.objects.filter(barcode=self.barcode).exists():
                self.barcode = str(uuid.uuid4())[:12]  # Generiere einen neuen Barcode, falls der existiert

        self.barcode_text = f"Barcode für {self.name}: {self.barcode}"

        # Aufruf der übergeordneten save-Methode, um den Artikel zu speichern
        super().save(*args, **kwargs)

        # Überprüfe, ob der Barcode korrekt ist, bevor du das Bild generierst
        if self.barcode:
            self.generate_barcode_image()
            self.save_barcode_text_to_file()
        else:
            print(f"Barcode konnte nicht generiert werden für {self.name}")  # Debugging-Ausgabe

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

    def save_barcode_text_to_file(self):
        """Speichert den Barcode-Text in einer Textdatei."""
        if not os.path.exists('barcodes'):
            os.makedirs('barcodes')
        with open(f'barcodes/barcode_{self.id}.txt', 'w') as file:
            file.write(self.barcode_text)

    @staticmethod
    def get_similar_items(item_name):
        """Suche nach Artikeln mit ähnlichem Namen oder Beschreibung."""
        return InventoryItem.objects.filter(
            models.Q(name__icontains=item_name) |
            models.Q(description__icontains=item_name)
        ).exclude(name=item_name)  # Verhindert, dass der aktuelle Artikel gefunden wird


class Category(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

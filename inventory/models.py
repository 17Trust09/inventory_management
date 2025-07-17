from django.db import models
from django.contrib.auth.models import User
from barcode import Code128
from barcode.writer import ImageWriter
import os
import uuid


# Anwendungstag-Modell
class ApplicationTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# Benutzerprofil mit zugewiesenen Anwendungstags
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tags = models.ManyToManyField(ApplicationTag, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


# Hauptmodell für Inventar
class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")  # Beschreibung für genauere Suche
    quantity = models.IntegerField()
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location_letter = models.CharField(max_length=1, verbose_name="Schrank", null=True, blank=True)
    location_number = models.IntegerField(verbose_name="Schublade", null=True, blank=True)
    location_shelf = models.CharField(max_length=50, verbose_name="Fach", null=True, blank=True)
    low_quantity = models.IntegerField(default=3, verbose_name="Mindestbestand")
    order_link = models.URLField(max_length=500, null=True, blank=True, verbose_name="Bestell-Link")
    barcode = models.CharField(max_length=50, unique=True, blank=True)
    barcode_text = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    application_tags = models.ManyToManyField(ApplicationTag, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = str(uuid.uuid4())[:12]
            while InventoryItem.objects.filter(barcode=self.barcode).exists():
                self.barcode = str(uuid.uuid4())[:12]

        self.barcode_text = f"Barcode für {self.name}: {self.barcode}"
        super().save(*args, **kwargs)

        if self.barcode:
            self.generate_barcode_image()
            self.save_barcode_text_to_file()
        else:
            print(f"Barcode konnte nicht generiert werden für {self.name}")

    def generate_barcode_image(self):
        if not self.barcode:
            print("Kein Barcode gefunden!")
            return

        if not os.path.exists('barcodes'):
            os.makedirs('barcodes')

        try:
            barcode = Code128(self.barcode, writer=ImageWriter())
            barcode.save(f'barcodes/barcode_{self.barcode}')
            print(f"Barcode-Bild wurde erfolgreich erstellt für {self.barcode}")
        except Exception as e:
            print(f"Fehler bei der Barcode-Generierung: {e}")

    def save_barcode_text_to_file(self):
        if not os.path.exists('barcodes'):
            os.makedirs('barcodes')
        with open(f'barcodes/barcode_{self.id}.txt', 'w') as file:
            file.write(self.barcode_text)

    @staticmethod
    def get_similar_items(item_name):
        return InventoryItem.objects.filter(
            models.Q(name__icontains=item_name) |
            models.Q(description__icontains=item_name)
        ).exclude(name=item_name)


# Kategorie-Modell (unverändert)
class Category(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

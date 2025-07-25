from django.db import models
from django.contrib.auth.models import User
from barcode import Code128
from barcode.writer import ImageWriter
import os
import uuid
import qrcode
from django.conf import settings
from PIL import Image


class ApplicationTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tags = models.ManyToManyField(ApplicationTag, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class GlobalSettings(models.Model):
    qr_base_url = models.CharField(
        max_length=200,
        default='http://127.0.0.1:8000',
        help_text='Basis-URL für QR-Code-Links, z. B. http://192.168.178.20:8000'
    )

    def __str__(self):
        return "Globale Einstellungen"

    class Meta:
        verbose_name = "Globale Einstellung"
        verbose_name_plural = "Globale Einstellungen"


class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")
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

    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    maintenance_date = models.DateField(blank=True, null=True, verbose_name="Wartungs-/Ablaufdatum")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        regenerate_qr = False

        if not self.barcode:
            self.barcode = str(uuid.uuid4())[:12]
            while InventoryItem.objects.filter(barcode=self.barcode).exists():
                self.barcode = str(uuid.uuid4())[:12]

        self.barcode_text = f"Barcode für {self.name}: {self.barcode}"

        if not is_new:
            old = InventoryItem.objects.get(pk=self.pk)
            if (old.name != self.name or
                old.location_letter != self.location_letter or
                old.location_number != self.location_number or
                old.location_shelf != self.location_shelf):
                regenerate_qr = True

        super().save(*args, **kwargs)

        if is_new or regenerate_qr or not os.path.exists(os.path.join(settings.MEDIA_ROOT, f'qrcodes/qr_{self.id}.jpg')):
            self.generate_barcode_image()
            self.save_barcode_text_to_file()
            self.generate_qr_code()

    def generate_barcode_image(self):
        if not self.barcode:
            print("Kein Barcode gefunden!")
            return

        path = os.path.join(settings.MEDIA_ROOT, 'barcodes')
        os.makedirs(path, exist_ok=True)

        try:
            barcode = Code128(self.barcode, writer=ImageWriter())
            barcode.save(os.path.join(path, f'barcode_{self.barcode}'))
            print(f"Barcode-Bild erstellt: {self.barcode}")
        except Exception as e:
            print(f"Fehler Barcode: {e}")

    def save_barcode_text_to_file(self):
        path = os.path.join(settings.MEDIA_ROOT, 'barcodes')
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f'barcode_{self.id}.txt'), 'w') as file:
            file.write(self.barcode_text)

    def generate_qr_code(self):
        try:
            from .models import GlobalSettings

            settings_instance = GlobalSettings.objects.first()
            base_url = settings_instance.qr_base_url if settings_instance else "http://127.0.0.1:8000"
            url = f"{base_url}/edit-item/{self.id}"

            qr = qrcode.make(url)
            path = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
            os.makedirs(path, exist_ok=True)
            full_path = os.path.join(path, f'qr_{self.id}.jpg')
            qr.save(full_path)
            print(f"QR-Code gespeichert: {full_path}")
        except Exception as e:
            print(f"Fehler bei QR-Code-Generierung: {e}")

    @staticmethod
    def get_similar_items(item_name):
        return InventoryItem.objects.filter(
            models.Q(name__icontains=item_name) |
            models.Q(description__icontains=item_name)
        ).exclude(name=item_name)


class Category(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


# Dummy-Modell für QR-Code-Übersicht im Admin
class QRCodeOverviewModel(models.Model):
    class Meta:
        verbose_name = "QR-Code Übersicht"
        verbose_name_plural = "QR-Code Übersicht"
        managed = False

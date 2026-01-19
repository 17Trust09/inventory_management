from datetime import date
import logging
import os
import uuid
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from django.utils import timezone
from barcode import Code128
from barcode.writer import ImageWriter
import qrcode
from django.db.models import JSONField

logger = logging.getLogger(__name__)


class TagType(models.Model):
    """
    Definiert, ob ein Tag zu Equipment oder Verbrauchsmaterial gehört.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Tag-Typ"
    )

    def __str__(self):
        return self.name


class ApplicationTag(models.Model):
    """
    Tags für Inventar-Items, jetzt mit Zuordnung zu einem TagType.
    Das Feld 'type' ist derzeit optional, um Migrationen ohne Default zu ermöglichen.
    """
    name = models.CharField(max_length=50, unique=True)
    type = models.ForeignKey(
        TagType,
        on_delete=models.CASCADE,
        related_name="tags",
        verbose_name="Typ",
        null=True,     # vorübergehend erlaubt NULL
        blank=True
    )

    def __str__(self):
        # Type kann None sein, daher Absicherung
        type_name = self.type.name if self.type else "–"
        return f"{self.name} ({type_name})"

    class Meta:
        indexes = [
            models.Index(fields=["type", "name"]),
        ]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Welche Dashboards (Overviews) dieser User sehen darf.
    # Leer bedeutet: KEIN Zugriff (es muss explizit angehakt werden).
    allowed_overviews = models.ManyToManyField(
        'Overview',
        blank=True,
        related_name='allowed_users',
        help_text="Leer lassen = kein Zugriff auf Dashboards (explizit auswählen)"
    )

    def __str__(self):
        return f"{self.user.username} Profile"


class GlobalSettings(models.Model):
    qr_base_url = models.CharField(
        max_length=200,
        default='http://127.0.0.1:8000',
        help_text='Basis-URL für QR-Code-Links, z. B. http://192.168.178.20:8000'
    )
    nfc_base_url_local = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Lokale Basis-URL für NFC-Links, z. B. http://192.168.178.20:8000",
    )
    nfc_base_url_remote = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Remote/Tailscale Basis-URL für NFC-Links, z. B. https://host.tailnet-xyz.ts.net",
    )
    show_patch_notes = models.BooleanField(
        default=True,
        verbose_name="Patch Notes anzeigen",
    )
    show_feedback = models.BooleanField(
        default=True,
        verbose_name="Feedback-Board anzeigen",
    )
    show_movement_report = models.BooleanField(
        default=True,
        verbose_name="Lagerbewegungen anzeigen",
    )
    show_admin_history = models.BooleanField(
        default=True,
        verbose_name="Admin-Historie & Rollback anzeigen",
    )
    show_scheduled_exports = models.BooleanField(
        default=True,
        verbose_name="Geplante Exporte anzeigen",
    )

    def __str__(self):
        return "Globale Einstellungen"

    class Meta:
        verbose_name = "Globale Einstellung"
        verbose_name_plural = "Globale Einstellungen"


class InventoryItem(models.Model):
    NFC_BASE_CHOICES = (
        ("local", "Lokal"),
        ("remote", "Tailscale/Remote"),
    )
    ITEM_TYPES = (
        ("equipment", "Equipment"),
        ("consumable", "Verbrauchsmaterial"),
    )

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPES,
        default="equipment",
        verbose_name="Art des Artikels",
        db_index=True,
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, verbose_name="Beschreibung")
    quantity = models.IntegerField(verbose_name="Ist-Bestand", db_index=True)

    category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    # 🔑 NEU: harte Zuordnung zu GENAU EINEM Dashboard
    overview = models.ForeignKey(
        "Overview",
        on_delete=models.CASCADE,
        related_name="items",
        null=True,   # nur für Migration
        blank=True
    )

    is_favorite = models.BooleanField(default=False, verbose_name="Favorit")
    last_used = models.DateTimeField(blank=True, null=True, verbose_name="Letzte Nutzung", db_index=True)

    low_quantity = models.IntegerField(default=3, verbose_name="Grundpuffer", db_index=True)

    order_link = models.URLField(max_length=500, blank=True, null=True, verbose_name="Bestell-Link")

    barcode = models.CharField(max_length=50, unique=True, blank=True)
    barcode_text = models.TextField(blank=True, null=True)
    nfc_token = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="NFC-Tag Token",
        help_text="Token für NFC-Tags (wird automatisch erzeugt, wenn leer).",
    )
    nfc_base_choice = models.CharField(
        max_length=12,
        choices=NFC_BASE_CHOICES,
        default="local",
        verbose_name="NFC-Basis",
        help_text="Welche Basis-URL für NFC-Links verwendet werden soll.",
    )

    location_letter = models.CharField(max_length=1, null=True, blank=True, db_index=True)
    location_number = models.IntegerField(null=True, blank=True, db_index=True)
    location_shelf = models.CharField(max_length=50, null=True, blank=True)

    storage_location = models.ForeignKey(
        "StorageLocation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items"
    )

    maintenance_date = models.DateField(blank=True, null=True, db_index=True)

    image = models.ImageField(upload_to="item_images/", blank=True, null=True)

    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application_tags = models.ManyToManyField(ApplicationTag, blank=True)

    def __str__(self):
        return self.name



    # ---------- NEU: QR-Helfer (Eigenschaften) ----------
    @property
    def qr_file_path(self) -> str:
        """Absoluter Dateipfad des QR-Codes."""
        return os.path.join(settings.MEDIA_ROOT, 'qrcodes', f'qr_{self.id}.jpg') if self.id else ""

    @property
    def qr_url(self) -> str:
        """Öffentliche URL des QR-Codes (für Templates/Download)."""
        if not self.id:
            return ""
        # MEDIA_URL endet i. d. R. mit '/', daher bewusst ohne extra Slash hier
        return f"{settings.MEDIA_URL}qrcodes/qr_{self.id}.jpg"

    @property
    def qr_exists(self) -> bool:
        """True, wenn die QR-Code-Datei existiert."""
        try:
            return bool(self.id and os.path.exists(self.qr_file_path))
        except Exception:
            return False
    # ---------- Ende NEU ----------

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        regenerate_qr = False

        if not self.barcode:
            self.barcode = str(uuid.uuid4())[:12]
            while InventoryItem.objects.filter(barcode=self.barcode).exists():
                self.barcode = str(uuid.uuid4())[:12]

        self.barcode_text = f"Barcode für {self.name}: {self.barcode}"

        if not self.nfc_token:
            self.nfc_token = uuid.uuid4().hex[:16]
            while InventoryItem.objects.filter(nfc_token=self.nfc_token).exists():
                self.nfc_token = uuid.uuid4().hex[:16]

        if not is_new:
            old = InventoryItem.objects.get(pk=self.pk)
            if (old.name != self.name or
                old.location_letter != self.location_letter or
                old.location_number != self.location_number or
                old.location_shelf != self.location_shelf):
                regenerate_qr = True

        super().save(*args, **kwargs)

        qr_path = self.qr_file_path  # ← nutzt die neue Property
        if is_new or regenerate_qr or not os.path.exists(qr_path):
            self.generate_barcode_image()
            self.save_barcode_text_to_file()
            self.generate_qr_code()

    def generate_barcode_image(self):
        if not self.barcode:
            return
        path = os.path.join(settings.MEDIA_ROOT, 'barcodes')
        os.makedirs(path, exist_ok=True)
        try:
            barcode = Code128(self.barcode, writer=ImageWriter())
            barcode.save(os.path.join(path, f'barcode_{self.barcode}'))
        except Exception:
            logger.exception("Fehler Barcode-Erzeugung für Item %s", self.id)

    def save_barcode_text_to_file(self):
        path = os.path.join(settings.MEDIA_ROOT, 'barcodes')
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, f'barcode_{self.id}.txt'), 'w') as file:
            file.write(self.barcode_text)

    def generate_qr_code(self):
        try:
            base = (
                GlobalSettings.objects.first().qr_base_url
                if GlobalSettings.objects.exists()
                else settings.INVENTORY_BASE_URL
            )
            url = f"{base}/edit-item/{self.id}"
            qr = qrcode.make(url)
            path = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
            os.makedirs(path, exist_ok=True)
            # ↓ nutzt den standardisierten Dateinamen
            qr.save(self.qr_file_path)
        except Exception:
            logger.exception("Fehler bei QR-Code-Generierung für Item %s", self.id)

    @property
    def verliehen(self):
        return (self.borrowings
                .filter(returned=False)
                .aggregate(total=models.Sum("quantity_borrowed"))
               )["total"] or 0

    @property
    def borrowed_quantity(self):
        return self.verliehen

    @property
    def calculated_target_quantity(self):
        return self.quantity + self.borrowed_quantity

    @property
    def dynamischer_mindestbestand(self):
        return self.low_quantity if self.item_type == 'consumable' else 0

    @property
    def muss_bestellt_werden(self):
        return self.quantity < self.dynamischer_mindestbestand

    @property
    def is_expired(self):
        """True, wenn maintenance_date in der Vergangenheit liegt."""
        return bool(self.maintenance_date and self.maintenance_date < date.today())

    @staticmethod
    def get_similar_items(item_name):
        return InventoryItem.objects.filter(
            models.Q(name__icontains=item_name) |
            models.Q(description__icontains=item_name)
        ).exclude(name=item_name)

    class Meta:
        indexes = [
            # Häufige Filter-/Sortierkombinationen
            models.Index(fields=["item_type", "is_active"]),
            models.Index(fields=["item_type", "category"]),
            models.Index(fields=["location_letter", "location_number"]),
            models.Index(fields=["date_created"]),
        ]


class InventoryHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Erstellt"
        UPDATED = "updated", "Geändert"
        MOVEMENT = "movement", "Lagerbewegung"
        QUANTITY = "quantity_adjusted", "Bestand angepasst"
        BORROWED = "borrowed", "Ausgeliehen"
        RETURNED = "returned", "Zurückgegeben"
        ROLLBACK = "rollback", "Rollback"

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="history_entries",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_history_entries",
    )
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    changes = models.JSONField(default=list, blank=True)
    data_before = models.JSONField(default=dict, blank=True)
    data_after = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Inventar-Historie"
        verbose_name_plural = "Inventar-Historie"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.item.name} – {self.get_action_display()} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def can_rollback(self) -> bool:
        return bool(self.data_before)


class ScheduledExport(models.Model):
    class Format(models.TextChoices):
        CSV = "csv", "CSV"
        EXCEL = "excel", "Excel (TSV)"

    class Frequency(models.TextChoices):
        DAILY = "daily", "Täglich"
        WEEKLY = "weekly", "Wöchentlich"
        MONTHLY = "monthly", "Monatlich"

    overview = models.ForeignKey(
        "Overview",
        on_delete=models.CASCADE,
        related_name="scheduled_exports",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_exports",
    )
    export_format = models.CharField(max_length=12, choices=Format.choices, default=Format.CSV)
    frequency = models.CharField(max_length=12, choices=Frequency.choices, default=Frequency.WEEKLY)
    columns = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Geplanter Export"
        verbose_name_plural = "Geplante Exporte"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export {self.overview.name} ({self.get_frequency_display()})"


class ExportRun(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Erfolgreich"
        FAILED = "failed", "Fehlgeschlagen"

    scheduled_export = models.ForeignKey(
        ScheduledExport,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(max_length=12, choices=Status.choices, db_index=True)
    file_path = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Export-Lauf"
        verbose_name_plural = "Export-Läufe"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export #{self.id} ({self.get_status_display()})"


class Category(models.Model):
    """
    Globale Kategorien – KEINE Unterscheidung mehr nach Equipment/Verbrauchsmaterial.
    """
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Kategorie"
        verbose_name_plural = "Kategorien"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class QRCodeOverviewModel(models.Model):
    class Meta:
        managed = False
        verbose_name = "QR-Code Übersicht"
        verbose_name_plural = "QR-Code Übersicht"


class BorrowedItem(models.Model):
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    borrower = models.CharField(
        max_length=200,
        verbose_name="Entleiher"
    )
    quantity_borrowed = models.PositiveIntegerField(
        verbose_name="Anzahl"
    )
    borrowed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ausgeliehen am",
        db_index=True  # 🔹 häufige Sortierung/Filter
    )
    returned = models.BooleanField(
        default=False,
        verbose_name="Zurückgegeben?",
        db_index=True  # 🔹 häufige Filterbedingung
    )
    returned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Zurückgegeben am",
        db_index=True
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Kommentar"
    )
    return_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Geplantes Rückgabedatum",
        db_index=True
    )

    def __str__(self):
        return f"{self.quantity_borrowed}x {self.item.name} an {self.borrower}"

    def return_item(self):
        if not self.returned:
            # Bestand zurück buchen
            self.item.quantity += self.quantity_borrowed
            # letzte Nutzung setzen
            self.item.last_used = timezone.now()
            self.item.save()

            self.returned = True
            self.returned_at = timezone.now()
            self.save()

    class Meta:
        indexes = [
            models.Index(fields=["item", "returned"]),
            models.Index(fields=["returned", "borrowed_at"]),
        ]


class Page(models.Model):
    """
    Repräsentiert eine Resource bzw. Seite im Admin-Frontend.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Menschlicher Name, z.B. 'Items Übersicht'"
    )
    url_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Der Name der URL in deinen admin_urls.py, z.B. 'admin_items'"
    )
    example_kwargs = JSONField(
        default=dict,
        blank=True,
        help_text="Beispiel-Parameter für reverse(), z.B. {'pk': 1}"
    )

    class Meta:
        verbose_name = "Seite"
        verbose_name_plural = "Seiten"
        permissions = [
            ("manage_permissions", "Kann Seiten-Berechtigungen verwalten"),
        ]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Pivot-Tabelle zwischen Django Group (Rolle) und Page mit erlaubter Ansicht.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=False)

    class Meta:
        unique_together = ('group', 'page')

    def __str__(self):
        return f"{self.group.name} -> {self.page.url_name}"


# --- Lagerorte Verwaltung --- #
class StorageLocation(models.Model):
    NFC_BASE_CHOICES = (
        ("local", "Lokal"),
        ("remote", "Tailscale/Remote"),
    )
    name = models.CharField(max_length=100, db_index=True)
    nfc_token = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="NFC-Tag Token",
        help_text="Token für NFC-Tags (wird automatisch erzeugt, wenn leer).",
    )
    nfc_base_choice = models.CharField(
        max_length=12,
        choices=NFC_BASE_CHOICES,
        default="local",
        verbose_name="NFC-Basis",
        help_text="Welche Basis-URL für NFC-Links verwendet werden soll.",
    )
    ha_entity_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional: Home-Assistant Entity-ID für LED/Schublade (z. B. light.drawer_a1)"
    )
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        related_name='children',
        on_delete=models.CASCADE
    )
    # …

    def __str__(self):
        return self.name

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name

    @property
    def level(self):
        lvl = 0
        node = self.parent
        while node:
            lvl += 1
            node = node.parent
        return lvl

    def save(self, *args, **kwargs):
        if not self.nfc_token:
            self.nfc_token = uuid.uuid4().hex[:16]
            while StorageLocation.objects.filter(nfc_token=self.nfc_token).exists():
                self.nfc_token = uuid.uuid4().hex[:16]
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["parent", "name"]),
        ]


# --- NEU: Modulares Dashboard/Overview --- #
class Overview(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    icon_emoji = models.CharField(max_length=16, blank=True, help_text="Emoji oder Icon (z. B. 🛠️)")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    visible_for_groups = models.ManyToManyField(Group, blank=True, help_text="Leer = für alle sichtbar.")
    categories = models.ManyToManyField('Category', blank=True, help_text="Optional: Filter auf Kategorien.")

    show_quantity = models.BooleanField(default=True, verbose_name="Mengen anzeigen")
    has_locations = models.BooleanField(default=True, verbose_name="Lagerorte verwenden")
    has_min_stock = models.BooleanField(default=False, verbose_name="Mindestbestand verwenden")
    enable_borrow = models.BooleanField(default=False, verbose_name="Verleih/Return verwenden")
    is_consumable_mode = models.BooleanField(default=False, verbose_name="Verbrauchsmaterial-Logik")
    require_qr = models.BooleanField(default=False, verbose_name="QR/Barcode Pflicht")
    enable_quick_adjust = models.BooleanField(default=False, verbose_name="Schnellbestand +/- erlauben")

    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("overview-dashboard", kwargs={"slug": self.slug})

    def features(self):
        return {
            "show_quantity": self.show_quantity,
            "has_locations": self.has_locations,
            "has_min_stock": self.has_min_stock,
            "enable_borrow": self.enable_borrow,
            "is_consumable_mode": self.is_consumable_mode,
            "require_qr": self.require_qr,
            "enable_quick_adjust": self.enable_quick_adjust,
        }


# -------------------------------------------------------------------
# NEU: Feedback-Modelle (lokales Feedback-Board mit Votes & Kommentaren)
# -------------------------------------------------------------------
class Feedback(models.Model):
    class Status(models.TextChoices):
        OFFEN = "open", "Offen"
        IN_ARBEIT = "in_progress", "In Bearbeitung"
        ERLEDIGT = "done", "Erledigt"

    title = models.CharField("Titel", max_length=200)
    description = models.TextField("Beschreibung", blank=True)
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.OFFEN,
        db_index=True,
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="feedback_created", verbose_name="Erstellt von"
    )
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="feedback_assigned", verbose_name="Zugewiesen an"
    )
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedback"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    @property
    def upvotes_count(self) -> int:
        return self.votes.filter(value=1).count()

    @property
    def downvotes_count(self) -> int:
        return self.votes.filter(value=-1).count()


class FeedbackVote(models.Model):
    """
    Eine Stimme pro Nutzer und Feedback (👍 = +1, 👎 = -1).
    """
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedback_votes")
    value = models.SmallIntegerField(choices=((1, "👍"), (-1, "👎")), verbose_name="Wert")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feedback-Stimme"
        verbose_name_plural = "Feedback-Stimmen"
        unique_together = (("feedback", "user"),)
        indexes = [
            models.Index(fields=["feedback", "user"]),
            models.Index(fields=["feedback", "value"]),
        ]

    def __str__(self):
        return f"Vote({self.value}) von {self.user} für {self.feedback_id}"


class FeedbackComment(models.Model):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="comments", verbose_name="Feedback")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedback_comments", verbose_name="Autor")
    text = models.TextField("Kommentar")
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Feedback-Kommentar"
        verbose_name_plural = "Feedback-Kommentare"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["feedback", "created_at"]),
        ]

    def __str__(self):
        return f"Kommentar von {self.author} zu #{self.feedback_id}"

class Cable(models.Model):
    code = models.CharField(max_length=50, unique=True)
    etage = models.CharField(max_length=10)
    raum = models.CharField(max_length=20)
    funktion = models.CharField(max_length=30)
    nummer = models.CharField(max_length=10)
    beschreibung = models.TextField(blank=True, null=True)
    sicherung = models.CharField(max_length=20, blank=True, null=True)
    ziel = models.CharField(max_length=100, blank=True, null=True)
    kabeltyp = models.CharField(max_length=50, blank=True, null=True)
    laenge = models.FloatField(blank=True, null=True)
    status = models.CharField(max_length=20, default="aktiv")
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    ha_link = models.URLField(blank=True, null=True)
    bemerkung = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

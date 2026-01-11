from django import forms
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import (
    Category,
    InventoryItem,
    ApplicationTag,
    BorrowedItem,
    StorageLocation,
    Feedback,
    FeedbackComment
)


# -----------------------------
# Helpers: sicher bei fehlenden Tabellen
# -----------------------------
def table_exists(model) -> bool:
    """
    Prüft sicher, ob die Tabelle für ein gegebenes Model existiert.
    Verhindert ProgrammingError/OperationalError bei DB-Zugriffen während Import/Checks.
    """
    try:
        table_name = model._meta.db_table
        with connection.cursor():
            return table_name in connection.introspection.table_names()
    except Exception:
        # Falls die DB-Verbindung noch nicht bereit ist oder introspection fehlschlägt.
        return False


def safe_all_tags():
    """
    Liefert sicher ein QuerySet für *alle* ApplicationTags (ohne TagType).
    Gibt bei fehlenden Tabellen ein leeres QuerySet zurück.
    """
    try:
        if not table_exists(ApplicationTag):
            return ApplicationTag.objects.none()
        return ApplicationTag.objects.all()
    except (OperationalError, ProgrammingError):
        return ApplicationTag.objects.none()
    except Exception:
        return ApplicationTag.objects.none()


# -----------------------------
# Custom Fields
# -----------------------------
class StorageLocationChoiceField(forms.ModelChoiceField):
    """
    Dropdown für Lagerorte:
    - zeigt den vollständigen Pfad (get_full_path)
    - ACHTUNG: Die tatsächlichen Choices werden in den Forms in __init__ gesetzt,
      damit sie nicht beim Import „einfrieren“.
    """
    def label_from_instance(self, obj):
        return obj.get_full_path()


class TagNameOnlyMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Zeigt bei Checkboxen nur den Tag-Namen."""
    def label_from_instance(self, obj):
        return obj.name


# -----------------------------
# Gemeinsame Hilfen für sichtbare/unsichtbare Tags
# -----------------------------
SYSTEM_TAG_FILTER = (Q(name='-') | Q(name__startswith='__ov::'))

def visible_tags_qs():
    """Nur sichtbare (nicht-systemische) Tags."""
    return ApplicationTag.objects.exclude(SYSTEM_TAG_FILTER).order_by('name')


# -----------------------------
# Forms
# -----------------------------
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-lg'})


class EquipmentItemForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'}),
        label="Kategorie*"
    )
    application_tags = TagNameOnlyMultipleChoiceField(
        label="Tags*",
        queryset=ApplicationTag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    storage_location = StorageLocationChoiceField(
        queryset=StorageLocation.objects.none(),   # ← wird in __init__ gesetzt
        required=False,
        empty_label="–",
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'}),
        label="Lagerort"
    )

    class Meta:
        model = InventoryItem
        fields = [
            'name', 'quantity', 'category', 'storage_location',
            'order_link', 'application_tags', 'image', 'maintenance_date',
        ]
        labels = {
            'name': 'Name*',
            'quantity': 'Ist-Bestand*',
            'storage_location': 'Lagerort',
            'order_link': 'Bestell-Link',
            'application_tags': 'Tags*',
            'image': 'Bild (optional)',
            'maintenance_date': 'Wartungs-/Ablaufdatum',
        }

    def __init__(self, *args, **kwargs):
        # user wird evtl. übergeben, aber nicht mehr verwendet
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Bootstrap-Klassen
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxSelectMultiple):
                css = f.widget.attrs.get('class', '')
                if 'form-control' not in css:
                    f.widget.attrs['class'] = (css + ' form-control form-control-lg').strip()

        # >>> NUR sichtbare Tags anzeigen (System-Tags ausblenden)
        self.fields['application_tags'].queryset = visible_tags_qs()

        # >>> NEU/ÄNDERUNG: Lagerorte dynamisch befüllen (nicht beim Import einfrieren)
        try:
            qs_all = StorageLocation.objects.all()
            # Für die Anzeige nach Pfad sortieren
            sorted_locs = sorted(qs_all, key=lambda loc: loc.get_full_path().lower())
            # QuerySet (Validierung) + Choices (Sortierung) setzen
            self.fields['storage_location'].queryset = qs_all
            choices = [('', '–')]
            choices.extend((loc.pk, loc.get_full_path()) for loc in sorted_locs)
            self.fields['storage_location'].choices = choices
        except Exception:
            # Fallback: nur leere Auswahl
            self.fields['storage_location'].queryset = StorageLocation.objects.none()
            self.fields['storage_location'].choices = [('', '–')]

    def clean_application_tags(self):
        tags = self.cleaned_data.get('application_tags')
        if not tags:
            raise forms.ValidationError("Du musst mindestens einen Tag auswählen.")
        return tags

    def save(self, commit=True):
        """
        Beim Editieren: bereits vorhandene System-Tags am Item NICHT verlieren,
        obwohl sie im Formular nicht sichtbar/auswählbar sind.
        """
        instance = super().save(commit=commit)

        # existierendes Objekt? -> System-Tags wieder hinzufügen
        if instance.pk:
            try:
                before = InventoryItem.objects.get(pk=instance.pk)
                system_tags = before.application_tags.filter(SYSTEM_TAG_FILTER)
                if system_tags.exists():
                    instance.application_tags.add(*system_tags)
            except InventoryItem.DoesNotExist:
                pass
        return instance


class ConsumableItemForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'}),
        label="Kategorie*"
    )
    low_quantity = forms.IntegerField(
        label="Mindestbestand*",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg'}),
        required=True
    )
    application_tags = TagNameOnlyMultipleChoiceField(
        label="Tags*",
        queryset=ApplicationTag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    storage_location = StorageLocationChoiceField(
        queryset=StorageLocation.objects.none(),   # ← wird in __init__ gesetzt
        required=False,
        empty_label="–",
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'}),
        label="Lagerort"
    )

    class Meta:
        model = InventoryItem
        fields = [
            'name', 'quantity', 'category', 'storage_location',
            'low_quantity', 'order_link', 'application_tags', 'image', 'maintenance_date',
        ]
        labels = {
            'name': 'Name*',
            'quantity': 'Ist-Bestand*',
            'storage_location': 'Lagerort',
            'low_quantity': 'Mindestbestand*',
            'order_link': 'Bestell-Link',
            'application_tags': 'Tags*',
            'image': 'Bild (optional)',
            'maintenance_date': 'Wartungs-/Ablaufdatum',
        }

    def __init__(self, *args, **kwargs):
        # user wird evtl. übergeben, aber nicht mehr verwendet
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxSelectMultiple):
                css = f.widget.attrs.get('class', '')
                if 'form-control' not in css:
                    f.widget.attrs['class'] = (css + ' form-control form-control-lg').strip()

        # >>> NUR sichtbare Tags anzeigen (System-Tags ausblenden)
        self.fields['application_tags'].queryset = visible_tags_qs()

        # >>> NEU/ÄNDERUNG: Lagerorte dynamisch befüllen (nicht beim Import einfrieren)
        try:
            qs_all = StorageLocation.objects.all()
            sorted_locs = sorted(qs_all, key=lambda loc: loc.get_full_path().lower())
            self.fields['storage_location'].queryset = qs_all
            choices = [('', '–')]
            choices.extend((loc.pk, loc.get_full_path()) for loc in sorted_locs)
            self.fields['storage_location'].choices = choices
        except Exception:
            self.fields['storage_location'].queryset = StorageLocation.objects.none()
            self.fields['storage_location'].choices = [('', '–')]

    def clean_low_quantity(self):
        low = self.cleaned_data.get('low_quantity')
        if low is None or low < 0:
            raise forms.ValidationError("Mindestbestand muss eine positive Zahl sein.")
        return low

    def clean_application_tags(self):
        tags = self.cleaned_data.get('application_tags')
        if not tags:
            raise forms.ValidationError("Du musst mindestens einen Tag auswählen.")
        return tags

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if instance.pk:
            try:
                before = InventoryItem.objects.get(pk=instance.pk)
                system_tags = before.application_tags.filter(SYSTEM_TAG_FILTER)
                if system_tags.exists():
                    instance.application_tags.add(*system_tags)
            except InventoryItem.DoesNotExist:
                pass
        return instance


class BorrowItemForm(forms.ModelForm):
    return_date = forms.DateField(
        required=False,
        label="Rückgabedatum (optional)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = BorrowedItem
        fields = ['borrower', 'quantity_borrowed', 'comment', 'return_date']
        labels = {
            'borrower': 'Entleiher*',
            'quantity_borrowed': 'Anzahl*',
            'comment': 'Kommentar (optional)',
        }

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item', None)
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            css = f.widget.attrs.get('class', '')
            if 'form-control' not in css:
                f.widget.attrs['class'] = (css + ' form-control').strip()

    def clean_quantity_borrowed(self):
        qty = self.cleaned_data.get('quantity_borrowed')
        if qty is None or qty <= 0:
            raise forms.ValidationError("Die Anzahl muss größer als 0 sein.")
        if self.item and qty > self.item.quantity:
            raise forms.ValidationError(f"Maximal verfügbare Menge: {self.item.quantity}")
        return qty


class FeedbackForm(forms.ModelForm):
    """
    Robuste ModelForm:
    - nimmt zunächst alle Felder,
    - zeigt aber standardmäßig nur title/description (falls vorhanden) sichtbar an.
    - alle anderen Felder werden versteckt und auf 'required = False' gesetzt,
      damit es keine Validierungsfehler gibt (created_by setzt die View).
    """
    class Meta:
        model = Feedback
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        visible_candidates = ["title", "beschreibung", "subject", "summary",
                              "description", "text", "body", "message"]
        # welche Felder tatsächlich existieren?
        visible = [n for n in visible_candidates if n in self.fields]

        # Fallback: wenn kein bekanntes Feld gefunden wurde, alles sichtbar lassen
        if not visible:
            return

        # alle außer den sichtbaren verstecken
        for name, field in list(self.fields.items()):
            if name not in visible:
                field.required = False
                field.widget = forms.HiddenInput()

        # nette Widgets
        for n in visible:
            f = self.fields[n]
            if isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({"class": "form-control", "rows": 5})
            else:
                f.widget.attrs.update({"class": "form-control"})


class FeedbackCommentForm(forms.ModelForm):
    """
    Robuste Comment-Form:
    - zeigt nur ein Textfeld (content/text/body/message/comment), je nachdem was existiert.
    - alle anderen Felder werden versteckt und 'required = False'.
    """
    class Meta:
        model = FeedbackComment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        text_candidates = ["content", "text", "body", "message", "comment"]
        visible = [n for n in text_candidates if n in self.fields]

        if not visible:
            return

        for name, field in list(self.fields.items()):
            if name not in visible:
                field.required = False
                field.widget = forms.HiddenInput()

        for n in visible:
            f = self.fields[n]
            f.widget = forms.Textarea(attrs={"class": "form-control", "rows": 4})

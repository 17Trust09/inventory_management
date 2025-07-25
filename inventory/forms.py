from django import forms
from .models import Category, InventoryItem, ApplicationTag
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control form-control-lg'
            })


class InventoryItemForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), initial=0)
    location_shelf = forms.CharField(
        max_length=100,
        required=False,
        label="Fach",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg'})
    )
    application_tags = forms.ModelMultipleChoiceField(
        queryset=ApplicationTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags"
    )

    class Meta:
        model = InventoryItem
        fields = [
            'name', 'quantity', 'category',
            'location_letter', 'location_number', 'location_shelf',
            'low_quantity', 'order_link', 'application_tags',
            'image', 'maintenance_date'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'form-control form-control-lg'})

        self.fields['order_link'].widget.attrs.update({
            'class': 'btn btn-primary btn-lg w-100'
        })

        # Tag-Filter nach Benutzerrechten
        if user and not user.is_superuser:
            profile = getattr(user, 'userprofile', None)
            if profile:
                self.fields['application_tags'].queryset = profile.tags.exclude(name="-")
            else:
                self.fields['application_tags'].queryset = ApplicationTag.objects.none()
        else:
            self.fields['application_tags'].queryset = ApplicationTag.objects.exclude(name="-")

    def clean_application_tags(self):
        tags = self.cleaned_data.get('application_tags')

        # Nur beim Erstellen erforderlich
        if not tags and self.instance.pk is None:
            raise forms.ValidationError("Du musst mindestens einen Tag auswählen.")

        return tags

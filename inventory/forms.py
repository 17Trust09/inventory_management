from django import forms
from .models import Category, InventoryItem
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
                'class': 'form-control form-control-lg'  # Große Eingabefelder
            })


class InventoryItemForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), initial=0)

    # Füge das Fach-Feld hinzu
    location_shelf = forms.CharField(max_length=100, required=False, label="Fach", widget=forms.TextInput(attrs={'class': 'form-control form-control-lg'}))

    class Meta:
        model = InventoryItem
        fields = ['name', 'quantity', 'category', 'location_letter', 'location_number', 'location_shelf', 'low_quantity', 'order_link']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control form-control-lg'  # Große Eingabefelder
            })

        self.fields['order_link'].widget.attrs.update({
            'class': 'btn btn-primary btn-lg w-100'  # Button für Touchscreen größer und responsiv
        })

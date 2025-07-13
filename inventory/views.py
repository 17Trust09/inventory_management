from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegisterForm, InventoryItemForm
from .models import InventoryItem, Category
from django.contrib import messages
from django.db import models
from django.db.models import Q
import requests  # Für die Kommunikation mit Home Assistant
from django.conf import settings  # Für das Laden von API-Token und URL aus den Django-Einstellungen
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import InventoryItem
from django.http import JsonResponse


# Index View (Landing Page)
class Index(TemplateView):
    template_name = 'inventory/index.html'

# Dashboard View (Anzeigen von Artikeln und Filterfunktionen)
class Dashboard(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('search')
        category_filter = request.GET.get('category')
        location_letter = request.GET.get('location_letter')  # Schubladenbezeichner aus der URL
        location_number = request.GET.get('location_number')  # Schubladenbezeichner aus der URL

        items = InventoryItem.objects.filter(user=request.user).order_by('id')

        if query:
            items = items.filter(
                Q(name__icontains=query) |
                Q(location_letter__icontains=query) |
                Q(location_number__icontains=query)
            )

        if category_filter and category_filter != "all":
            items = items.filter(category__id=category_filter)

        # Wenn Schublade angegeben, zeige nur Artikel aus dieser Schublade
        if location_letter and location_number:
            items = items.filter(location_letter=location_letter, location_number=location_number)

        low_inventory = items.filter(quantity__lte=models.F('low_quantity'))

        if low_inventory.exists():
            message = ', '.join([f'<a href="{reverse_lazy("edit-item", args=[item.id])}" style="color: black;">{item.name}</a> '
                                 f'(Mindestbestand: {item.low_quantity}, Aktueller Bestand: {item.quantity})'
                                 for item in low_inventory])
            messages.error(request, f'Artikel mit geringem Bestand: {message}', extra_tags='safe')

        categories = Category.objects.all()

        return render(request, 'inventory/dashboard.html', {
            'items': items,
            'categories': categories,
            'selected_category': category_filter,
            'low_inventory_ids': low_inventory.values_list('id', flat=True),
            'location_letter': location_letter,
            'location_number': location_number
        })

# Registrierung View
class SignUpView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, 'inventory/signup.html', {'form': form})

    def post(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1']
            )
            login(request, user)
            return redirect('index')
        return render(request, 'inventory/signup.html', {'form': form})

# Artikel hinzufügen View
class AddItem(CreateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

    def form_valid(self, form):
        # Hole den Namen des Artikels
        item_name = form.cleaned_data['name'].lower()

        # Suche nach ähnlichen Artikeln anhand des Namens oder der Beschreibung
        similar_items = InventoryItem.get_similar_items(item_name)

        if similar_items.exists():
            # Wenn ähnliche Artikel existieren, zeige eine Warnung
            messages.warning(self.request, "Meinst du eines dieser Items?")
            context = {
                'form': form,
                'categories': Category.objects.all(),
                'similar_items': similar_items  # Übergabe der ähnlichen Artikel
            }
            return render(self.request, 'inventory/item_form.html', context)

        # Wenn keine ähnlichen Artikel gefunden werden, Artikel speichern
        form.instance.user = self.request.user
        return super().form_valid(form)

# Artikel bearbeiten View
class EditItem(LoginRequiredMixin, UpdateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('dashboard')

# Artikel löschen View
class DeleteItem(LoginRequiredMixin, DeleteView):
    model = InventoryItem
    template_name = 'inventory/delete_item.html'
    success_url = reverse_lazy('dashboard')
    context_object_name = 'item'

# Barcode scannen View
class ScanBarcodeView(LoginRequiredMixin, View):
    def get(self, request):
        barcode = request.GET.get('barcode')
        if barcode:
            item = get_object_or_404(InventoryItem, barcode=barcode)
            return redirect('edit-item', pk=item.id)
        else:
            messages.error(request, "Kein Barcode übergeben.")
            return redirect('dashboard')

# Barcode Liste View
class BarcodeListView(LoginRequiredMixin, View):
    def get(self, request):
        items = InventoryItem.objects.filter(user=request.user)
        return render(request, 'inventory/barcode_list.html', {'items': items})

# Markieren View (Steuert die LED über Home Assistant)
class MarkItemAPI(View):
    def post(self, request, item_id):
        # Hole den Artikel aus der Datenbank
        item = get_object_or_404(InventoryItem, id=item_id)

        # An Home Assistant eine Anfrage senden, um die LED zu steuern
        ha_url = settings.HA_URL  # Lese die URL aus den Einstellungen
        headers = {
            'Authorization': f'Bearer {settings.HA_API_TOKEN}',  # API-Token aus den Django-Einstellungen
            'Content-Type': 'application/json'
        }
        payload = {
            "entity_id": "light.dummy_led"  # Ersetze mit deiner tatsächlichen LED-Entität
        }
        response = requests.post(ha_url, json=payload, headers=headers)

        if response.status_code == 200:
            messages.success(request, f"LED für {item.name} wurde eingeschaltet.")
        else:
            messages.error(request, "Fehler bei der Steuerung der LED.")
        return redirect('dashboard')


class DrawerItemsAPI(View):
    def get(self, request, location_letter, location_number):
        # Filtere die Artikel nach Standort und Aktivstatus
        items = InventoryItem.objects.filter(
            location_letter=location_letter,
            location_number=location_number,
            is_active = models.BooleanField(default=True)
        )

        items_list = [{"id": item.id, "name": item.name, "quantity": item.quantity} for item in items]

        return JsonResponse(items_list, safe=False)
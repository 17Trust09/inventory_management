from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegisterForm, InventoryItemForm
from .models import InventoryItem, Category, UserProfile
from django.contrib import messages
from django.db import models
from django.db.models import Q
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

# Index View (Landing Page)
class Index(TemplateView):
    template_name = 'inventory/index.html'


# Dashboard View (Artikel + Filter)
class Dashboard(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('search')
        category_filter = request.GET.get('category')
        tag_filter = request.GET.get('tag')
        location_letter = request.GET.get('location_letter')
        location_number = request.GET.get('location_number')

        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_tags = user_profile.tags.exclude(name="-")

        if not user_tags.exists():
            items = InventoryItem.objects.none()
        else:
            # Standardmäßig alle Items mit einem Tag des Nutzers
            items = InventoryItem.objects.filter(application_tags__in=user_tags)

            # Wenn ein spezieller Tagfilter gesetzt ist
            if tag_filter and tag_filter != "all":
                items = items.filter(application_tags__name=tag_filter)

            # Wenn "all" gewählt wurde, nochmal alle user_tags
            elif tag_filter == "all":
                items = InventoryItem.objects.filter(application_tags__in=user_tags)

        if query:
            items = items.filter(
                Q(name__icontains=query) |
                Q(location_letter__icontains=query) |
                Q(location_number__icontains=query)
            )

        if category_filter and category_filter != "all":
            items = items.filter(category__id=category_filter)

        if location_letter and location_number:
            items = items.filter(location_letter=location_letter, location_number=location_number)

        items = items.distinct().order_by('id')
        low_inventory = items.filter(quantity__lte=models.F('low_quantity'))

        if low_inventory.exists():
            message = ', '.join([
                f'<a href="{reverse_lazy("edit-item", args=[item.id])}" style="color: black;">{item.name}</a> '
                f'(Mindestbestand: {item.low_quantity}, Aktueller Bestand: {item.quantity})'
                for item in low_inventory
            ])
            messages.error(request, f'Artikel mit geringem Bestand: {message}', extra_tags='safe')

        categories = Category.objects.all()

        return render(request, 'inventory/dashboard.html', {
            'items': items,
            'categories': categories,
            'selected_category': category_filter,
            'low_inventory_ids': low_inventory.values_list('id', flat=True),
            'location_letter': location_letter,
            'location_number': location_number,
            'user_tags': user_tags,
            'selected_tag': tag_filter,
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Übergibt Benutzer für Tag-Filterung
        return kwargs

    def form_valid(self, form):
        item_name = form.cleaned_data['name'].lower()
        similar_items = InventoryItem.get_similar_items(item_name)

        if similar_items.exists():
            messages.warning(self.request, "Meinst du eines dieser Items?")
            context = {
                'form': form,
                'categories': Category.objects.all(),
                'similar_items': similar_items
            }
            return render(self.request, 'inventory/item_form.html', context)

        form.instance.user = self.request.user
        return super().form_valid(form)


# Artikel bearbeiten View
class EditItem(LoginRequiredMixin, UpdateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Übergibt Benutzer für Tag-Filterung
        return kwargs


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


# Markieren View (für Home Assistant LED)
class MarkItemAPI(View):
    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, id=item_id)

        ha_url = settings.HA_URL
        headers = {
            'Authorization': f'Bearer {settings.HA_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        payload = {
            "entity_id": "light.dummy_led"
        }
        response = requests.post(ha_url, json=payload, headers=headers)

        if response.status_code == 200:
            messages.success(request, f"LED für {item.name} wurde eingeschaltet.")
        else:
            messages.error(request, "Fehler bei der Steuerung der LED.")
        return redirect('dashboard')


# API für Items in einer Schublade
class DrawerItemsAPI(View):
    def get(self, request, location_letter, location_number):
        items = InventoryItem.objects.filter(
            location_letter=location_letter,
            location_number=location_number,
            is_active=True
        )
        items_list = [{"id": item.id, "name": item.name, "quantity": item.quantity} for item in items]
        return JsonResponse(items_list, safe=False)

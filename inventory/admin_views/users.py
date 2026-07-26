"""
Admin-User: Profile, Aktivieren/Deaktivieren, Löschen.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest

from ..models import UserProfile, Overview, InventoryItem
from .helpers import staff_required, StaffRequiredMixin


def _ensure_profile(user: User) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@staff_required
def admin_userprofile_edit(request, pk):
    profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
    edit_user = profile.user

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_overviews":
            ids = request.POST.getlist("allowed_overviews")
            profile.allowed_overviews.set(Overview.objects.filter(pk__in=ids))
            profile.save()
            messages.success(request, "Zugriff auf Dashboards gespeichert.")
            return redirect("admin_userprofile_edit", pk=pk)
        if action == "save_role":
            desired = (request.POST.get("role") or "").lower()
            if edit_user.is_superuser:
                messages.info(request, "Die Rolle eines Superusers kann hier nicht geändert werden.")
                return redirect("admin_userprofile_edit", pk=pk)
            if desired not in {"admin", "user"}:
                messages.error(request, "Ungültige Rollenangabe.")
                return redirect("admin_userprofile_edit", pk=pk)
            edit_user.is_staff = (desired == "admin")
            edit_user.save(update_fields=["is_staff"])
            messages.success(request, f"Rolle gespeichert: „{edit_user.username}“ ist jetzt {'Admin' if edit_user.is_staff else 'User'}.")
            return redirect("admin_userprofile_edit", pk=pk)
        if action == "deactivate":
            edit_user.is_active = False
            edit_user.save(update_fields=["is_active"])
            messages.success(request, f"Benutzer „{edit_user.username}“ wurde deaktiviert.")
            return redirect("admin_userprofile_edit", pk=pk)
        if action == "reactivate":
            edit_user.is_active = True
            edit_user.save(update_fields=["is_active"])
            messages.success(request, f"Benutzer „{edit_user.username}“ wurde reaktiviert.")
            return redirect("admin_userprofile_edit", pk=pk)
        if action == "delete":
            items_count = InventoryItem.objects.filter(user=edit_user).count()
            if items_count > 0:
                messages.error(request, "Löschen nicht möglich: Dem Benutzer sind noch Artikel zugeordnet. Bitte vorher übertragen oder löschen.")
                return redirect("admin_userprofile_edit", pk=pk)
            username = edit_user.username
            edit_user.delete()
            messages.success(request, f"Benutzer „{username}“ wurde gelöscht.")
            return redirect("admin_user_profiles")
        if action == "transfer_and_delete":
            target_id = request.POST.get("transfer_to")
            try:
                target = User.objects.get(pk=target_id)
            except User.DoesNotExist:
                messages.error(request, "Zielbenutzer nicht gefunden.")
                return redirect("admin_userprofile_edit", pk=pk)
            if target.pk == edit_user.pk:
                messages.error(request, "Zielbenutzer darf nicht identisch mit dem Quellbenutzer sein.")
                return redirect("admin_userprofile_edit", pk=pk)
            moved = InventoryItem.objects.filter(user=edit_user).update(user=target)
            username = edit_user.username
            edit_user.delete()
            messages.success(request, f"{moved} Artikel übertragen. Benutzer „{username}“ wurde gelöscht.")
            return redirect("admin_user_profiles")
        messages.error(request, "Unbekannte Aktion.")
        return redirect("admin_userprofile_edit", pk=pk)

    all_overviews = Overview.objects.all().order_by("order", "name")
    current_ids = set(profile.allowed_overviews.values_list("id", flat=True))
    items_count = InventoryItem.objects.filter(user=edit_user).count()
    other_users = User.objects.exclude(pk=edit_user.pk).order_by("username")

    return render(request, "inventory/admin_userprofiles_edit.html", {
        "profile": profile,
        "edit_user": edit_user,
        "all_overviews": all_overviews,
        "current_ids": current_ids,
        "items_count": items_count,
        "other_users": other_users,
    })


@staff_required
def admin_user_toggle_active(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("Nur POST erlaubt.")
    profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
    user = profile.user
    if request.user.id == user.id and request.POST.get("active") == "0":
        messages.error(request, "Du kannst dein eigenes Konto nicht deaktivieren.")
        return redirect('admin_userprofile_edit', pk=pk)
    make_active = request.POST.get("active") == "1"
    user.is_active = make_active
    user.save(update_fields=["is_active"])
    messages.success(request, f"Benutzer „{user.username}“ wurde {'aktiviert' if make_active else 'deaktiviert'}.")
    return redirect('admin_userprofile_edit', pk=pk)


@staff_required
def admin_userprofile_delete(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("Nur POST erlaubt.")
    profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
    user = profile.user
    if request.user.id == user.id:
        messages.error(request, "Du kannst dein eigenes Konto nicht löschen.")
        return redirect('admin_userprofile_edit', pk=pk)
    if InventoryItem.objects.filter(user=user).exists():
        messages.error(request, "Löschen abgebrochen: Dem Benutzer sind noch Inventar-Artikel zugeordnet. Bitte Artikel umhängen oder löschen.")
        return redirect('admin_userprofile_edit', pk=pk)
    username = user.username
    user.delete()
    messages.success(request, f"Benutzer „{username}“ wurde gelöscht.")
    return redirect('admin_user_profiles')


class UserProfileListView(StaffRequiredMixin, ListView):
    model = UserProfile
    template_name = 'inventory/admin_userprofiles_list.html'
    context_object_name = 'profiles'

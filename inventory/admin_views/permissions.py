"""
Admin Permissions: Matrix und Rollen (Legacy – unverändert).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.http import JsonResponse

from ..models import Page, RolePermission, UserProfile
from .helpers import staff_required


@staff_required
def permissions_matrix(request):
    pages = Page.objects.all().order_by("name")
    groups = Group.objects.all().order_by("name")
    return render(request, 'inventory/../a1_OLD/permissions_matrix.html', {
        "pages": pages,
        "groups": groups,
    })


@staff_required
def toggle_permission(request):
    if request.method != "POST":
        return JsonResponse({"error": "Nur POST"}, status=400)
    page_id = request.POST.get("page_id")
    group_id = request.POST.get("group_id")
    column = request.POST.get("column")
    if not all([page_id, group_id, column]):
        return JsonResponse({"error": "Fehlende Parameter"}, status=400)
    perm, _ = RolePermission.objects.get_or_create(page_id=page_id, group_id=group_id)
    if column != "view":
        return JsonResponse({"error": "Unbekannte Spalte"}, status=400)
    perm.can_view = not perm.can_view
    perm.save()
    return JsonResponse({"success": True})


@staff_required
def admin_manage_roles(request):
    groups = Group.objects.all().order_by("name")
    users = User.objects.filter(is_superuser=False).order_by("username")
    return render(request, 'inventory/../a1_OLD/admin_manage_roles.html', {
        "groups": groups,
        "users": users,
    })


@staff_required
def admin_user_roles_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        group_ids = request.POST.getlist("groups")
        user.groups.set(Group.objects.filter(pk__in=group_ids))
        messages.success(request, f"Rollen für „{user.username}“ gespeichert.")
        return redirect("admin_manage_roles")
    all_groups = Group.objects.all().order_by("name")
    user_group_ids = set(user.groups.values_list("id", flat=True))
    return render(request, 'inventory/../a1_OLD/admin_user_roles_form.html', {
        "edit_user": user,
        "all_groups": all_groups,
        "user_group_ids": user_group_ids,
    })


@staff_required
def admin_user_delete_legacy(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"Benutzer „{username}“ gelöscht.")
        return redirect("admin_manage_roles")
    return render(request, 'inventory/../a1_OLD/admin_user_confirm_delete.html', {"delete_user": user})

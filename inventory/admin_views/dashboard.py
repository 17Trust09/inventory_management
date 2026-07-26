"""
Admin-Dashboard-View.
"""
from django.shortcuts import render
from ..models import Overview, Feedback
from .helpers import _get_global_settings, _feature_enabled, staff_required


@staff_required
def dashboard(request):
    """Admin-Dashboard mit Schnellüberblick."""
    from ..models import PendingCategoryRequest, PendingTagRequest

    latest_feedback = Feedback.objects.select_related("created_by").order_by("-created_at")[:8]
    pending_overview_qs = Overview.objects.filter(is_active=False, requested_by__isnull=False)
    pending_overviews = pending_overview_qs.select_related("requested_by").order_by("-id")[:8]
    settings_obj = _get_global_settings()
    tailscale_setup_complete = (
        settings_obj.tailscale_setup_complete
        or settings_obj.tailscale_setup_ignored
        or settings_obj.tailscale_setup_step >= 4
    )
    pending_cat_count = PendingCategoryRequest.objects.filter(approved__isnull=True).count()
    pending_tag_count = PendingTagRequest.objects.filter(approved__isnull=True).count()
    pending_cat_reqs = PendingCategoryRequest.objects.filter(approved__isnull=True).select_related("requested_by").order_by("-created_at")[:5]
    pending_tag_reqs = PendingTagRequest.objects.filter(approved__isnull=True).select_related("requested_by").order_by("-created_at")[:5]

    return render(request, 'inventory/admin_dashboard.html', {
        "latest_feedback": latest_feedback,
        "pending_overviews": pending_overviews,
        "pending_overview_count": pending_overview_qs.count(),
        "tailscale_setup_complete": tailscale_setup_complete,
        "pending_cat_count": pending_cat_count,
        "pending_tag_count": pending_tag_count,
        "pending_cat_reqs": pending_cat_reqs,
        "pending_tag_reqs": pending_tag_reqs,
    })

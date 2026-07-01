"""
Admin-Feedback: Status setzen.
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

from ..models import Feedback
from .helpers import staff_required


@staff_required
def admin_feedback_set_status(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard')
    feedback = get_object_or_404(Feedback, pk=pk)
    new_status = request.POST.get("status", "").strip()
    if new_status in dict(Feedback.STATUS_CHOICES):
        feedback.status = new_status
        feedback.save(update_fields=["status"])
        messages.success(request, "Status aktualisiert.")
    return redirect('admin_dashboard')

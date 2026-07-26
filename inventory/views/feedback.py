"""
Feedback-Views: Liste, Detail, Erstellen, Vote, Kommentare.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, TemplateView, View
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from ..forms import FeedbackForm, FeedbackCommentForm
from ..models import Feedback, FeedbackComment, FeedbackVote


class FeedbackListView(LoginRequiredMixin, ListView):
    model = Feedback
    template_name = "inventory/feedback_list.html"
    context_object_name = "feedback_list"
    paginate_by = 20

    def get_queryset(self):
        qs = Feedback.objects.select_related("created_by").order_by("-created_at")
        status_filter = self.request.GET.get("status", "")
        valid_statuses = {choice[0] for choice in Feedback.Status.choices}
        if status_filter in valid_statuses:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get("status", "")
        valid_statuses = {choice[0] for choice in Feedback.Status.choices}
        ctx["status_filter"] = status_filter if status_filter in valid_statuses else ""
        return ctx


class FeedbackDetailView(LoginRequiredMixin, TemplateView):
    template_name = "inventory/feedback_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        feedback = get_object_or_404(
            Feedback.objects.select_related("created_by"),
            pk=kwargs["pk"]
        )
        ctx["feedback"] = feedback
        ctx["comments"] = FeedbackComment.objects.filter(feedback=feedback).select_related("author")
        ctx["comment_form"] = FeedbackCommentForm()
        user_vote = FeedbackVote.objects.filter(
            feedback=feedback, user=self.request.user
        ).first()
        ctx["user_vote"] = user_vote.value if user_vote else None
        return ctx


class FeedbackCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "inventory/feedback_form.html", {"form": FeedbackForm()})

    def post(self, request):
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.created_by = request.user
            fb.save()
            messages.success(request, "Feedback gesendet. Danke!")
            return redirect("feedback-list")
        return render(request, "inventory/feedback_form.html", {"form": form})


class FeedbackVoteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        feedback = get_object_or_404(Feedback, pk=pk)
        vote_value = request.POST.get("vote") or request.GET.get("v")
        if vote_value not in ("up", "down"):
            messages.error(request, "Ungültiger Vote.")
            return redirect("feedback-detail", pk=pk)

        existing = FeedbackVote.objects.filter(feedback=feedback, user=request.user).first()
        if existing:
            existing.delete()

        value = 1 if vote_value == "up" else -1
        FeedbackVote.objects.create(feedback=feedback, user=request.user, value=value)
        return redirect("feedback-detail", pk=pk)


class FeedbackCommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        feedback = get_object_or_404(Feedback, pk=pk)
        form = FeedbackCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.feedback = feedback
            comment.author = request.user
            comment.save()
            messages.success(request, "Kommentar hinzugefügt.")
        else:
            messages.error(request, "Fehler beim Speichern.")
        return redirect("feedback-detail", pk=pk)


__all__ = [
    "FeedbackListView", "FeedbackDetailView", "FeedbackCreateView",
    "FeedbackVoteView", "FeedbackCommentCreateView",
]

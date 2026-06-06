"""Admin registration for suppression models."""
from django.contrib import admin

from .models import Bounce, Complaint, Unsubscribe


@admin.register(Bounce)
class BounceAdmin(admin.ModelAdmin):
    """Admin view for bounce records."""

    list_display = ["email", "smtp_code", "created_at"]
    search_fields = ["email"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    """Admin view for spam complaint records."""

    list_display = ["email", "feedback_type", "created_at"]
    search_fields = ["email"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(Unsubscribe)
class UnsubscribeAdmin(admin.ModelAdmin):
    """Admin view for unsubscribe records."""

    list_display = ["email", "source", "created_at"]
    search_fields = ["email"]
    readonly_fields = ["token", "created_at"]
    ordering = ["-created_at"]

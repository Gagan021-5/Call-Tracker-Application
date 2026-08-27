"""
Django Admin configuration for Call Tracer models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CallLog, CallStats, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for the User model with role and device_id fields."""

    list_display = [
        "username",
        "email",
        "role",
        "device_id",
        "date_joined",
        "last_login",
        "is_active",
    ]
    list_filter = ["role", "is_active", "date_joined"]
    search_fields = ["username", "email", "device_id"]
    ordering = ["-date_joined"]

    # Add custom fields to the admin form
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Call Tracer",
            {
                "fields": ("role", "device_id"),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Call Tracer",
            {
                "fields": ("role", "device_id"),
            },
        ),
    )


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    """Admin for browsing synced call logs."""

    list_display = [
        "user",
        "phone_number",
        "call_type",
        "duration",
        "timestamp",
        "synced_at",
    ]
    list_filter = ["call_type", "timestamp", "synced_at"]
    search_fields = ["phone_number", "user__username"]
    raw_id_fields = ["user"]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]


@admin.register(CallStats)
class CallStatsAdmin(admin.ModelAdmin):
    """Admin for viewing aggregated daily call statistics."""

    list_display = [
        "user",
        "date",
        "total_calls",
        "total_duration",
    ]
    list_filter = ["date"]
    search_fields = ["user__username"]
    raw_id_fields = ["user"]
    date_hierarchy = "date"
    ordering = ["-date"]

"""
Django Admin configuration for Call Tracer models.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from api.models import CallLog, CallStats

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""

    list_display = [
        "username",
        "email",
        "role",
        "connect_code",
        "admin_id",
        "device_model",
        "consent_given",
        "is_active",
        "date_joined",
    ]
    list_filter = ["role", "consent_given", "is_active", "is_staff"]
    search_fields = ["username", "email", "connect_code", "device_id", "device_model"]
    ordering = ["-date_joined"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Call Tracer & Team Management",
            {
                "fields": (
                    "role",
                    "connect_code",
                    "admin_id",
                    "device_id",
                    "device_model",
                    "app_version",
                    "consent_given",
                ),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Call Tracer & Team Management",
            {
                "fields": (
                    "role",
                    "connect_code",
                    "admin_id",
                    "device_id",
                    "device_model",
                    "app_version",
                    "consent_given",
                ),
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
    """Admin for viewing aggregated call statistics."""

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

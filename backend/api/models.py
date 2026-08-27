"""
Models for the Call Tracer API.

- User: extends AbstractUser with role, admin_id link, connect_code, device info, and consent
- CallLog: individual call log entries synced from employee devices
- CallStats: aggregated daily per-user call statistics
"""

import secrets
import string
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


def generate_connect_code() -> str:
    """Generate a unique connect code for admin accounts: format XXX-NNNN-NNNN (3 uppercase letters, 4 digits, 4 digits)."""
    letters = "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))
    digits1 = "".join(secrets.choice(string.digits) for _ in range(4))
    digits2 = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{letters}-{digits1}-{digits2}"


class User(AbstractUser):
    """Custom user model with role-based team management and device tracking."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("admin", "Admin"),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="user",
        db_index=True,
        help_text="Determines access level: 'user' for employees, 'admin' for managers.",
    )
    admin_id = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Links an employee to their admin manager; null for admin accounts.",
    )
    connect_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Auto-generated unique code for admin accounts (e.g. OBL-XXXX-XXXX).",
    )
    device_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default="",
        help_text="Unique identifier for the employee's company-issued Android device.",
    )
    device_model = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default="",
        help_text="Hardware device model (e.g. Samsung Galaxy S24, Pixel 8).",
    )
    app_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default="",
        help_text="Installed application version.",
    )
    consent_given = models.BooleanField(
        default=False,
        help_text="Indicates whether the employee has acknowledged the monitoring disclosure.",
    )

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        if self.role == "admin":
            return f"{self.username} (Admin: {self.connect_code or 'No Code'})"
        return f"{self.username} (Employee of {self.admin_id.username if self.admin_id else 'Unassigned'})"

    def save(self, *args, **kwargs):
        # Auto-generate unique connect code for admin users if not already set
        if self.role == "admin" and not self.connect_code:
            code = generate_connect_code()
            while User.objects.filter(connect_code=code).exists():
                code = generate_connect_code()
            self.connect_code = code
        elif self.role == "user":
            self.connect_code = None
        super().save(*args, **kwargs)


class CallLog(models.Model):
    """
    Individual call log entry synced from an employee's device.
    Deduplication enforced via unique constraint on (user, phone_number, timestamp).
    """

    CALL_TYPE_CHOICES = [
        ("incoming", "Incoming"),
        ("outgoing", "Outgoing"),
        ("missed", "Missed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="call_logs",
    )
    phone_number = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Phone number involved in the call.",
    )
    call_type = models.CharField(
        max_length=10,
        choices=CALL_TYPE_CHOICES,
        db_index=True,
    )
    duration = models.PositiveIntegerField(
        default=0,
        help_text="Call duration in seconds.",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When the call occurred on the device.",
    )
    synced_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was synced to the server.",
    )

    class Meta:
        db_table = "call_logs"
        ordering = ["-timestamp"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "phone_number", "timestamp"],
                name="unique_call_log_entry",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "timestamp"],
                name="idx_user_timestamp",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.call_type} — {self.phone_number} @ {self.timestamp}"


class CallStats(models.Model):
    """
    Aggregated daily call statistics per user.
    Populated by the `aggregate_call_stats` management command.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="call_stats",
    )
    date = models.DateField(
        db_index=True,
        help_text="The date these statistics cover.",
    )
    total_calls = models.PositiveIntegerField(default=0)
    total_duration = models.PositiveIntegerField(
        default=0,
        help_text="Total call duration in seconds for this date.",
    )
    calls_by_type = models.JSONField(
        default=dict,
        help_text='Breakdown by call type, e.g. {"incoming": 5, "outgoing": 3, "missed": 1}',
    )
    top_numbers = models.JSONField(
        default=list,
        help_text='Top contacted numbers, e.g. [{"number": "+91...", "count": 10}, ...]',
    )

    class Meta:
        db_table = "call_stats"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_user_date_stats",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.date} — {self.total_calls} calls"

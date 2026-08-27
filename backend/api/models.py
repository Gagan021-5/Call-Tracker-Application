"""
Models for the Call Tracer API.

- User: extends AbstractUser with role (user/admin) and device_id
- CallLog: individual call log entries synced from employee devices
- CallStats: aggregated daily per-user call statistics
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role-based access and device tracking."""

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
    device_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Unique identifier for the employee's company-issued Android device.",
    )

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.role})"


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

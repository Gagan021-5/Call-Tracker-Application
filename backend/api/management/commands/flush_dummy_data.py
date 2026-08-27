"""
Management command to clear all dummy/test call logs, stats, and non-admin users.
Preserves admin superuser account(s) so you can monitor incoming real-time calls.

Usage:
    python manage.py flush_dummy_data
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from api.models import CallLog, CallStats

User = get_user_model()


class Command(BaseCommand):
    help = "Clear all dummy data from database for clean production / real-time tracking."

    def handle(self, *args, **options):
        self.stdout.write("Clearing dummy data...")

        # Delete all call logs & aggregated stats
        logs_deleted, _ = CallLog.objects.all().delete()
        stats_deleted, _ = CallStats.objects.all().delete()

        # Delete all non-admin employee users
        employees = User.objects.filter(role="user")
        emp_count = employees.count()
        employees.delete()

        admin_count = User.objects.filter(role="admin").count()

        self.stdout.write(
            self.style.SUCCESS(
                f"[SUCCESS] Database cleaned!\n"
                f"  - Deleted {logs_deleted} CallLog entries\n"
                f"  - Deleted {stats_deleted} CallStats records\n"
                f"  - Deleted {emp_count} test employee user(s)\n"
                f"  - Preserved {admin_count} admin account(s)\n"
                f"Ready for real-time tracking."
            )
        )

"""
Management command to seed realistic dummy data for testing the Call Tracer UI.

Creates:
- 3 Sales Employee users (john_sales, sarah_sales, alex_sales)
- 300+ Call Logs spanning the last 14 days with incoming, outgoing, missed calls
- Pre-aggregates daily CallStats for rich chart visualizations

Usage:
    python manage.py seed_dummy_data
"""

import random
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from api.models import CallLog

User = get_user_model()

SAMPLE_NUMBERS = [
    "+1 (555) 234-5678",
    "+1 (555) 876-5432",
    "+1 (555) 345-6789",
    "+1 (555) 987-6543",
    "+1 (555) 456-7890",
    "+91 98765 43210",
    "+91 91234 56789",
    "+91 99887 76655",
    "+44 20 7946 0912",
    "+44 20 7946 0834",
]

SAMPLE_EMPLOYEES = [
    {
        "username": "john_sales",
        "email": "john.sales@company.com",
        "device_id": "Pixel 8 Pro (DEV-001)",
        "password": "password123",
    },
    {
        "username": "sarah_sales",
        "email": "sarah.sales@company.com",
        "device_id": "Galaxy S24 (DEV-002)",
        "password": "password123",
    },
    {
        "username": "alex_sales",
        "email": "alex.sales@company.com",
        "device_id": "Moto Edge 40 (DEV-003)",
        "password": "password123",
    },
]


class Command(BaseCommand):
    help = "Seed realistic dummy call logs and users for UI testing."

    def handle(self, *args, **options):
        self.stdout.write("Seeding dummy data...")

        created_users = []
        for emp_data in SAMPLE_EMPLOYEES:
            user, created = User.objects.get_or_create(
                username=emp_data["username"],
                defaults={
                    "email": emp_data["email"],
                    "device_id": emp_data["device_id"],
                    "role": "user",
                },
            )
            if created:
                user.set_password(emp_data["password"])
                user.save()
                self.stdout.write(f"  Created user: {user.username}")
            else:
                self.stdout.write(f"  User already exists: {user.username}")
            created_users.append(user)

        # Generate call logs over the last 14 days
        now = datetime.now(timezone.utc)
        call_logs = []
        call_types = ["incoming", "outgoing", "outgoing", "incoming", "missed"]

        for user in created_users:
            for day_offset in range(14):
                day_date = now - timedelta(days=day_offset)
                num_calls = random.randint(4, 12)

                for _ in range(num_calls):
                    call_type = random.choice(call_types)
                    duration = 0 if call_type == "missed" else random.randint(25, 950)
                    phone_number = random.choice(SAMPLE_NUMBERS)

                    hour = random.randint(9, 18)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    call_time = day_date.replace(
                        hour=hour, minute=minute, second=second, microsecond=0
                    )

                    call_logs.append(
                        CallLog(
                            user=user,
                            phone_number=phone_number,
                            call_type=call_type,
                            duration=duration,
                            timestamp=call_time,
                        )
                    )

        # Bulk create with ignore conflicts
        created = CallLog.objects.bulk_create(call_logs, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(f"  Created {len(created)} call log entries.")
        )

        # Run aggregate_call_stats to populate CallStats for all dates
        self.stdout.write("  Aggregating call statistics...")
        call_command("aggregate_call_stats", all_dates=True)

        self.stdout.write(
            self.style.SUCCESS(
                "\n[SUCCESS] Dummy data seeded successfully!\n"
                "You can now explore the Users list, Call Logs, and visual Charts on the Admin Dashboard."
            )
        )

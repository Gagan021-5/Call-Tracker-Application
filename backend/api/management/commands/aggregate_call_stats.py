"""
Management command: aggregate_call_stats

Computes daily per-user call statistics from the CallLog table
and writes them to the CallStats table using update_or_create.

Usage:
    python manage.py aggregate_call_stats                # aggregates for yesterday
    python manage.py aggregate_call_stats --date 2026-08-25  # specific date
    python manage.py aggregate_call_stats --all-dates    # all dates with data

Can be scheduled via cron:
    0 2 * * * cd /path/to/backend && python manage.py aggregate_call_stats
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate

from api.models import CallLog, CallStats

User = get_user_model()


class Command(BaseCommand):
    help = "Aggregate daily call statistics per user from CallLog into CallStats."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Specific date to aggregate (YYYY-MM-DD). Defaults to yesterday.",
        )
        parser.add_argument(
            "--all-dates",
            action="store_true",
            default=False,
            help="Aggregate stats for ALL dates that have call log data.",
        )

    def handle(self, *args, **options):
        if options["all_dates"]:
            # Get all unique dates from call logs
            dates = (
                CallLog.objects.annotate(log_date=TruncDate("timestamp"))
                .values_list("log_date", flat=True)
                .distinct()
                .order_by("log_date")
            )
            dates = list(dates)
            self.stdout.write(f"Aggregating stats for {len(dates)} date(s)...")
        elif options["date"]:
            target_date = date.fromisoformat(options["date"])
            dates = [target_date]
        else:
            # Default: yesterday
            target_date = date.today() - timedelta(days=1)
            dates = [target_date]

        total_created = 0
        total_updated = 0

        for target_date in dates:
            self.stdout.write(f"Processing date: {target_date}")

            # Get all users who have call logs on this date
            user_ids = (
                CallLog.objects.filter(timestamp__date=target_date)
                .values_list("user_id", flat=True)
                .distinct()
            )

            for user_id in user_ids:
                user_logs = CallLog.objects.filter(
                    user_id=user_id,
                    timestamp__date=target_date,
                )

                # Total calls and duration
                totals = user_logs.aggregate(
                    total_calls=Count("id"),
                    total_duration=Sum("duration"),
                )

                # Calls by type
                calls_by_type = dict(
                    user_logs.values("call_type")
                    .annotate(count=Count("id"))
                    .values_list("call_type", "count")
                )

                # Top 5 numbers
                top_numbers = list(
                    user_logs.values("phone_number")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:5]
                )

                # Upsert
                _, created = CallStats.objects.update_or_create(
                    user_id=user_id,
                    date=target_date,
                    defaults={
                        "total_calls": totals["total_calls"] or 0,
                        "total_duration": totals["total_duration"] or 0,
                        "calls_by_type": calls_by_type,
                        "top_numbers": top_numbers,
                    },
                )

                if created:
                    total_created += 1
                else:
                    total_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {total_created}, Updated: {total_updated}"
            )
        )

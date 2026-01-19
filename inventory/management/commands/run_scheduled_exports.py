from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.exports import export_overview_to_file, calculate_next_run
from inventory.models import ScheduledExport, ExportRun


class Command(BaseCommand):
    help = "Führt fällige geplante Exporte aus."

    def handle(self, *args, **options):
        now = timezone.now()
        schedules = ScheduledExport.objects.filter(is_active=True).filter(
            next_run_at__isnull=True
        ) | ScheduledExport.objects.filter(is_active=True, next_run_at__lte=now)

        count = 0
        for schedule in schedules.select_related("overview"):
            run = ExportRun.objects.create(
                scheduled_export=schedule,
                status=ExportRun.Status.SUCCESS,
            )
            try:
                file_path = export_overview_to_file(
                    overview=schedule.overview,
                    export_format=schedule.export_format,
                    columns=schedule.columns,
                )
                run.file_path = file_path
                run.save(update_fields=["file_path"])
                schedule.last_run_at = now
                schedule.next_run_at = calculate_next_run(schedule.frequency, now)
                schedule.save(update_fields=["last_run_at", "next_run_at"])
                count += 1
            except Exception as exc:
                run.status = ExportRun.Status.FAILED
                run.error_message = str(exc)
                run.save(update_fields=["status", "error_message"])

        self.stdout.write(self.style.SUCCESS(f"{count} Exporte ausgeführt."))

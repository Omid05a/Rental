from django.core.management.base import BaseCommand

from apps.bookings.trip_services import release_due_deposits


class Command(BaseCommand):
    help = "Returns deposits whose damage-report window has ended."

    def handle(self, *args, **options):
        count = release_due_deposits()
        self.stdout.write(self.style.SUCCESS(f"Released {count} deposit(s)."))
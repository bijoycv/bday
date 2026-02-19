"""Run the unified scheduled wishes engine (channel-aware)."""
from django.core.management.base import BaseCommand
from birthday.tasks import send_scheduled_wishes_task


class Command(BaseCommand):
    help = 'Send all pending scheduled wishes that are due'

    def handle(self, *args, **options):
        result = send_scheduled_wishes_task()
        self.stdout.write(self.style.SUCCESS('Processing complete!'))
        self.stdout.write(f"  Sent: {result.get('sent', 0)}")
        self.stdout.write(f"  Failed: {result.get('failed', 0)}")
        self.stdout.write(f"  Total: {result.get('total', 0)}")

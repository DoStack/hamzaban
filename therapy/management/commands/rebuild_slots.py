from django.core.management.base import BaseCommand

from therapy.models import TherapistProfile
from therapy.services import rebuild_slots


class Command(BaseCommand):
    help = "Rebuild open appointment slots for the next 30 days."

    def handle(self, *args, **options):
        count = 0
        for profile in TherapistProfile.objects.all().iterator():
            rebuild_slots(profile)
            count += 1
        self.stdout.write(f"rebuilt slots for {count} therapists")

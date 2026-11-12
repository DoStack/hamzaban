from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from clients.forms import THERAPIST_GROUP_NAME
from therapy.directory_import import directory_slugs, parse_profile
from therapy.models import AvailabilityCell, TherapistProfile
from therapy.services import replace_cells


class Command(BaseCommand):
    help = "Import public therapist profiles from a Hamzaban directory."

    def add_arguments(self, parser):
        parser.add_argument("--base", default="https://hamzaban.bigde.li")

    def handle(self, *args, **options):
        base = options["base"].rstrip("/")
        slugs = directory_slugs(_read(f"{base}/therapists"))
        group, _created = Group.objects.get_or_create(name=THERAPIST_GROUP_NAME)
        for slug in slugs:
            record = parse_profile(_read(f"{base}/therapists/{slug}"), slug)
            profile = save_imported_profile(record, group, base)
            open_slots = profile.slots.filter(status="OPEN").count()
            self.stdout.write(f"{profile.display_name} · {profile.status} · {open_slots} open slots")


def save_imported_profile(record, group, base):
    with transaction.atomic():
        user, created = User.objects.get_or_create(
            username=record["slug"][:150],
            defaults={
                "email": f"{record['slug'][:60]}@imported.hamzaban.invalid",
                "first_name": record["display_name"][:150],
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        user.groups.add(group)
        fields = dict(
            display_name=record["display_name"],
            slug=record["slug"],
            gender="unspecified",
            languages=record["languages"],
            years_experience=0,
            license_type=record["license_type"],
            license_number=record["license_number"],
            license_country="ایران",
            specialties=record["specialties"],
            approach=record["approach"],
            introduction=record["introduction"],
            currency=record["currency"],
            session_price=Decimal(record["session_price"]),
            timezone=record["timezone"],
        )
        profile = TherapistProfile.objects.filter(user=user).first()
        if profile is None:
            profile = TherapistProfile(user=user, status=TherapistProfile.Status.PENDING, **fields)
            profile.save()
        else:
            for key, value in fields.items():
                setattr(profile, key, value)
            profile.save()
        if not profile.license_file:
            profile.license_file.save(
                f"{record['slug']}-license.txt",
                ContentFile("مجوز از صفحهٔ عمومی وارد نشده است.".encode()),
                save=True,
            )
        if record["image"]:
            _save_photo(profile, base, record["image"])
        target = TherapistProfile.Status.PENDING if record["test_profile"] else TherapistProfile.Status.APPROVED
        if profile.status != target:
            profile.status = target
            profile.save()
        if profile.status == TherapistProfile.Status.APPROVED:
            replace_cells(profile, record["cells"])
        else:
            profile.cells.all().delete()
            AvailabilityCell.objects.bulk_create(
                [AvailabilityCell(profile=profile, weekday=day, start=start) for day, start in record["cells"]]
            )
        return profile


def _read(url):
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def _save_photo(profile, base, image_path):
    with urlopen(base + image_path, timeout=30) as response:
        content = response.read()
    profile.photo.save(Path(image_path).name, ContentFile(content), save=True)

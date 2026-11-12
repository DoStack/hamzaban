from datetime import time
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile

from therapy.models import AvailabilityCell, TherapistProfile
from therapy.services import rebuild_slots


def make_client(username="leila", first_name="لیلا"):
    return User.objects.create_user(
        username=username,
        password="Safe-pass-48",
        first_name=first_name,
        email=f"{username}@example.com",
    )


def make_profile(
    *,
    username="sara",
    display_name="سارا نیک‌فر",
    specialties=None,
    status=TherapistProfile.Status.PENDING,
    with_hours=False,
    slug=None,
):
    user = User.objects.create_user(
        username=username,
        password="Safe-pass-48",
        first_name=display_name.split()[0],
        email=f"{username}@example.com",
    )
    group, _created = Group.objects.get_or_create(name="therapist")
    user.groups.add(group)
    profile = TherapistProfile.objects.create(
        user=user,
        display_name=display_name,
        slug=slug or username,
        gender="female",
        languages=["فارسی"],
        years_experience=6,
        license_type="psychology",
        license_number=f"LIC-{username}",
        license_country="ایران",
        license_file=SimpleUploadedFile(f"{username}.pdf", b"%PDF-1.4", content_type="application/pdf"),
        specialties=specialties or ["اضطراب"],
        approach="cbt",
        introduction="معرفی کوتاه برای آزمون.",
        currency="IRR",
        session_price=Decimal("500000"),
        timezone="Asia/Tehran",
        status=TherapistProfile.Status.PENDING,
    )
    if with_hours:
        for weekday in range(7):
            AvailabilityCell.objects.create(profile=profile, weekday=weekday, start=time(12, 0))
    if status != TherapistProfile.Status.PENDING:
        profile.status = status
        profile.save()
    elif with_hours:
        rebuild_slots(profile)
    return profile


def registration_data(**overrides):
    data = {
        "first_name": "سارا",
        "username": "sara",
        "email": "sara@example.com",
        "password1": "Safe-pass-48",
        "password2": "Safe-pass-48",
        "display_name": "سارا نیک‌فر",
        "gender": "female",
        "languages": ["فارسی"],
        "years_experience": "6",
        "license_type": "psychology",
        "license_number": "A-100",
        "license_country": "ایران",
        "specialties": ["اضطراب"],
        "approach": "cbt",
        "introduction": "با اضطراب کار می‌کنم.",
        "currency": "IRR",
        "session_price": "450000",
        "timezone": "Asia/Tehran",
    }
    data.update(overrides)
    return data

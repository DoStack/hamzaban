from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from therapy.calendar import MONTHS, add_business_days, format_jalali, gregorian_to_jalali, grid_starts
from therapy.choices import DAY_LABELS, SLOT_MINUTES
from therapy.models import (
    AvailabilityClosure,
    AvailabilityCell,
    Booking,
    ClientLink,
    ClientRecord,
    Notification,
    MoodLog,
    Receipt,
    Slot,
    Task,
    TherapistProfile,
)

WEEK_COUNTS = (2, 4, 6, 8, 10, 12)

DAILY_CARDS = (
    ("daily", "کارت امروز", "یک کار کوچک را تا آخر انجام بده و تمام شدنش را برای خودت علامت بزن.", "حس تمام کردن"),
    ("challenge", "چالش امروز", "ده دقیقه راه برو و فقط به قدم‌ها توجه کن.", "ده دقیقه برای خودت"),
    ("practice", "یادآور تمرین", "چهار شماره دم، شش شماره بازدم. این را سه بار تکرار کن.", "بدن کمی آرام‌تر"),
)


class SlotTaken(Exception):
    pass


class CancelError(Exception):
    pass


def normalize(value):
    return value.strip().replace("\u200c", "").replace("ي", "ی").replace("ك", "ک").casefold()


def unique_slug(name):
    base = slugify(name, allow_unicode=True) or "therapist"
    slug = base
    number = 2
    while TherapistProfile.objects.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


def notify(user, title, body, *, link="", event_key=""):
    """Store the latest news for one event. A repeat update replaces the previous one."""
    if event_key:
        note = Notification.objects.filter(user=user, event_key=event_key).first()
        if note is not None:
            note.title = title
            note.body = body
            note.link = link
            note.read_at = None
            note.created_at = timezone.now()
            note.save(update_fields=["title", "body", "link", "read_at", "created_at"])
            return note
    return Notification.objects.create(user=user, title=title, body=body, link=link, event_key=event_key)


def _event_link(name, fragment, *args):
    return f"{reverse(name, args=args)}#{fragment}"


def review_deadline(profile):
    submitted = timezone.localtime(profile.created_at).date()
    return add_business_days(submitted, 2)


def review_is_late(profile, today=None):
    if profile.status != TherapistProfile.Status.PENDING:
        return False
    today = today or timezone.localdate()
    return today > review_deadline(profile)


def notice_cutoff(profile, now=None):
    now = now or timezone.now()
    return now + timedelta(hours=profile.min_notice_hours)


def shown_start(profile, starts_at):
    """Clock time printed for the client, read on the site clock."""
    site = ZoneInfo(timezone.get_current_timezone_name())
    shown = timezone.localtime(starts_at, ZoneInfo(profile.timezone))
    return shown.replace(tzinfo=site)


def accepts_notice(profile, starts_at, now=None):
    """A time is bookable only after this therapist's notice on the site clock."""
    cutoff = notice_cutoff(profile, now)
    return starts_at >= cutoff and shown_start(profile, starts_at) >= cutoff


def shown_on_site(profile, now=None):
    now = now or timezone.now()
    if profile.status != TherapistProfile.Status.APPROVED:
        return False
    cutoff = now + timedelta(hours=profile.min_notice_hours)
    return profile.slots.filter(status=Slot.Status.OPEN, starts_at__gte=cutoff).exists()


def public_therapists():
    ready = [
        profile.pk
        for profile in TherapistProfile.objects.filter(status=TherapistProfile.Status.APPROVED)
        if shown_on_site(profile)
    ]
    return TherapistProfile.objects.filter(pk__in=ready).order_by("display_name")


def search_public_therapists(query):
    profiles = list(public_therapists())
    needle = normalize(query)
    if not needle:
        return profiles
    matches = []
    for profile in profiles:
        haystack = normalize(
            " ".join(
                [
                    profile.display_name,
                    profile.get_approach_display(),
                    profile.introduction,
                    " ".join(profile.specialties or []),
                    " ".join(profile.education or []),
                    " ".join(profile.languages or []),
                ]
            )
        )
        if needle in haystack:
            matches.append(profile)
    return matches


def public_profile(slug):
    return public_therapists().filter(slug=slug).first()


def open_slots_by_day(profile):
    zone = ZoneInfo(profile.timezone)
    slots = profile.slots.filter(status=Slot.Status.OPEN, starts_at__gte=notice_cutoff(profile)).order_by("starts_at")
    days = []
    index = {}
    for slot in slots:
        if not accepts_notice(profile, slot.starts_at):
            continue
        local = timezone.localtime(slot.starts_at, zone)
        key = local.date()
        if key not in index:
            jy, jm, jd = gregorian_to_jalali(local.year, local.month, local.day)
            from therapy.calendar import MONTHS

            bucket = {
                "label": f"{DAY_LABELS[local.weekday()]} {jd} {MONTHS[jm]}",
                "slots": [],
            }
            index[key] = bucket
            days.append(bucket)
        index[key]["slots"].append({"id": slot.pk, "time": local.strftime("%H:%M")})
    return days


def booking_weeks(profile, now=None):
    """Weeks of bookable days, Saturday through Friday, in the therapist's zone.

    A time today is included when it is at least this therapist's minimum notice away.
    """
    now = now or timezone.now()
    zone = ZoneInfo(profile.timezone)
    today = timezone.localtime(now, zone).date()
    tomorrow = today + timedelta(days=1)
    horizon_end = today + timedelta(days=profile.horizon_days)
    week_start = today - timedelta(days=(today.weekday() - 5) % 7)
    grouped = {}
    slots = profile.slots.filter(status=Slot.Status.OPEN, starts_at__gte=notice_cutoff(profile, now)).order_by("starts_at")
    for slot in slots:
        if not accepts_notice(profile, slot.starts_at, now):
            continue
        local = timezone.localtime(slot.starts_at, zone)
        grouped.setdefault(local.date(), []).append({"id": slot.pk, "time": local.strftime("%H:%M")})
    weeks = []
    cursor = week_start
    while cursor <= horizon_end:
        days = []
        for offset in range(7):
            day = cursor + timedelta(days=offset)
            _year, month, number = gregorian_to_jalali(day.year, day.month, day.day)
            days.append(
                {
                    "key": day.isoformat(),
                    "name": DAY_LABELS[day.weekday()],
                    "number": number,
                    "month": MONTHS[month],
                    "label": f"{DAY_LABELS[day.weekday()]} {number} {MONTHS[month]}",
                    "badge": "امروز" if day == today else "فردا" if day == tomorrow else "",
                    "slots": grouped.get(day, []) if today <= day <= horizon_end else [],
                }
            )
        weeks.append({"id": cursor.isoformat(), "days": days})
        cursor += timedelta(days=7)
    return weeks


def ensure_link(therapist, client):
    link, _created = ClientLink.objects.get_or_create(therapist=therapist, client=client)
    ClientRecord.objects.get_or_create(link=link)
    return link


def book_slot(slot, client, amount, reference, attachment=None, note=""):
    with transaction.atomic():
        profile = TherapistProfile.objects.select_for_update().get(pk=slot.profile_id)
        cutoff = notice_cutoff(profile)
        if profile.user_id == client.id or profile.status != TherapistProfile.Status.APPROVED:
            raise SlotTaken
        locked = (
            Slot.objects.select_for_update()
            .filter(pk=slot.pk, profile=profile, status=Slot.Status.OPEN, starts_at__gte=cutoff)
            .first()
        )
        if locked is None or not accepts_notice(profile, locked.starts_at):
            raise SlotTaken
        gap = timedelta(minutes=profile.gap_minutes)
        overlaps = profile.slots.filter(
            status__in=[Slot.Status.HELD, Slot.Status.BOOKED],
            starts_at__lt=locked.ends_at + gap,
            ends_at__gt=locked.starts_at - gap,
        ).exclude(pk=locked.pk)
        if overlaps.exists():
            raise SlotTaken
        updated = Slot.objects.filter(pk=locked.pk, status=Slot.Status.OPEN).update(status=Slot.Status.HELD)
        if updated != 1:
            raise SlotTaken
        locked.refresh_from_db()
        booking = Booking.objects.create(
            client=client,
            therapist=profile,
            slot=locked,
            starts_at=locked.starts_at,
            ends_at=locked.ends_at,
            status=Booking.Status.AWAITING,
            price=profile.session_price,
            currency=profile.currency,
            client_note=(note or "")[:1000],
        )
        receipt = Receipt(booking=booking, amount=amount, reference=reference, status=Receipt.Status.SUBMITTED)
        if attachment:
            receipt.attachment = attachment
        receipt.save()
        ensure_link(profile, client)
        local = timezone.localtime(locked.starts_at, ZoneInfo(profile.timezone))
        when = f"{format_jalali(local)}، ساعت {local.strftime('%H:%M')}"
        notify(
            client,
            "رسید ثبت شد",
            "رسید شما برای درمانگر فرستاده شد. جلسه پس از تأیید او قطعی می‌شود.",
            link=_event_link("client_payments", f"receipt-{receipt.pk}"),
            event_key=f"booking-{booking.pk}",
        )
        notify(
            profile.user,
            "رسید جدید",
            f"یک رسید برای جلسهٔ {when} ثبت شد.",
            link=_event_link("therapist_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
    return booking


def book_slots(slots, client, amount, reference, attachment=None, note=""):
    """Hold every selected time and store one receipt share for each session."""
    ordered = sorted(slots, key=lambda item: (item.starts_at, item.pk))
    if len(ordered) < 2:
        raise SlotTaken("حداقل دو وقت جدا انتخاب کنید.")
    file_bytes = b""
    file_name = ""
    if attachment:
        file_bytes = attachment.read()
        file_name = Path(attachment.name).name
    amount = Decimal(amount)
    with transaction.atomic():
        profile = TherapistProfile.objects.select_for_update().get(pk=ordered[0].profile_id)
        if any(item.profile_id != profile.pk for item in ordered) or profile.user_id == client.id:
            raise SlotTaken("رزرو از حساب درمانگر انجام نمی‌شود.")
        if profile.status != TherapistProfile.Status.APPROVED:
            raise SlotTaken("این وقت دیگر آزاد نیست.")
        locked = []
        for item in sorted(ordered, key=lambda row: row.pk):
            row = (
                Slot.objects.select_for_update()
                .filter(pk=item.pk, profile=profile, status=Slot.Status.OPEN, starts_at__gte=notice_cutoff(profile))
                .first()
            )
            if row is None or not accepts_notice(profile, row.starts_at):
                raise SlotTaken("یکی از وقت‌ها دیگر آزاد نیست.")
            locked.append(row)
        locked.sort(key=lambda row: row.starts_at)
        batch = {row.pk for row in locked}
        gap = timedelta(minutes=profile.gap_minutes)
        for row in locked:
            overlaps = profile.slots.filter(
                status__in=[Slot.Status.HELD, Slot.Status.BOOKED],
                starts_at__lt=row.ends_at + gap,
                ends_at__gt=row.starts_at - gap,
            ).exclude(pk__in=batch)
            if overlaps.exists():
                raise SlotTaken("یکی از وقت‌ها به جلسهٔ دیگری خیلی نزدیک است.")
        for row in locked:
            if Slot.objects.filter(pk=row.pk, status=Slot.Status.OPEN).update(status=Slot.Status.HELD) != 1:
                raise SlotTaken("یکی از وقت‌ها همین حالا گرفته شد.")
        share = (amount / len(locked)).quantize(Decimal("0.01"))
        shares = [share] * (len(locked) - 1)
        shares.append(amount - share * (len(locked) - 1))
        note = (note or "")[:1000]
        bookings = []
        for row, part in zip(locked, shares):
            booking = Booking.objects.create(
                client=client,
                therapist=profile,
                slot=row,
                starts_at=row.starts_at,
                ends_at=row.ends_at,
                status=Booking.Status.AWAITING,
                price=profile.session_price,
                currency=profile.currency,
                client_note=note,
            )
            receipt = Receipt(booking=booking, amount=part, reference=reference, status=Receipt.Status.SUBMITTED)
            if file_bytes:
                receipt.attachment.save(file_name, ContentFile(file_bytes), save=False)
            receipt.save()
            bookings.append(booking)
        ensure_link(profile, client)
        count = len(bookings)
        when = "، ".join(slot_when(item.slot) for item in bookings[:3])
        notify(
            client,
            "رسید ثبت شد",
            f"رسید {count} جلسه ثبت شد. جلسه‌ها پس از تأیید درمانگر قطعی می‌شوند.",
            link=_event_link("client_payments", f"receipt-{bookings[0].receipt.pk}"),
            event_key=f"booking-{bookings[0].pk}",
        )
        notify(
            profile.user,
            "رسید جدید",
            f"یک رسید برای {count} جلسه ثبت شد: {when}",
            link=_event_link("therapist_sessions", f"booking-{bookings[0].pk}"),
            event_key=f"booking-{bookings[0].pk}",
        )
    return bookings


def weekly_plan(profile, anchor, count, now=None):
    """Same clock time for the next count weeks, including weeks that are not free."""
    now = now or timezone.now()
    count = int(count)
    if count not in WEEK_COUNTS:
        raise ValueError(count)
    zone = ZoneInfo(profile.timezone)
    local = timezone.localtime(anchor.starts_at, zone)
    clock = local.time().replace(second=0, microsecond=0)
    closed_days = set()
    closed_hours = set()
    for closure in profile.closures.all():
        if closure.start is None:
            closed_days.add(closure.date)
        else:
            closed_hours.add((closure.date, closure.start.replace(second=0, microsecond=0)))
    has_cell = profile.cells.filter(weekday=local.weekday(), start=clock).exists()
    meetings = []
    for index in range(count):
        day = local.date() + timedelta(weeks=index)
        starts = datetime.combine(day, clock, tzinfo=zone)
        ends = starts + timedelta(minutes=SLOT_MINUTES)
        existing = profile.slots.filter(starts_at=starts).first()
        if existing is not None and existing.status != Slot.Status.OPEN:
            available, reason = False, "این هفته گرفته شده"
        elif day in closed_days or (day, clock) in closed_hours:
            available, reason = False, "این هفته بسته است"
        elif not accepts_notice(profile, starts, now):
            available, reason = False, "زودتر از حداقل اطلاع قبلی است"
        elif existing is None and not has_cell:
            available, reason = False, "این ساعت در هفته‌های بعد نیست"
        else:
            available, reason = True, ""
        meetings.append(
            {
                "label": f"{format_jalali(starts)}، ساعت {clock.strftime('%H:%M')}",
                "time": clock.strftime("%H:%M"),
                "available": available,
                "reason": reason,
                "starts": starts,
                "ends": ends,
                "slot": existing if existing is not None and existing.status == Slot.Status.OPEN else None,
            }
        )
    return meetings


def book_weekly(profile, anchor, count, client, amount, reference, attachment, note, expected):
    with transaction.atomic():
        profile = TherapistProfile.objects.select_for_update().get(pk=profile.pk)
        anchor = profile.slots.get(pk=anchor.pk)
        open_rows = [row for row in weekly_plan(profile, anchor, count) if row["available"]]
        if len(open_rows) < 2 or len(open_rows) != int(expected):
            raise SlotTaken("تعداد جلسه‌های آزاد عوض شد. فهرست را دوباره ببینید.")
        slots = []
        for row in open_rows:
            slot = row["slot"]
            if slot is None:
                slot, _created = Slot.objects.get_or_create(
                    profile=profile,
                    starts_at=row["starts"],
                    defaults={"ends_at": row["ends"], "status": Slot.Status.OPEN},
                )
            if slot.status != Slot.Status.OPEN:
                raise SlotTaken("یکی از هفته‌ها همین حالا گرفته شد.")
            slots.append(slot)
        return book_slots(slots, client, amount, reference, attachment, note)


def _sync_calendar(booking_id, publish):
    from therapy.google_calendar import GoogleCalendarError, drop_booking_event, publish_booking

    booking = Booking.objects.select_related("therapist__user", "client").get(pk=booking_id)
    try:
        if publish:
            ready = publish_booking(booking)
        else:
            ready = drop_booking_event(booking)
    except GoogleCalendarError:
        notify(
            booking.therapist.user,
            "تقویم گوگل به‌روز نشد",
            "جلسه در هم‌زبان ثبت است، اما رویداد تقویم ساخته یا حذف نشد.",
            link=_event_link("therapist_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
        return
    if publish and ready and booking.meet_url:
        notify(
            booking.client,
            "پیوند جلسه آماده شد",
            "ورود به جلسه از بخش جلسه‌ها باز می‌شود.",
            link=_event_link("client_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )


def accept_receipt(receipt):
    with transaction.atomic():
        therapist_id = Booking.objects.filter(pk=receipt.booking_id).values_list("therapist_id", flat=True).first()
        if therapist_id is None:
            return False
        profile = TherapistProfile.objects.select_for_update().get(pk=therapist_id)
        booking = Booking.objects.select_for_update().get(pk=receipt.booking_id)
        receipt = Receipt.objects.select_for_update().get(pk=receipt.pk)
        if (
            profile.status != TherapistProfile.Status.APPROVED
            or booking.status != Booking.Status.AWAITING
            or receipt.status != Receipt.Status.SUBMITTED
        ):
            return False
        receipt.status = Receipt.Status.ACCEPTED
        receipt.save(update_fields=["status"])
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status"])
        if booking.slot_id:
            Slot.objects.filter(pk=booking.slot_id).update(status=Slot.Status.BOOKED)
        gap = timedelta(minutes=profile.gap_minutes)
        Slot.objects.filter(
            profile=profile,
            status=Slot.Status.OPEN,
            starts_at__lt=booking.ends_at + gap,
            ends_at__gt=booking.starts_at - gap,
        ).delete()
        notify(
            booking.client,
            "رسید تأیید شد",
            "جلسهٔ شما قطعی شد.",
            link=_event_link("client_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
        notify(
            profile.user,
            "جلسه قطعی شد",
            "رسید یک جلسه را تأیید کردید.",
            link=_event_link("therapist_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
        booking_id = booking.pk
    _sync_calendar(booking_id, publish=True)
    return True


def reject_receipt(receipt):
    with transaction.atomic():
        therapist_id = Booking.objects.filter(pk=receipt.booking_id).values_list("therapist_id", flat=True).first()
        if therapist_id is None:
            return False
        profile = TherapistProfile.objects.select_for_update().get(pk=therapist_id)
        booking = Booking.objects.select_for_update().get(pk=receipt.booking_id)
        receipt = Receipt.objects.select_for_update().get(pk=receipt.pk)
        if booking.status != Booking.Status.AWAITING or receipt.status != Receipt.Status.SUBMITTED:
            return False
        receipt.status = Receipt.Status.REJECTED
        receipt.save(update_fields=["status"])
        slot_id = booking.slot_id
        booking.status = Booking.Status.CANCELLED
        booking.slot = None
        booking.save(update_fields=["status", "slot"])
        if slot_id:
            Slot.objects.filter(pk=slot_id).delete()
        rebuild_slots(profile)
        notify(
            booking.client,
            "رسید رد شد",
            "درمانگر این رسید را نپذیرفت. اگر وقت آزاد باشد می‌توانید دوباره رزرو کنید.",
            link=_event_link("client_payments", f"receipt-{receipt.pk}"),
            event_key=f"booking-{booking.pk}",
        )
    return True


def cancel_booking(booking, now=None, enforce_notice=True):
    now = now or timezone.now()
    if booking.status not in {Booking.Status.AWAITING, Booking.Status.CONFIRMED}:
        raise CancelError("این جلسه را نمی‌توان لغو کرد.")
    notice = timedelta(hours=booking.therapist.min_notice_hours)
    if enforce_notice and booking.starts_at - now < notice:
        raise CancelError("کمتر از حداقل زمان اطلاع قبلی مانده است.")
    receipt = Receipt.objects.filter(booking=booking).first()
    paid = receipt is not None and receipt.status == Receipt.Status.ACCEPTED
    with transaction.atomic():
        slot_id = booking.slot_id
        booking.status = Booking.Status.REFUNDED if paid else Booking.Status.CANCELLED
        booking.slot = None
        booking.save(update_fields=["status", "slot"])
        if slot_id:
            Slot.objects.filter(pk=slot_id).delete()
        if receipt is not None:
            receipt.status = Receipt.Status.REFUNDED if paid else Receipt.Status.REJECTED
            receipt.save(update_fields=["status"])
        rebuild_slots(booking.therapist, now=now)
        if paid:
            text = "جلسه لغو شد و مبلغ آن بازپرداخت می‌شود. وقت دوباره آزاد است."
        else:
            text = "جلسه لغو شد و وقت دوباره آزاد است."
        notify(
            booking.client,
            "جلسه لغو شد",
            text,
            link=_event_link("client_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
        notify(
            booking.therapist.user,
            "جلسه لغو شد",
            text,
            link=_event_link("therapist_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
        booking_id = booking.pk
    _sync_calendar(booking_id, publish=False)
    return Booking.objects.get(pk=booking_id)


def complete_booking(booking, now=None):
    now = now or timezone.now()
    if booking.status != Booking.Status.CONFIRMED:
        raise CancelError("فقط جلسهٔ تأییدشده را می‌توان انجام‌شده کرد.")
    if booking.starts_at > now:
        raise CancelError("هنوز زمان جلسه نرسیده است.")
    booking.status = Booking.Status.COMPLETED
    booking.save(update_fields=["status"])
    return booking


def refund_future_bookings(profile, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        profile = TherapistProfile.objects.select_for_update().get(pk=profile.pk)
        count = _refund_locked_profile(profile, now)
        event_ids = list(
            profile.bookings.exclude(google_event_id="").filter(
                status__in=[Booking.Status.CANCELLED, Booking.Status.REFUNDED]
            ).values_list("pk", flat=True)
        )
    for booking_id in event_ids:
        _sync_calendar(booking_id, publish=False)
    return count


def _refund_locked_profile(profile, now):
    bookings = list(
        profile.bookings.select_for_update()
        .filter(
            starts_at__gt=now,
            status__in=[Booking.Status.AWAITING, Booking.Status.CONFIRMED],
        )
        .select_related("client")
    )
    for booking in bookings:
        receipt = Receipt.objects.filter(booking=booking).first()
        slot_id = booking.slot_id
        booking.status = Booking.Status.REFUNDED
        booking.slot = None
        booking.save(update_fields=["status", "slot"])
        if slot_id:
            Slot.objects.filter(pk=slot_id).delete()
        if receipt is not None and receipt.status != Receipt.Status.REFUNDED:
            receipt.status = Receipt.Status.REFUNDED
            receipt.save(update_fields=["status"])
        notify(
            booking.client,
            "رزرو لغو شد",
            "حساب درمانگر تعلیق شد و مبلغ این جلسه بازپرداخت می‌شود.",
            link=_event_link("client_sessions", f"booking-{booking.pk}"),
            event_key=f"booking-{booking.pk}",
        )
    profile.slots.filter(starts_at__gt=now).delete()
    notify(
        profile.user,
        "حساب تعلیق شد",
        f"{len(bookings)} رزرو آینده لغو و بازپرداخت شد.",
        link=reverse("therapist_income"),
        event_key="account",
    )
    return len(bookings)


def rebuild_slots(profile, now=None):
    now = now or timezone.now()
    if profile.status != TherapistProfile.Status.APPROVED:
        profile.slots.filter(status=Slot.Status.OPEN).delete()
        return 0
    zone = ZoneInfo(profile.timezone)
    horizon = now + timedelta(days=profile.horizon_days)
    notice = now + timedelta(hours=profile.min_notice_hours)
    protected = list(
        profile.slots.filter(status__in=[Slot.Status.HELD, Slot.Status.BOOKED]).values_list("starts_at", "ends_at")
    )
    profile.slots.filter(status=Slot.Status.OPEN).delete()
    taken = set(profile.slots.values_list("starts_at", flat=True))
    closed_days = set()
    closed_hours = set()
    for closure in profile.closures.all():
        if closure.start is None:
            closed_days.add(closure.date)
        else:
            closed_hours.add((closure.date, closure.start))
    gap = timedelta(minutes=profile.gap_minutes)
    step = timedelta(minutes=SLOT_MINUTES)
    allowed_starts = set(grid_starts())
    cells = [cell for cell in profile.cells.all() if cell.start in allowed_starts]
    start_day = timezone.localtime(now, zone).date()
    last_day = timezone.localtime(horizon, zone).date()
    new_slots = []
    day = start_day
    while day <= last_day:
        if day not in closed_days:
            for cell in cells:
                if cell.weekday != day.weekday() or (day, cell.start) in closed_hours:
                    continue
                starts = datetime.combine(day, cell.start, tzinfo=zone)
                ends = starts + step
                if starts < notice or starts >= horizon or starts in taken:
                    continue
                if any(
                    starts < protected_end + gap and ends > protected_start - gap
                    for protected_start, protected_end in protected
                ):
                    continue
                new_slots.append(Slot(profile=profile, starts_at=starts, ends_at=ends, status=Slot.Status.OPEN))
                taken.add(starts)
        day += timedelta(days=1)
    Slot.objects.bulk_create(new_slots, ignore_conflicts=True)
    return len(new_slots)


def handle_status_change(profile, previous):
    if previous == profile.status:
        return
    with transaction.atomic():
        if profile.status == TherapistProfile.Status.SUSPENDED:
            refund_future_bookings(profile)
        if profile.status == TherapistProfile.Status.APPROVED:
            rebuild_slots(profile)
        else:
            profile.slots.filter(status=Slot.Status.OPEN).delete()


def replace_cells(profile, chosen):
    with transaction.atomic():
        profile.cells.all().delete()
        AvailabilityCell.objects.bulk_create(
            [AvailabilityCell(profile=profile, weekday=day, start=start) for day, start in sorted(chosen)]
        )
    return rebuild_slots(profile)


def add_closure(profile, day, start):
    if start is None:
        profile.closures.filter(date=day).delete()
        AvailabilityClosure.objects.create(profile=profile, date=day, start=None)
    elif not profile.closures.filter(date=day, start__isnull=True).exists():
        AvailabilityClosure.objects.get_or_create(profile=profile, date=day, start=start)
    return rebuild_slots(profile)


def record_mood(user, emoji, word):
    MoodLog.objects.update_or_create(
        client=user,
        logged_on=timezone.localdate(),
        defaults={"emoji": emoji, "word": word},
    )
    name = user.get_full_name() or user.get_username()
    for link in user.care_links.select_related("therapist__user"):
        notify(
            link.therapist.user,
            "حال مراجع",
            f"{name}: {emoji} {word}",
            link=reverse("therapist_crm", args=[user.pk]),
            event_key=f"mood-{user.pk}",
        )


def ensure_daily_card(user, today=None):
    today = today or timezone.localdate()
    kind, title, body, reward = DAILY_CARDS[today.toordinal() % len(DAILY_CARDS)]
    task, _created = Task.objects.get_or_create(
        client=user,
        therapist=None,
        due_on=today,
        defaults={"kind": kind, "title": title, "body": body, "reward": reward},
    )
    return task


def income_groups(profile):
    receipts = Receipt.objects.filter(booking__therapist=profile).select_related("booking__client")
    received = receipts.filter(
        status=Receipt.Status.ACCEPTED,
        booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
    )
    pending = receipts.filter(status=Receipt.Status.SUBMITTED, booking__status=Booking.Status.AWAITING)
    refunded = receipts.filter(status=Receipt.Status.REFUNDED)
    totals = received.values("booking__currency").annotate(total=Sum("amount")).order_by("booking__currency")
    return {
        "received": received.order_by("-created_at"),
        "pending": pending.order_by("-created_at"),
        "refunded": refunded.order_by("-created_at"),
        "totals": [
            {"label": format_money_currency(row["total"], row["booking__currency"]), "currency": row["booking__currency"]}
            for row in totals
        ],
    }


def format_money_currency(amount, currency):
    from therapy.choices import format_money

    return format_money(amount, currency)


def slot_when(slot):
    zone = ZoneInfo(slot.profile.timezone)
    local = timezone.localtime(slot.starts_at, zone)
    return f"{format_jalali(local)} ساعت {local.strftime('%H:%M')}"

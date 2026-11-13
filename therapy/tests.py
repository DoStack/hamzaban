from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from therapy.calendar import (
    add_business_days,
    format_jalali,
    gregorian_to_jalali,
    grid_starts,
    jalali_to_gregorian,
    latin_digits,
    month_bounds,
    month_length,
    month_weeks,
    parse_jalali_date,
    shift_month,
)
from therapy.directory_import import directory_slugs, parse_profile
from therapy.factories import make_client, make_profile, registration_data
from therapy.models import (
    AvailabilityCell,
    AvailabilityClosure,
    Booking,
    MoodLog,
    Notification,
    Receipt,
    Slot,
    Task,
    TherapistProfile,
)
from therapy.forms import TherapistRegistrationForm
from therapy.services import (
    CancelError,
    SlotTaken,
    accept_receipt,
    book_slot,
    cancel_booking,
    public_therapists,
    rebuild_slots,
    reject_receipt,
    review_is_late,
)


class DirectoryImportTests(TestCase):
    def test_profile_page_keeps_the_public_details(self):
        html = """
        <main>
          <h1>انوشه امین‌زاده</h1>
          <div class="muted">درمانگر زوج و فردی</div>
          <span class="pill warn">پیش‌نویس — منتظر تأیید</span>
          <div class="tags"><span class="pill gray">افسردگی</span><span class="pill gray">اضطراب</span></div>
          <p>روانشناس با دکترای روانشناسی.</p>
          <table><tr><th>تحصیلات</th><td>دانشگاه تهران</td></tr>
          <tr><th>شماره‌ی نظام</th><td>پروانه نظام روانشناسی شماره ۳۱۱۸</td></tr></table>
          <img class="avatar lg" src="/therapists/anoosheh-aminzadeh.jpg" alt="">
          <input name="zone" value="America/Toronto">
          <input name="startsAt" value="2026-11-14T13:30:00.000Z">
          $<!-- -->25
        </main>
        """
        record = parse_profile(html, "anoosheh-aminzadeh")
        self.assertEqual(record["display_name"], "انوشه امین‌زاده")
        self.assertEqual(record["license_number"], "3118")
        self.assertEqual(record["license_type"], "psychology")
        self.assertIn("خلق", record["specialties"])
        self.assertIn("دانشگاه تهران", record["introduction"])
        self.assertNotIn("hamzaban.bigde.li", record["introduction"])
        self.assertEqual(record["session_price"], "25")
        self.assertEqual(record["cells"], [(5, time(8, 30))])
        self.assertEqual(directory_slugs('<a href="/therapists/anoosheh-aminzadeh">x</a><a href="/therapists/a.jpg">'), ["anoosheh-aminzadeh"])


class CalendarTests(TestCase):
    def test_nowruz_2026_is_the_first_of_farvardin(self):
        self.assertEqual(gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
        self.assertEqual(jalali_to_gregorian(1405, 1, 1), (2026, 3, 21))

    def test_iranian_business_days_skip_thursday_and_friday(self):
        self.assertEqual(add_business_days(date(2026, 11, 7), 2), date(2026, 11, 9))
        self.assertEqual(add_business_days(date(2026, 11, 12), 2), date(2026, 11, 15))

    def test_jalali_helpers_round_trip_months_and_digits(self):
        self.assertEqual(latin_digits("۱۴۰۵-۰۱-۰۱"), "1405-01-01")
        self.assertEqual(parse_jalali_date("۱۴۰۵-۰۱-۰۱"), date(2026, 3, 21))
        self.assertEqual(format_jalali(datetime(2026, 3, 21, 12, 0)), "1 فروردین 1405")
        self.assertIn(month_length(1403, 12), (29, 30))
        self.assertEqual(month_length(1405, 1), 31)
        self.assertEqual(shift_month(1404, 12, 1), (1405, 1))
        self.assertEqual(shift_month(1405, 1, -1), (1404, 12))
        start, end = month_bounds(1405, 1)
        self.assertEqual(start, date(2026, 3, 21))
        self.assertEqual(end, date(2026, 4, 21))
        self.assertTrue(all(len(week) == 7 for week in month_weeks(1405, 1)))
        self.assertEqual(grid_starts()[0], time(7, 0))
        self.assertEqual(grid_starts()[-1], time(22, 30))
        early = gregorian_to_jalali(1500, 6, 15)
        self.assertEqual(jalali_to_gregorian(*early), (1500, 6, 15))
        self.assertEqual(jalali_to_gregorian(*gregorian_to_jalali(2100, 1, 1)), (2100, 1, 1))
        with self.assertRaises(ValueError):
            parse_jalali_date("nope")
        with self.assertRaises(ValueError):
            parse_jalali_date("1404-13-01")


class SlotTests(TestCase):
    def test_rebuild_respects_notice_closure_and_gap(self):
        profile = make_profile(with_hours=False)
        for start in (time(10, 0), time(10, 30), time(11, 0)):
            AvailabilityCell.objects.create(profile=profile, weekday=0, start=start)
        AvailabilityClosure.objects.create(profile=profile, date=date(2026, 11, 16))
        AvailabilityClosure.objects.create(profile=profile, date=date(2026, 11, 23), start=time(11, 0))
        TherapistProfile.objects.filter(pk=profile.pk).update(status=TherapistProfile.Status.APPROVED)
        profile.refresh_from_db()
        zone = ZoneInfo("Asia/Tehran")
        now = datetime(2026, 11, 9, 9, 0, tzinfo=zone)
        Slot.objects.create(
            profile=profile,
            starts_at=datetime(2026, 11, 23, 10, 0, tzinfo=zone),
            ends_at=datetime(2026, 11, 23, 10, 30, tzinfo=zone),
            status=Slot.Status.BOOKED,
        )
        rebuild_slots(profile, now=now)
        starts = set(profile.slots.filter(status=Slot.Status.OPEN).values_list("starts_at", flat=True))

        self.assertNotIn(datetime(2026, 11, 9, 10, 0, tzinfo=zone), starts)
        self.assertFalse(any(item.astimezone(zone).date() == date(2026, 11, 16) for item in starts))
        self.assertNotIn(datetime(2026, 11, 23, 10, 30, tzinfo=zone), starts)
        self.assertNotIn(datetime(2026, 11, 23, 11, 0, tzinfo=zone), starts)
        self.assertIn(datetime(2026, 11, 23, 10, 0, tzinfo=zone), set(profile.slots.values_list("starts_at", flat=True)))
        self.assertIn(datetime(2026, 11, 30, 10, 0, tzinfo=zone), starts)

    def test_only_approved_profiles_with_an_open_slot_are_public(self):
        pending = make_profile(
            username="pending",
            display_name="درمانگر در انتظار",
            status=TherapistProfile.Status.PENDING,
            with_hours=True,
        )
        approved = make_profile(
            username="open",
            display_name="درمانگر آزاد",
            status=TherapistProfile.Status.APPROVED,
            with_hours=True,
        )
        closed = make_profile(
            username="closed",
            display_name="درمانگر بدون وقت",
            status=TherapistProfile.Status.APPROVED,
            with_hours=False,
        )

        names = [item["name"] for item in self.client.get(reverse("api_therapists")).json()["therapists"]]

        self.assertIn(approved.display_name, names)
        self.assertNotIn(pending.display_name, names)
        self.assertNotIn(closed.display_name, names)
        self.assertEqual(self.client.get(reverse("therapist_detail", args=[pending.slug])).status_code, 404)

    def test_a_second_reserve_loses_and_cancel_reopens_the_slot(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED, with_hours=True)
        slot = profile.slots.filter(
            status=Slot.Status.OPEN,
            starts_at__gte=timezone.now() + timedelta(days=2),
        ).order_by("starts_at").first()
        first = make_client(username="one")
        second = make_client(username="two")

        booking = book_slot(slot, first, Decimal("500000"), "TR-1")
        with self.assertRaises(SlotTaken):
            book_slot(slot, second, Decimal("500000"), "TR-2")
        self.assertEqual(Booking.objects.count(), 1)

        self.client.force_login(profile.user)
        self.client.post(
            reverse("therapist_sessions"),
            {"action": "accept", "booking": booking.pk},
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertFalse(profile.slots.filter(starts_at=booking.starts_at, status=Slot.Status.OPEN).exists())

        self.client.force_login(first)
        self.client.post(reverse("client_sessions"), {"booking": booking.pk})
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.REFUNDED)
        self.assertTrue(profile.slots.filter(starts_at=booking.starts_at, status=Slot.Status.OPEN).exists())
        self.assertIn("بازپرداخت", self.client.get(reverse("api_client_payments")).content.decode())
        self.client.force_login(profile.user)
        self.assertIn("بازپرداخت", self.client.get(reverse("api_therapist_income")).content.decode())

    def test_late_cancel_keeps_the_booking(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED, with_hours=True)
        slot = profile.slots.order_by("starts_at").first()
        client = make_client()
        booking = book_slot(slot, client, Decimal("500000"), "TR-9")
        booking.starts_at = timezone.now() + timedelta(hours=1)
        booking.save(update_fields=["starts_at"])

        with self.assertRaises(CancelError):
            cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.AWAITING)


class ReceiptAccessTests(TestCase):
    def test_client_and_own_therapist_see_the_receipt_and_others_do_not(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED, with_hours=True)
        other = make_profile(username="other", status=TherapistProfile.Status.APPROVED, with_hours=True)
        client = make_client()
        slot = profile.slots.filter(status=Slot.Status.OPEN).first()
        booking = book_slot(
            slot,
            client,
            Decimal("500000"),
            "REC-1",
            SimpleUploadedFile("receipt.png", b"\x89PNG\r\n", content_type="image/png"),
        )

        self.client.force_login(client)
        page = self.client.get(reverse("api_client_payments"))
        self.assertContains(page, "REC-1")
        own_file = self.client.get(reverse("receipt_file", args=[booking.receipt.pk]))
        self.assertEqual(own_file.status_code, 200)

        self.client.force_login(profile.user)
        self.assertContains(self.client.get(reverse("api_therapist_sessions")), "REC-1")
        self.assertEqual(self.client.get(reverse("receipt_file", args=[booking.receipt.pk])).status_code, 200)

        self.client.force_login(other.user)
        denied = self.client.get(reverse("receipt_file", args=[booking.receipt.pk]))
        self.assertEqual(denied.status_code, 403)
        self.assertContains(denied, "دسترسی ندارید", status_code=403)


class TherapistPanelTests(TestCase):
    def test_added_student_gets_a_record_task_and_reward(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED, with_hours=True)
        self.client.force_login(profile.user)
        created = self.client.post(
            reverse("therapist_add_student"),
            {
                "first_name": "نیما",
                "username": "nima",
                "email": "nima@example.com",
                "password": "Safe-pass-48",
            },
        )
        student = get_user_model().objects.get(username="nima")
        self.assertRedirects(created, reverse("therapist_crm", args=[student.pk]))
        self.assertTrue(profile.students.filter(client=student).exists())

        self.client.post(
            reverse("therapist_tasks"),
            {
                "client": student.pk,
                "kind": "practice",
                "title": "تمرین تنفس",
                "body": "سه بار تکرار کن.",
                "reward": "یک ستاره",
                "due_on": timezone.localdate().isoformat(),
            },
        )
        self.client.force_login(student)
        reminders = self.client.get(reverse("api_client_notifications"))
        self.assertContains(reminders, "تمرین تنفس")
        self.assertContains(reminders, "یک ستاره")
        self.assertNotContains(reminders, "حال امروز")
        task = Task.objects.get(client=student, title="تمرین تنفس")
        done = self.client.post(reverse("client_complete_task", args=[task.pk]))
        self.assertRedirects(done, reverse("client_reminders"))
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)

    def test_caseload_filters_to_one_client_and_crm_is_private(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED)
        other = make_profile(username="other", status=TherapistProfile.Status.APPROVED)
        client = make_client()
        hidden = make_client(username="hidden", first_name="پنهان")
        profile.students.create(client=client)
        other.students.create(client=hidden)
        MoodLog.objects.create(client=client, emoji="😔", word="سنگین", logged_on=timezone.localdate())
        MoodLog.objects.create(client=hidden, emoji="😊", word="سبک", logged_on=timezone.localdate())

        self.client.force_login(profile.user)
        everyone = self.client.get(reverse("api_therapist_caseload"))
        self.assertContains(everyone, "سنگین")
        self.assertNotContains(everyone, "سبک")
        one = self.client.get(reverse("api_therapist_caseload"), {"client": client.pk})
        self.assertContains(one, "سنگین")
        missing = self.client.get(reverse("therapist_caseload"), {"client": hidden.pk})
        self.assertEqual(missing.status_code, 404)
        foreign = self.client.get(reverse("therapist_crm", args=[hidden.pk]))
        self.assertEqual(foreign.status_code, 404)

        record = self.client.post(
            reverse("therapist_crm", args=[client.pk]),
            {"notes": "یادداشت", "mind_map": "نقشه", "reports": "گزارش", "pre_session_summary": "خلاصه"},
        )
        self.assertRedirects(record, reverse("therapist_crm", args=[client.pk]))
        self.assertContains(self.client.get(reverse("api_therapist_crm", args=[client.pk])), "نقشه")

    def test_more_than_five_specialties_are_rejected(self):
        payload = registration_data(specialties=["اضطراب", "خلق", "رابطه", "تروما", "سوگ", "خواب"])
        payload["license_file"] = SimpleUploadedFile("license.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = self.client.post(reverse("therapist_register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حداکثر ۵ تخصص")
        self.assertFalse(get_user_model().objects.filter(username="sara").exists())

    def test_rejection_needs_a_fixed_code_and_suspension_refunds(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED, with_hours=True)
        client = make_client()
        slot = profile.slots.filter(status=Slot.Status.OPEN).first()
        booking = book_slot(slot, client, Decimal("500000"), "PAY-1")
        accept_receipt(booking.receipt)
        profile.rejection_code = ""
        profile.status = TherapistProfile.Status.REJECTED
        with self.assertRaises(ValidationError):
            profile.full_clean()

        staff = get_user_model().objects.create_superuser("root", "root@example.com", "Safe-pass-48")
        self.client.force_login(staff)
        self.client.post(
            reverse("admin:therapy_therapistprofile_changelist"),
            {"action": "suspend_selected", "_selected_action": [str(profile.pk)]},
        )
        profile.refresh_from_db()
        booking.refresh_from_db()
        receipt = Receipt.objects.get(booking=booking)
        self.assertEqual(profile.status, TherapistProfile.Status.SUSPENDED)
        self.assertEqual(booking.status, Booking.Status.REFUNDED)
        self.assertEqual(receipt.status, Receipt.Status.REFUNDED)
        self.assertFalse(profile.slots.filter(status=Slot.Status.OPEN).exists())
        self.assertEqual(self.client.get(reverse("therapist_detail", args=[profile.slug])).status_code, 404)

    def test_old_pending_request_is_marked_late(self):
        profile = make_profile()
        TherapistProfile.objects.filter(pk=profile.pk).update(
            created_at=datetime(2020, 1, 4, tzinfo=ZoneInfo("Asia/Tehran"))
        )
        profile.refresh_from_db()
        self.assertTrue(review_is_late(profile, today=date(2020, 1, 8)))
        staff = get_user_model().objects.create_superuser("root", "root@example.com", "Safe-pass-48")
        self.client.force_login(staff)
        page = self.client.get(reverse("admin:therapy_therapistprofile_changelist"))
        self.assertContains(page, "دیرشده")
        self.assertContains(page, profile.display_name)


class CommandTests(TestCase):
    def test_nightly_command_rebuilds_open_slots(self):
        from django.core.management import call_command

        profile = make_profile(status=TherapistProfile.Status.APPROVED, with_hours=True)
        profile.slots.filter(status=Slot.Status.OPEN).delete()

        call_command("rebuild_slots")

        self.assertGreater(profile.slots.filter(status=Slot.Status.OPEN).count(), 0)


class PanelSmokeTests(TestCase):
    def setUp(self):
        self.profile = make_profile(
            username="open",
            display_name="درمانگر آزاد",
            status=TherapistProfile.Status.APPROVED,
            with_hours=True,
        )
        self.profile.photo = SimpleUploadedFile("face.png", b"\x89PNG\r\n", content_type="image/png")
        self.profile.save(update_fields=["photo"])
        self.client_user = make_client()
        self.later = timezone.now() + timedelta(days=2)

    def _open_slot(self):
        return self.profile.slots.filter(status=Slot.Status.OPEN, starts_at__gte=self.later).order_by("starts_at").first()

    def test_client_books_pays_and_uses_reminders(self):
        slot = self._open_slot()
        self.client.force_login(self.profile.user)
        blocked = self.client.get(reverse("book_slot", args=[self.profile.slug, slot.pk]))
        self.assertRedirects(blocked, reverse("therapist_detail", args=[self.profile.slug]))

        self.client.force_login(self.client_user)
        opened = self.client.get(reverse("book_slot", args=[self.profile.slug, slot.pk]))
        self.assertRedirects(opened, f"{reverse('therapist_detail', args=[self.profile.slug])}?slot={slot.pk}")
        page = self.client.get(reverse("api_book", args=[self.profile.slug, slot.pk]))
        self.assertEqual(page.json()["therapist"], "درمانگر آزاد")
        booked = self.client.post(
            reverse("book_slot", args=[self.profile.slug, slot.pk]),
            {
                "amount": "500000",
                "reference": "PAY-9",
                "attachment": SimpleUploadedFile("receipt.pdf", b"%PDF-1.4", content_type="application/pdf"),
                "note": "می‌خواهم دربارهٔ خواب حرف بزنیم.",
            },
        )
        self.assertRedirects(booked, reverse("client_payments"))
        booking = Booking.objects.get(client=self.client_user)
        self.assertEqual(booking.client_note, "می‌خواهم دربارهٔ خواب حرف بزنیم.")
        local = timezone.localtime(booking.starts_at)
        year, month, _day = gregorian_to_jalali(local.year, local.month, local.day)

        sessions = self.client.get(reverse("api_client_sessions"), {"year": year, "month": month})
        self.assertContains(sessions, "درمانگر آزاد")
        self.assertIn("next", sessions.json()["calendar"])
        self.assertEqual(self.client.get(reverse("api_client_sessions"), {"month": "0"}).status_code, 200)
        payments = self.client.get(reverse("api_client_payments"))
        self.assertContains(payments, "PAY-9")
        receipt = Receipt.objects.get(booking=booking)
        file_page = self.client.get(reverse("receipt_file", args=[receipt.pk]))
        self.assertEqual(file_page.status_code, 200)

        reminders = self.client.get(reverse("api_client_notifications"))
        self.assertContains(reminders, "رسید ثبت شد")
        self.assertContains(reminders, reverse("client_payments"))
        self.assertContains(reminders, format_jalali(timezone.localdate()))
        task = Task.objects.get(client=self.client_user, therapist=None)
        done = self.client.post(reverse("client_complete_task", args=[task.pk]))
        self.assertRedirects(done, reverse("client_reminders"))
        self.client.post(
            reverse("client_reminders"),
            {"action": "mood", "emoji": "😊", "word": "آرام"},
        )
        self.assertTrue(MoodLog.objects.filter(client=self.client_user, word="آرام").exists())
        self.client.post(reverse("client_reminders"), {"action": "telegram", "telegram_username": "@hamzaban_user"})
        self.client_user.client_profile.refresh_from_db()
        self.assertEqual(self.client_user.client_profile.telegram_username, "hamzaban_user")
        self.client.post(reverse("client_reminders"), {"action": "telegram", "telegram_username": "no"})

        self.client.force_login(self.profile.user)
        self.client.post(reverse("therapist_sessions"), {"booking": booking.pk, "action": "accept"})
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        latest = Notification.objects.get(user=self.client_user, event_key=f"booking-{booking.pk}")
        self.assertEqual(latest.title, "رسید تأیید شد")
        self.assertIn(f"#booking-{booking.pk}", latest.link)
        self.assertEqual(Notification.objects.filter(user=self.client_user, event_key=f"booking-{booking.pk}").count(), 1)
        self.client.post(
            reverse("therapist_sessions"),
            {"booking": booking.pk, "action": "update", "meet_url": "https://meet.example/room", "summary": "خلاصه"},
        )
        self.client.post(reverse("therapist_sessions"), {"booking": booking.pk, "action": "complete"})
        booking.refresh_from_db()
        self.assertEqual(booking.summary, "خلاصه")
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

        self.client.force_login(self.client_user)
        cancelled = self.client.post(reverse("client_sessions"), {"booking": booking.pk})
        self.assertRedirects(cancelled, reverse("client_sessions"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.REFUNDED)

    def test_therapist_panel_pages_save(self):
        self.client.force_login(self.profile.user)
        for name in (
            "therapist_home",
            "therapist_students",
            "therapist_caseload",
            "therapist_tasks",
            "therapist_notifications",
            "therapist_income",
            "therapist_profile",
            "therapist_hours",
            "therapist_sessions",
        ):
            page = self.client.get(reverse(name))
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, 'src="/static/build/app.js"')
            self.assertContains(page, "app-shell")

        me = self.client.get(reverse("api_me")).json()
        self.assertEqual(me["photo"], reverse("therapist_photo", args=[self.profile.slug]))
        self.assertEqual(me["status_code"], self.profile.status.lower())
        self.assertEqual(me["status"], self.profile.get_status_display())

        plain = make_profile(username="nophoto", display_name="بدون عکس")
        self.client.force_login(plain.user)
        self.assertEqual(self.client.get(reverse("api_me")).json()["photo"], "")
        self.client.force_login(self.profile.user)

        photo = self.client.get(reverse("therapist_photo", args=[self.profile.slug]))
        self.assertEqual(photo.status_code, 200)
        license_page = self.client.get(reverse("therapist_license", args=[self.profile.pk]))
        self.assertEqual(license_page.status_code, 200)
        home = self.client.get(reverse("therapist_home"))
        self.assertContains(home, "app-shell")
        self.assertContains(home, "manifest.webmanifest?app=therapist")
        self.assertNotContains(home, "site-header")
        manifest = self.client.get(f"{reverse('manifest')}?app=client")
        self.assertEqual(manifest.json()["start_url"], "/profile/")
        self.assertEqual(manifest.json()["icons"][0]["sizes"], "192x192")
        self.assertEqual(self.client.get(f"{reverse('manifest')}?app=therapist").json()["start_url"], "/therapist/home/")
        self.assertEqual(self.client.get(reverse("service_worker")).status_code, 200)

        saved = self.client.post(
            reverse("therapist_profile"),
            {
                "display_name": self.profile.display_name,
                "gender": self.profile.gender,
                "languages": self.profile.languages,
                "years_experience": self.profile.years_experience,
                "license_type": self.profile.license_type,
                "license_number": self.profile.license_number,
                "license_country": self.profile.license_country,
                "specialties": self.profile.specialties,
                "education": ["کارشناسی ارشد"],
                "approach": self.profile.approach,
                "introduction": "معرفی به‌روز شده.",
                "currency": self.profile.currency,
                "session_price": self.profile.session_price,
                "timezone": self.profile.timezone,
            },
        )
        self.assertRedirects(saved, reverse("therapist_profile"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.introduction, "معرفی به‌روز شده.")
        self.assertEqual(self.profile.status, TherapistProfile.Status.APPROVED)

        hours = self.client.post(reverse("therapist_hours"), {"save-hours": "1", "cells": ["0-12:00", "nope"]})
        self.assertRedirects(hours, reverse("therapist_hours"))
        self.assertTrue(AvailabilityCell.objects.filter(profile=self.profile, weekday=0, start=time(12, 0)).exists())
        day = timezone.localdate() + timedelta(days=10)
        year, month, day_number = gregorian_to_jalali(day.year, day.month, day.day)
        closed = self.client.post(
            reverse("therapist_hours"),
            {"on": f"{year}-{month:02d}-{day_number:02d}", "all_day": "on"},
        )
        self.assertRedirects(closed, reverse("therapist_hours"))
        closure = self.profile.closures.get()
        removed = self.client.post(reverse("therapist_hours"), {"delete-closure": closure.pk})
        self.assertRedirects(removed, reverse("therapist_hours"))
        self.assertFalse(self.profile.closures.exists())

        from therapy.services import ensure_link

        link = ensure_link(self.profile, self.client_user)
        record = self.client.post(
            reverse("therapist_crm", args=[self.client_user.pk]),
            {
                "notes": "یادداشت",
                "mind_map": "نقشه",
                "reports": "گزارش",
                "pre_session_summary": "خلاصه قبل از جلسه",
            },
        )
        self.assertRedirects(record, reverse("therapist_crm", args=[self.client_user.pk]))
        link.record.refresh_from_db()
        self.assertEqual(link.record.pre_session_summary, "خلاصه قبل از جلسه")
        caseload = self.client.get(reverse("api_therapist_caseload"), {"client": self.client_user.pk})
        self.assertContains(caseload, self.client_user.first_name)

        stranger = make_client(username="other", first_name="دیگر")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(reverse("therapist_license", args=[self.profile.pk])).status_code, 403)


class BookingGuardTests(TestCase):
    def test_notice_window_and_session_gap_block_a_second_hold(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED)
        soon = timezone.now() + timedelta(hours=1)
        soon_slot = Slot.objects.create(
            profile=profile,
            starts_at=soon,
            ends_at=soon + timedelta(minutes=30),
            status=Slot.Status.OPEN,
        )
        client = make_client()
        with self.assertRaises(SlotTaken):
            book_slot(soon_slot, client, Decimal("500000"), "SOON")
        self.assertFalse(public_therapists().filter(pk=profile.pk).exists())
        self.client.force_login(client)
        self.assertEqual(self.client.get(reverse("book_slot", args=[profile.slug, soon_slot.pk])).status_code, 404)

        start = (timezone.now() + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
        first = Slot.objects.create(
            profile=profile,
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
            status=Slot.Status.OPEN,
        )
        second = Slot.objects.create(
            profile=profile,
            starts_at=start + timedelta(minutes=30),
            ends_at=start + timedelta(minutes=60),
            status=Slot.Status.OPEN,
        )
        booking = book_slot(first, client, Decimal("500000"), "GAP")
        with self.assertRaises(SlotTaken):
            book_slot(second, make_client(username="nima"), Decimal("500000"), "NEXT")
        self.assertTrue(accept_receipt(booking.receipt))
        self.assertFalse(reject_receipt(booking.receipt))
        booking.refresh_from_db()
        first.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(first.status, Slot.Status.BOOKED)

        profile.status = TherapistProfile.Status.SUSPENDED
        profile.save()
        later = start + timedelta(days=1)
        leftover = Slot.objects.create(
            profile=profile,
            starts_at=later,
            ends_at=later + timedelta(minutes=30),
            status=Slot.Status.OPEN,
        )
        with self.assertRaises(SlotTaken):
            book_slot(leftover, client, Decimal("500000"), "AFTER")

    def test_existing_account_is_not_attached_to_a_therapist(self):
        profile = make_profile(status=TherapistProfile.Status.APPROVED)
        other = make_client()
        self.client.force_login(profile.user)
        response = self.client.post(
            reverse("therapist_add_student"),
            {
                "first_name": "لیلا",
                "username": other.username,
                "email": other.email,
                "password": "Safe-pass-48",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(profile.students.filter(client=other).exists())

    def test_failed_profile_insert_does_not_keep_the_user(self):
        from unittest.mock import patch

        payload = registration_data(username="fresh", email="fresh@example.com")
        upload = SimpleUploadedFile("license.pdf", b"%PDF-1.4", content_type="application/pdf")
        form = TherapistRegistrationForm(payload, {"license_file": upload})
        self.assertTrue(form.is_valid(), form.errors)
        with patch("therapy.models.TherapistProfile.save", side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                form.save()
        self.assertFalse(get_user_model().objects.filter(username="fresh").exists())


class DatabaseStorageTests(TestCase):
    def test_license_upload_is_saved_without_a_folder(self):
        from django.core.files.base import ContentFile

        from therapy.storage import DatabaseStorage

        profile = make_profile()
        field = TherapistProfile._meta.get_field("license_file")
        original = field.storage
        storage = DatabaseStorage()
        field.storage = storage
        profile.__dict__.pop("license_file", None)
        try:
            profile.license_file.save("new.pdf", ContentFile(b"%PDF-new"), save=True)
            self.assertEqual(profile.license_file.read(), b"%PDF-new")
            self.assertTrue(storage.exists(profile.license_file.name))
        finally:
            field.storage = original

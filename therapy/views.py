import mimetypes
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from clients.views import render_spa
from therapy.access import client_only, forbid, therapist_only
from therapy.calendar import (
    MONTHS,
    WEEKDAY_NAMES,
    format_jalali,
    gregorian_to_jalali,
    month_bounds,
    month_weeks,
    shift_month,
)
from therapy.choices import DAY_LABELS, DISPLAY_DAYS, MOODS
from therapy.forms import (
    AddStudentForm,
    ClosureForm,
    MoodForm,
    ReceiptForm,
    RecordForm,
    SessionUpdateForm,
    TaskForm,
    TelegramForm,
    TherapistProfileForm,
)
from therapy.models import (
    Booking,
    ClientProfile,
    ClientRecord,
    MoodLog,
    Receipt,
    Slot,
    Task,
    TherapistProfile,
)
from therapy.services import (
    CancelError,
    SlotTaken,
    accept_receipt,
    add_closure,
    book_slot,
    cancel_booking,
    complete_booking,
    ensure_daily_card,
    record_mood,
    ensure_link,
    income_groups,
    notify,
    open_slots_by_day,
    public_profile,
    reject_receipt,
    replace_cells,
    slot_when,
)


def _parse_cells(values):
    from therapy.calendar import grid_starts

    allowed = set(grid_starts())
    chosen = set()
    for value in values:
        try:
            day_text, time_text = value.split("-", 1)
            day = int(day_text)
            hour, minute = (int(part) for part in time_text.split(":"))
            start = time(hour, minute)
        except (ValueError, TypeError):
            continue
        if day in range(7) and start in allowed:
            chosen.add((day, start))
    return chosen


def _hour_grid(profile):
    from therapy.calendar import grid_starts

    selected = {(cell.weekday, cell.start) for cell in profile.cells.all()}
    rows = []
    for start in grid_starts():
        label = start.strftime("%H:%M")
        rows.append(
            {
                "time": label,
                "cells": [
                    {"value": f"{day}-{label}", "checked": (day, start) in selected}
                    for day in DISPLAY_DAYS
                ],
            }
        )
    return rows


def _local_pair(moment, zone_name):
    local = timezone.localtime(moment, ZoneInfo(zone_name))
    return format_jalali(local), local.strftime("%H:%M")


def _can_read_receipt(user, receipt):
    booking = receipt.booking
    return user.is_staff or user.id == booking.client_id or user.id == booking.therapist.user_id


@require_GET
def therapist_photo(request, slug):
    profile = get_object_or_404(TherapistProfile, slug=slug)
    if not profile.photo:
        raise Http404("عکسی ثبت نشده است.")
    content_type = mimetypes.guess_type(profile.photo.name)[0] or "application/octet-stream"
    return FileResponse(profile.photo.open("rb"), content_type=content_type)


@login_required
@require_GET
def license_file(request, pk):
    profile = get_object_or_404(TherapistProfile, pk=pk)
    if not (request.user.is_staff or request.user.id == profile.user_id):
        return forbid(request)
    if not profile.license_file:
        raise Http404("مجوزی ثبت نشده است.")
    name = Path(profile.license_file.name).name
    return FileResponse(profile.license_file.open("rb"), as_attachment=True, filename=name)


@login_required
@require_GET
def receipt_file(request, pk):
    receipt = get_object_or_404(Receipt.objects.select_related("booking__therapist__user"), pk=pk)
    if not _can_read_receipt(request.user, receipt):
        return forbid(request)
    if not receipt.attachment:
        raise Http404("فایلی برای این رسید نیست.")
    name = Path(receipt.attachment.name).name
    return FileResponse(receipt.attachment.open("rb"), as_attachment=True, filename=name)


@login_required
@require_http_methods(["GET", "POST"])
def book(request, slug, slot_id):
    with translation.override("fa"):
        profile = public_profile(slug)
        if profile is None:
            raise Http404("درمانگر پیدا نشد.")
        slot = get_object_or_404(
            profile.slots,
            pk=slot_id,
            status=Slot.Status.OPEN,
            starts_at__gte=timezone.now() + timedelta(hours=profile.min_notice_hours),
        )
        if request.user.id == profile.user_id or request.user.groups.filter(name="therapist").exists():
            messages.error(request, "رزرو از حساب درمانگر انجام نمی‌شود.")
            return redirect("therapist_detail", slug=slug)
        form = ReceiptForm(request.POST or None, request.FILES or None, initial={"amount": profile.session_price})
        if request.method == "POST" and form.is_valid():
            try:
                book_slot(
                    slot,
                    request.user,
                    form.cleaned_data["amount"],
                    form.cleaned_data["reference"],
                    form.cleaned_data.get("attachment"),
                    form.cleaned_data.get("note", ""),
                )
            except SlotTaken:
                messages.error(request, "این وقت همین حالا گرفته شد. وقت دیگری را انتخاب کنید.")
                return redirect("therapist_detail", slug=slug)
            messages.success(request, "رسید ثبت شد و درمانگر آن را می‌بیند.")
            return redirect("client_payments")
        if request.method == "GET":
            return redirect(f"{reverse('therapist_detail', args=[profile.slug])}?slot={slot.pk}")
        return render(
            request,
            "clients/book.html",
            {
                "form": form,
                "therapist": profile,
                "when": slot_when(slot),
                "notice": profile.min_notice_hours,
            },
        )


@client_only
@require_http_methods(["GET", "POST"])
def client_sessions(request):
    if request.method == "POST":
        booking = get_object_or_404(Booking, pk=request.POST.get("booking"), client=request.user)
        try:
            cancel_booking(booking)
        except CancelError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "جلسه لغو شد.")
        return redirect("client_sessions")

    return render_spa(request, "client")


@client_only
@require_GET
def client_payments(request):
    return render_spa(request, "client")


@client_only
@require_http_methods(["GET", "POST"])
def client_reminders(request):
    ensure_daily_card(request.user)
    profile, _created = ClientProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "mood":
            form = MoodForm(request.POST)
            if form.is_valid():
                record_mood(request.user, form.cleaned_data["emoji"], form.cleaned_data["word"])
                messages.success(request, "حال امروز ثبت شد.")
            else:
                messages.error(request, "حال امروز ذخیره نشد. یک حال و یک کلمه لازم است.")
        elif action == "telegram":
            form = TelegramForm(request.POST)
            if form.is_valid():
                profile.telegram_username = form.cleaned_data["telegram_username"]
                profile.save(update_fields=["telegram_username"])
                messages.success(request, "نام کاربری تلگرام ذخیره شد. اعلان‌ها همین حالا در برنامه می‌آیند.")
            else:
                messages.error(request, form.errors["telegram_username"][0])
        return redirect("client_reminders")

    return render_spa(request, "client")


@client_only
@require_POST
def complete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id, client=request.user)
    if task.completed_at is None:
        task.completed_at = timezone.now()
        task.save(update_fields=["completed_at"])
        if task.therapist_id:
            notify(
                task.therapist.user,
                "کار انجام شد",
                task.title,
                link=f"{reverse('therapist_tasks')}#task-{task.pk}",
                event_key=f"task-{task.pk}",
            )
        messages.success(request, task.reward or "انجام شد.")
    return redirect("client_reminders")


@therapist_only
@require_GET
def therapist_home(request):
    profile = request.therapist_profile
    zone = ZoneInfo(profile.timezone)
    now_local = timezone.localtime(timezone.now(), zone)
    start = datetime.combine(now_local.date(), time.min, tzinfo=zone)
    sessions = list(
        profile.bookings.filter(starts_at__gte=start, starts_at__lt=start + timedelta(days=1))
        .select_related("client")
        .order_by("starts_at")
    )
    records = {
        item.link.client_id: item
        for item in ClientRecord.objects.filter(
            link__therapist=profile,
            link__client_id__in=[item.client_id for item in sessions],
        ).select_related("link")
    }
    for booking in sessions:
        booking.prep = records.get(booking.client_id)
        booking.when_date, booking.when_time = _local_pair(booking.starts_at, profile.timezone)
    tasks = profile.assigned_tasks.filter(due_on=now_local.date()).select_related("client")
    return render_spa(request, "therapist")


@therapist_only
@require_GET
def therapist_notifications(request):
    notes = list(request.user.notifications.all()[:30])
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return render_spa(request, "therapist")


@therapist_only
@require_GET
def students(request):
    links = request.therapist_profile.students.select_related("client").order_by("client__first_name", "client__username")
    return render_spa(request, "therapist")


@therapist_only
@require_http_methods(["GET", "POST"])
def add_student(request):
    profile = request.therapist_profile
    form = AddStudentForm(profile, request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
            )
            ClientProfile.objects.create(user=user)
            ensure_link(profile, user)
        messages.success(request, "مراجع به فهرست شما اضافه شد.")
        return redirect("therapist_crm", user_id=user.pk)
    if request.method == "GET":
        return render_spa(request, "therapist")
    return render(request, "therapists/student_form.html", {"section": "students", "form": form})


@therapist_only
@require_GET
def caseload(request):
    profile = request.therapist_profile
    links = list(profile.students.select_related("client").order_by("client__first_name"))
    selected = None
    client_id = request.GET.get("client")
    if client_id:
        selected = get_object_or_404(profile.students.select_related("client"), client_id=client_id)
        client_ids = [selected.client_id]
    else:
        client_ids = [link.client_id for link in links]
    week = timezone.localdate() - timedelta(days=6)
    recent = MoodLog.objects.filter(client_id__in=client_ids, logged_on__gte=week).select_related("client")
    summary = {}
    logged_ids = set()
    for log in recent:
        summary[log.emoji] = summary.get(log.emoji, 0) + 1
        logged_ids.add(log.client_id)
    quiet = [link for link in links if link.client_id not in logged_ids]
    if selected is not None:
        quiet = [link for link in quiet if link.client_id == selected.client_id]
    logs = MoodLog.objects.filter(client_id__in=client_ids).select_related("client").order_by("-logged_on")[:40]
    return render_spa(request, "therapist")


@therapist_only
@require_http_methods(["GET", "POST"])
def crm(request, user_id):
    profile = request.therapist_profile
    link = get_object_or_404(profile.students.select_related("client"), client_id=user_id)
    if request.method == "GET":
        return render_spa(request, "therapist")
    record, _created = ClientRecord.objects.get_or_create(link=link)
    form = RecordForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پرونده ذخیره شد.")
        return redirect("therapist_crm", user_id=user_id)
    sessions = profile.bookings.filter(client_id=user_id).order_by("-starts_at")[:12]
    moods = MoodLog.objects.filter(client_id=user_id).order_by("-logged_on")[:14]
    return render(
        request,
        "therapists/crm.html",
        {
            "section": "students",
            "link": link,
            "form": form,
            "sessions": sessions,
            "moods": moods,
        },
    )


@therapist_only
@require_http_methods(["GET", "POST"])
def tasks(request):
    if request.method == "GET":
        return render_spa(request, "therapist")
    profile = request.therapist_profile
    form = TaskForm(profile, request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = Task.objects.create(
            therapist=profile,
            client=form.cleaned_data["client"],
            kind=form.cleaned_data["kind"],
            title=form.cleaned_data["title"],
            body=form.cleaned_data["body"],
            reward=form.cleaned_data["reward"],
            due_on=form.cleaned_data["due_on"],
        )
        text = task.body
        if task.reward:
            text = f"{task.body}\nپاداش: {task.reward}"
        notify(task.client, task.title, text, event_key=f"task-{task.pk}")
        messages.success(request, "کار برای مراجع ثبت شد.")
        return redirect("therapist_tasks")
    assigned = profile.assigned_tasks.select_related("client").order_by("-due_on", "-id")[:40]
    return render(
        request,
        "therapists/tasks.html",
        {"section": "tasks", "form": form, "tasks": assigned},
    )


@therapist_only
@require_GET
def income(request):
    groups = income_groups(request.therapist_profile)
    return render_spa(request, "therapist")


@therapist_only
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    if request.method == "GET":
        return render_spa(request, "therapist")
    profile = request.therapist_profile
    was = profile.status
    form = TherapistProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        uploaded_license = bool(request.FILES.get("license_file"))
        if was == TherapistProfile.Status.REJECTED or (
            uploaded_license and was == TherapistProfile.Status.APPROVED
        ):
            updated.status = TherapistProfile.Status.PENDING
            updated.rejection_code = ""
            updated.reviewed_at = None
            messages.success(request, "ذخیره شد و درخواست دوباره در صف بررسی است.")
        else:
            messages.success(request, "پروفایل ذخیره شد.")
        updated.save()
        return redirect("therapist_profile")
    return render(
        request,
        "therapists/profile.html",
        {"section": "profile", "form": form, "profile": profile},
    )


@therapist_only
@require_http_methods(["GET", "POST"])
def hours(request):
    if request.method == "GET":
        return render_spa(request, "therapist")
    profile = request.therapist_profile
    form = ClosureForm()
    if request.method == "POST" and "save-hours" in request.POST:
        replace_cells(profile, _parse_cells(request.POST.getlist("cells")))
        messages.success(request, "ساعت‌ها ذخیره شد و وقت‌های ۳۰ روز آینده دوباره ساخته شد.")
        return redirect("therapist_hours")
    if request.method == "POST" and "delete-closure" in request.POST:
        profile.closures.filter(pk=request.POST.get("delete-closure")).delete()
        from therapy.services import rebuild_slots

        rebuild_slots(profile)
        messages.success(request, "استثنا حذف شد.")
        return redirect("therapist_hours")
    if request.method == "POST":
        form = ClosureForm(request.POST)
        if form.is_valid():
            add_closure(profile, form.cleaned_data["day"], form.cleaned_data["start_time"])
            messages.success(request, "استثنا ثبت شد.")
            return redirect("therapist_hours")
    closures = []
    for item in profile.closures.all():
        label = format_jalali(item.date)
        label += "، همهٔ روز" if item.start is None else f"، ساعت {item.start.strftime('%H:%M')}"
        closures.append({"id": item.pk, "label": label})
    return render(
        request,
        "therapists/hours.html",
        {
            "section": "hours",
            "profile": profile,
            "day_names": [DAY_LABELS[day] for day in DISPLAY_DAYS],
            "rows": _hour_grid(profile),
            "form": form,
            "closures": closures,
            "open_count": profile.slots.filter(status=Slot.Status.OPEN, starts_at__gte=timezone.now()).count(),
        },
    )


@therapist_only
@require_http_methods(["GET", "POST"])
def therapist_sessions(request):
    profile = request.therapist_profile
    if request.method == "GET":
        return render_spa(request, "therapist")
    if request.method == "POST":
        booking = get_object_or_404(Booking, pk=request.POST.get("booking"), therapist=profile)
        action = request.POST.get("action")
        if action == "accept" and hasattr(booking, "receipt"):
            if accept_receipt(booking.receipt):
                messages.success(request, "رسید تأیید شد.")
            else:
                messages.error(request, "این رسید دیگر قابل تأیید نیست.")
        elif action == "reject" and hasattr(booking, "receipt"):
            if reject_receipt(booking.receipt):
                messages.success(request, "رسید رد شد و وقت آزاد شد.")
            else:
                messages.error(request, "این رسید دیگر قابل رد نیست.")
        elif action == "cancel":
            try:
                cancel_booking(booking, enforce_notice=False)
            except CancelError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "جلسه لغو شد.")
        elif action == "complete":
            try:
                complete_booking(booking)
            except CancelError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "جلسه انجام‌شده شد.")
        elif action == "update":
            form = SessionUpdateForm(request.POST)
            if form.is_valid():
                booking.meet_url = form.cleaned_data["meet_url"]
                booking.summary = form.cleaned_data["summary"]
                booking.save(update_fields=["meet_url", "summary"])
                messages.success(request, "جلسه به‌روز شد.")
            else:
                messages.error(request, "پیوند جلسه معتبر نیست.")
        return redirect("therapist_sessions")

    bookings = list(profile.bookings.select_related("client", "receipt").order_by("starts_at"))
    for booking in bookings:
        booking.when_date, booking.when_time = _local_pair(booking.starts_at, profile.timezone)
    upcoming = [item for item in bookings if item.starts_at >= timezone.now()]
    earlier = [item for item in bookings if item.starts_at < timezone.now()]
    return render(
        request,
        "therapists/sessions.html",
        {"section": "sessions", "upcoming": upcoming, "earlier": list(reversed(earlier))},
    )


def manifest(request):
    from django.http import JsonResponse

    app = request.GET.get("app")
    if app == "client":
        name, start = "هم‌زبان مراجع", "/profile/"
    elif app == "therapist":
        name, start = "هم‌زبان درمانگر", "/therapist/home/"
    else:
        name, start = "هم‌زبان", "/"
    icons = [
        {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ]
    return JsonResponse(
        {
            "id": start,
            "name": name,
            "short_name": "هم‌زبان",
            "start_url": start,
            "scope": "/",
            "display": "standalone",
            "dir": "rtl",
            "lang": "fa",
            "background_color": "#f5f7f8",
            "theme_color": "#3AA58C",
            "icons": icons,
        },
        json_dumps_params={"ensure_ascii": False},
    )


def service_worker(request):
    response = FileResponse((Path(settings.BASE_DIR) / "static" / "sw.js").open("rb"), content_type="text/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response

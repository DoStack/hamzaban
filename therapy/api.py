import json
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone, translation
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from clients.catalog import FAQS, STATS, THERAPIST_FAQS, THERAPIST_STATS, THERAPIST_STEPS
from clients.forms import ClientRegistrationForm
from clients.views import account_home
from therapy.access import is_therapist
from therapy.calendar import MONTHS, WEEKDAY_NAMES, format_jalali, gregorian_to_jalali, month_bounds, month_weeks, shift_month
from therapy.choices import SLOT_MINUTES
from therapy.choices import (
    APPROACHES,
    CURRENCIES,
    EDUCATION_CHOICES,
    DAY_LABELS,
    DISPLAY_DAYS,
    GENDERS,
    LANGUAGE_CHOICES,
    LICENSE_TYPES,
    MOODS,
    SPECIALTY_CHOICES,
    TIMEZONES,
)
from therapy.forms import (
    AddStudentForm,
    MoodForm,
    TelegramForm,
    ClosureForm,
    ReceiptForm,
    RecordForm,
    SessionUpdateForm,
    TaskForm,
    TherapistProfileForm,
    TherapistRegistrationForm,
)
from therapy.models import Booking, ClientProfile, ClientRecord, MoodLog, Receipt, Slot, Task, TherapistProfile
from therapy.services import (
    CancelError,
    SlotTaken,
    accept_receipt,
    add_closure,
    booking_weeks,
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
    search_public_therapists,
    slot_when,
)
from therapy.views import _hour_grid, _local_pair, _parse_cells


def _json(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def _ok(**data):
    return _json({"ok": True, **data})


def _fail(message, status=400, errors=None):
    return _json({"ok": False, "message": message, "errors": errors or {}}, status=status)


def _body(request):
    if request.content_type.startswith("application/json"):
        try:
            raw = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            raw = {}
        query = QueryDict(mutable=True)
        for key, value in raw.items():
            if isinstance(value, list):
                query.setlist(key, [str(item) for item in value])
            elif isinstance(value, bool):
                if value:
                    query[key] = "on"
            elif value is not None:
                query[key] = str(value)
        return query
    return request.POST


def _form_fail(form):
    errors = {key: value[0] for key, value in form.errors.items()}
    message = errors.get("__all__") or next(iter(errors.values()), "اطلاعات کامل نیست.")
    return _fail(message, errors=errors)


def _choices(pairs):
    return [{"value": value, "label": label} for value, label in pairs]


def _client_required(view):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _fail("برای این بخش وارد شوید.", 401)
        if is_therapist(request.user):
            return _fail("این بخش برای حساب مراجع است.", 403)
        with translation.override("fa"):
            return view(request, *args, **kwargs)

    return wrapped


def _therapist_required(view):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _fail("برای این بخش وارد شوید.", 401)
        if not is_therapist(request.user):
            return _fail("این بخش برای حساب درمانگر است.", 403)
        try:
            request.therapist_profile = request.user.therapist_profile
        except TherapistProfile.DoesNotExist:
            return _fail("پروفایل درمانگر هنوز ساخته نشده است.", 409)
        with translation.override("fa"):
            return view(request, *args, **kwargs)

    return wrapped


def _person(user):
    return user.get_full_name() or user.get_username()


def _when(moment, zone_name):
    date_label, clock = _local_pair(moment, zone_name)
    return date_label, clock


def _therapist_card(profile):
    return {
        "slug": profile.slug,
        "name": profile.display_name,
        "approach": profile.get_approach_display(),
        "price": profile.price_label,
        "photo": reverse("therapist_photo", args=[profile.slug]) if profile.photo else "",
        "specialties": profile.specialties or [],
        "education": profile.education or [],
        "years": profile.years_experience,
        "gender": profile.get_gender_display(),
        "timezone": profile.timezone,
        "timezone_label": profile.get_timezone_display(),
        "languages": profile.languages or [],
        "license_type": profile.get_license_type_display(),
        "license_number": profile.license_number,
        "license_country": profile.license_country,
        "phone": profile.phone,
        "introduction": profile.introduction,
    }


def _note(note):
    local = timezone.localtime(note.created_at)
    unread = note.read_at is None
    return {
        "id": note.pk,
        "title": note.title,
        "body": note.body,
        "link": note.link,
        "when": f"{format_jalali(local)}، {local.strftime('%H:%M')}",
        "status": "unread" if unread else "read",
        "status_label": "خوانده‌نشده" if unread else "خوانده‌شده",
    }


def _mark_read(user):
    user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())


@require_GET
@ensure_csrf_cookie
def me(request):
    user = request.user
    if not user.is_authenticated:
        return _ok(authenticated=False)
    photo = ""
    status = ""
    status_code = ""
    if is_therapist(user):
        profile = getattr(user, "therapist_profile", None)
        if profile is not None:
            status = profile.get_status_display()
            status_code = profile.status.lower()
            if profile.photo:
                photo = reverse("therapist_photo", args=[profile.slug])
    return _ok(
        authenticated=True,
        is_therapist=is_therapist(user),
        is_staff=user.is_staff,
        name=_person(user),
        username=user.get_username(),
        photo=photo,
        status=status,
        status_code=status_code,
        home=reverse(account_home(user)),
    )


@require_POST
def login_api(request):
    data = _body(request)
    user = authenticate(request, username=data.get("username", ""), password=data.get("password", ""))
    if user is None:
        return _fail("نام کاربری یا گذرواژه درست نیست.", 400)
    login(request, user)
    nxt = data.get("next") or reverse(account_home(user))
    if not str(nxt).startswith("/"):
        nxt = reverse(account_home(user))
    return _ok(next=nxt)


@require_POST
def logout_api(request):
    logout(request)
    return _ok(next=reverse("home"))


@require_http_methods(["GET", "POST"])
def register_api(request):
    if request.user.is_authenticated:
        return _ok(next=reverse(account_home(request.user)))
    if request.method == "GET":
        return _ok()
    with translation.override("fa"):
        form = ClientRegistrationForm(_body(request))
        if not form.is_valid():
            return _form_fail(form)
        login(request, form.save())
    return _ok(next=reverse("client_profile"))


@require_http_methods(["GET", "POST"])
def therapist_register_api(request):
    if request.user.is_authenticated:
        return _ok(next=reverse(account_home(request.user)))
    if request.method == "GET":
        return _ok(options=_option_payload())
    with translation.override("fa"):
        form = TherapistRegistrationForm(request.POST, request.FILES)
        if not form.is_valid():
            return _form_fail(form)
        login(request, form.save())
    return _ok(next=reverse("therapist_home"))


def _option_payload():
    return {
        "genders": _choices(GENDERS),
        "languages": _choices(LANGUAGE_CHOICES),
        "specialties": _choices(SPECIALTY_CHOICES),
        "education": _choices(EDUCATION_CHOICES),
        "approaches": _choices(APPROACHES),
        "licenses": _choices(LICENSE_TYPES),
        "currencies": _choices(CURRENCIES),
        "timezones": _choices(TIMEZONES),
    }


@require_GET
def home_api(request):
    if request.GET.get("app") == "therapist":
        return _ok(stats=list(THERAPIST_STATS), faqs=list(THERAPIST_FAQS), steps=list(THERAPIST_STEPS))
    return _ok(stats=list(STATS), faqs=list(FAQS))


@require_GET
def therapists_api(request):
    query = request.GET.get("q", "").strip()
    return _ok(query=query, therapists=[_therapist_card(item) for item in search_public_therapists(query)])


@require_GET
def therapist_detail_api(request, slug):
    profile = public_profile(slug)
    if profile is None:
        return _fail("درمانگر پیدا نشد.", 404)
    return _ok(
        therapist=_therapist_card(profile),
        days=open_slots_by_day(profile),
        weeks=booking_weeks(profile),
        duration=f"{str(SLOT_MINUTES).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))} دقیقه",
        notice=profile.min_notice_hours,
        can_book=request.user.is_authenticated and not is_therapist(request.user),
        is_therapist=is_therapist(request.user),
    )


@require_http_methods(["GET", "POST"])
def book_api(request, slug, slot_id):
    if not request.user.is_authenticated:
        return _fail("برای رزرو وارد شوید.", 401)
    if is_therapist(request.user):
        return _fail("رزرو از حساب درمانگر انجام نمی‌شود.", 403)
    profile = public_profile(slug)
    if profile is None:
        return _fail("درمانگر پیدا نشد.", 404)
    slot = profile.slots.filter(
        pk=slot_id,
        status=Slot.Status.OPEN,
        starts_at__gte=timezone.now() + timedelta(hours=profile.min_notice_hours),
    ).first()
    if slot is None:
        return _fail("این وقت دیگر آزاد نیست.", 404)
    if request.method == "GET":
        return _ok(therapist=profile.display_name, when=slot_when(slot), amount=str(profile.session_price), notice=profile.min_notice_hours)
    with translation.override("fa"):
        form = ReceiptForm(request.POST, request.FILES, initial={"amount": profile.session_price})
        if not form.is_valid():
            return _form_fail(form)
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
            return _fail("این وقت همین حالا گرفته شد. وقت دیگری را انتخاب کنید.", 409)
    return _ok(next=reverse("client_payments"), message="رسید ثبت شد و درمانگر آن را می‌بیند.")


def _client_calendar(user, year, month):
    today = timezone.localdate()
    jy, jm, _jd = gregorian_to_jalali(today.year, today.month, today.day)
    try:
        jy = int(year or jy)
        jm = int(month or jm)
        if not 1 <= jm <= 12:
            raise ValueError
    except (TypeError, ValueError):
        jy, jm, _jd = gregorian_to_jalali(today.year, today.month, today.day)
    start, end = month_bounds(jy, jm)
    zone = ZoneInfo(settings.TIME_ZONE)
    bookings = Booking.objects.filter(
        client=user,
        starts_at__gte=datetime.combine(start, time.min, tzinfo=zone),
        starts_at__lt=datetime.combine(end, time.min, tzinfo=zone),
    ).select_related("therapist")
    by_day = {}
    for booking in bookings:
        local = timezone.localtime(booking.starts_at)
        _year, _month, day = gregorian_to_jalali(local.year, local.month, local.day)
        by_day.setdefault(day, []).append(
            {"time": local.strftime("%H:%M"), "status": booking.status.lower(), "label": booking.get_status_display(), "name": booking.therapist.display_name}
        )
    weeks = [[None if day is None else {"day": day, "items": by_day.get(day, [])} for day in week] for week in month_weeks(jy, jm)]
    prev_year, prev_month = shift_month(jy, jm, -1)
    next_year, next_month = shift_month(jy, jm, 1)
    return {
        "title": f"{MONTHS[jm]} {jy}",
        "weeks": weeks,
        "weekdays": WEEKDAY_NAMES,
        "prev": {"year": prev_year, "month": prev_month},
        "next": {"year": next_year, "month": next_month},
    }


def _booking_row(booking, zone_name, now):
    date_label, clock = _when(booking.starts_at, zone_name)
    notice = timedelta(hours=booking.therapist.min_notice_hours)
    try:
        receipt = booking.receipt
    except Receipt.DoesNotExist:
        receipt = None
    return {
        "id": booking.pk,
        "name": _person(booking.client) if zone_name != settings.TIME_ZONE else booking.therapist.display_name,
        "client": _person(booking.client),
        "therapist": booking.therapist.display_name,
        "date": date_label,
        "time": clock,
        "status": booking.status.lower(),
        "status_label": booking.get_status_display(),
        "price": booking.price_label,
        "can_cancel": booking.status in {Booking.Status.AWAITING, Booking.Status.CONFIRMED} and booking.starts_at - now >= notice,
        "meet_url": booking.meet_url,
        "summary": booking.summary,
        "note": booking.client_note,
        "receipt": None
        if receipt is None
        else {
            "id": receipt.pk,
            "reference": receipt.reference,
            "status": receipt.status.lower(),
            "status_label": receipt.get_status_display(),
            "file": reverse("receipt_file", args=[receipt.pk]) if receipt.attachment else "",
        },
    }


@_client_required
@require_http_methods(["GET", "POST"])
def client_sessions_api(request):
    if request.method == "POST":
        booking = get_object_or_404(Booking, pk=_body(request).get("booking"), client=request.user)
        try:
            cancel_booking(booking)
        except CancelError as exc:
            return _fail(str(exc))
        return _ok(message="جلسه لغو شد.")
    bookings = list(Booking.objects.filter(client=request.user).select_related("therapist").order_by("-starts_at")[:40])
    now = timezone.now()
    return _ok(
        calendar=_client_calendar(request.user, request.GET.get("year"), request.GET.get("month")),
        bookings=[_booking_row(item, settings.TIME_ZONE, now) for item in bookings],
    )


@_client_required
@require_http_methods(["GET", "POST"])
def client_home_api(request):
    if request.method == "POST":
        form = MoodForm(_body(request))
        if not form.is_valid():
            return _fail("حال امروز ذخیره نشد. یک حال و یک کلمه لازم است.")
        record_mood(request.user, form.cleaned_data["emoji"], form.cleaned_data["word"])
        return _ok(message="حال امروز ثبت شد.")
    today = timezone.localdate()
    ensure_daily_card(request.user, today)
    mood = MoodLog.objects.filter(client=request.user, logged_on=today).first()
    tasks = Task.objects.filter(client=request.user, due_on=today).order_by("id")
    return _ok(
        moods=[{"emoji": emoji, "label": label} for emoji, label in MOODS],
        mood=None if mood is None else {"emoji": mood.emoji, "word": mood.word},
        tasks=[
            {
                "id": item.pk,
                "title": item.title,
                "body": item.body,
                "reward": item.reward,
                "kind": item.get_kind_display(),
                "done": item.completed_at is not None,
                "status": "completed" if item.completed_at else "pending",
                "status_label": "انجام‌شده" if item.completed_at else "باز",
            }
            for item in tasks
        ],
    )


@_client_required
@require_http_methods(["GET", "POST"])
def client_account_api(request):
    profile, _created = ClientProfile.objects.get_or_create(user=request.user)
    if request.method == "GET":
        return _ok(first_name=request.user.first_name, email=request.user.email, telegram=profile.telegram_username)
    data = _body(request)
    first_name = (data.get("first_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    if not first_name:
        return _fail("نام لازم است.")
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

    try:
        validate_email(email)
    except ValidationError:
        return _fail("یک ایمیل معتبر وارد کنید.")
    if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
        return _fail("این ایمیل قبلاً ثبت شده است.")
    form = TelegramForm(data)
    if not form.is_valid():
        return _form_fail(form)
    request.user.first_name = first_name
    request.user.email = email
    request.user.save(update_fields=["first_name", "email"])
    profile.telegram_username = form.cleaned_data["telegram_username"]
    profile.save(update_fields=["telegram_username"])
    return _ok(message="پروفایل ذخیره شد.", first_name=first_name, email=email, telegram=profile.telegram_username)


@_client_required
@require_GET
def client_payments_api(request):
    receipts = Receipt.objects.filter(booking__client=request.user).select_related("booking").order_by("-created_at")
    return _ok(
        receipts=[
            {
                "id": item.pk,
                "amount": item.amount_label,
                "reference": item.reference,
                "status": item.status.lower(),
                "status_label": item.get_status_display(),
                "booking_status": item.booking.status.lower(),
                "booking_label": item.booking.get_status_display(),
                "file": reverse("receipt_file", args=[item.pk]) if item.attachment else "",
            }
            for item in receipts
        ]
    )


@_client_required
@require_GET
def client_notifications_api(request):
    ensure_daily_card(request.user)
    notes = list(request.user.notifications.all()[:30])
    _mark_read(request.user)
    return _ok(notes=[_note(item) for item in notes])


@_client_required
@require_POST
def client_task_done_api(request, task_id):
    task = get_object_or_404(Task, pk=task_id, client=request.user)
    if task.completed_at is None:
        task.completed_at = timezone.now()
        task.save(update_fields=["completed_at"])
        if task.therapist_id:
            notify(task.therapist.user, "کار انجام شد", task.title, link=f"{reverse('therapist_tasks')}#task-{task.pk}", event_key=f"task-{task.pk}")
    return _ok(message=task.reward or "انجام شد.")


@_therapist_required
@require_GET
def therapist_home_api(request):
    profile = request.therapist_profile
    zone = ZoneInfo(profile.timezone)
    now_local = timezone.localtime(timezone.now(), zone)
    start = datetime.combine(now_local.date(), time.min, tzinfo=zone)
    sessions = list(profile.bookings.filter(starts_at__gte=start, starts_at__lt=start + timedelta(days=1)).select_related("client").order_by("starts_at"))
    records = {
        item.link.client_id: item
        for item in ClientRecord.objects.filter(link__therapist=profile, link__client_id__in=[item.client_id for item in sessions]).select_related("link")
    }
    tasks = profile.assigned_tasks.filter(due_on=now_local.date()).select_related("client")
    return _ok(
        sessions=[
            {
                "id": item.pk,
                "client": _person(item.client),
                "time": _when(item.starts_at, profile.timezone)[1],
                "status": item.status.lower(),
                "status_label": item.get_status_display(),
                "prep": (records.get(item.client_id).pre_session_summary if records.get(item.client_id) else ""),
            }
            for item in sessions
        ],
        tasks=[
            {
                "id": item.pk,
                "title": item.title,
                "client": _person(item.client),
                "kind": item.get_kind_display(),
                "status": "completed" if item.completed_at else "pending",
                "status_label": "انجام‌شده" if item.completed_at else "باز",
            }
            for item in tasks
        ],
    )


@_therapist_required
@require_GET
def therapist_notifications_api(request):
    notes = list(request.user.notifications.all()[:30])
    _mark_read(request.user)
    return _ok(notes=[_note(item) for item in notes])


@_therapist_required
@require_GET
def therapist_students_api(request):
    links = request.therapist_profile.students.select_related("client").order_by("client__first_name", "client__username")
    return _ok(students=[{"id": item.client_id, "name": _person(item.client)} for item in links])


@_therapist_required
@require_http_methods(["GET", "POST"])
def therapist_add_student_api(request):
    if request.method == "GET":
        return _ok()
    form = AddStudentForm(request.therapist_profile, _body(request))
    if not form.is_valid():
        return _form_fail(form)
    with transaction.atomic():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["first_name"],
        )
        ClientProfile.objects.create(user=user)
        ensure_link(request.therapist_profile, user)
    return _ok(next=reverse("therapist_crm", args=[user.pk]), message="مراجع به فهرست شما اضافه شد.")


@_therapist_required
@require_GET
def therapist_caseload_api(request):
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
    recent = MoodLog.objects.filter(client_id__in=client_ids, logged_on__gte=week)
    summary = {}
    logged_ids = set()
    for log in recent:
        summary[log.emoji] = summary.get(log.emoji, 0) + 1
        logged_ids.add(log.client_id)
    quiet = [link for link in links if link.client_id not in logged_ids]
    if selected is not None:
        quiet = [link for link in quiet if link.client_id == selected.client_id]
    logs = MoodLog.objects.filter(client_id__in=client_ids).select_related("client").order_by("-logged_on")[:40]
    return _ok(
        students=[{"id": item.client_id, "name": _person(item.client)} for item in links],
        selected=None if selected is None else {"id": selected.client_id, "name": _person(selected.client)},
        summary=[{"emoji": emoji, "label": label, "count": summary.get(emoji, 0)} for emoji, label in MOODS],
        logs=[{"id": item.pk, "client": _person(item.client), "emoji": item.emoji, "word": item.word, "when": format_jalali(item.logged_on)} for item in logs],
        quiet=[{"id": item.client_id, "name": _person(item.client)} for item in quiet],
    )


@_therapist_required
@require_http_methods(["GET", "POST"])
def therapist_crm_api(request, user_id):
    profile = request.therapist_profile
    link = get_object_or_404(profile.students.select_related("client"), client_id=user_id)
    record, _created = ClientRecord.objects.get_or_create(link=link)
    if request.method == "POST":
        form = RecordForm(_body(request), instance=record)
        if not form.is_valid():
            return _form_fail(form)
        form.save()
        return _ok(message="پرونده ذخیره شد.")
    sessions = profile.bookings.filter(client_id=user_id).order_by("-starts_at")[:12]
    moods = MoodLog.objects.filter(client_id=user_id).order_by("-logged_on")[:14]
    return _ok(
        client={"id": link.client_id, "name": _person(link.client)},
        record={"notes": record.notes, "mind_map": record.mind_map, "reports": record.reports, "pre_session_summary": record.pre_session_summary},
        sessions=[
            {
                "id": item.pk,
                "date": _when(item.starts_at, profile.timezone)[0],
                "time": _when(item.starts_at, profile.timezone)[1],
                "status": item.status.lower(),
                "status_label": item.get_status_display(),
            }
            for item in sessions
        ],
        moods=[{"emoji": item.emoji, "word": item.word, "when": format_jalali(item.logged_on)} for item in moods],
    )


@_therapist_required
@require_http_methods(["GET", "POST"])
def therapist_tasks_api(request):
    profile = request.therapist_profile
    if request.method == "POST":
        form = TaskForm(profile, _body(request))
        if not form.is_valid():
            return _form_fail(form)
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
        return _ok(message="کار برای مراجع ثبت شد.")
    links = profile.students.select_related("client")
    assigned = profile.assigned_tasks.select_related("client").order_by("-due_on", "-id")[:40]
    return _ok(
        clients=[{"id": item.client_id, "name": _person(item.client)} for item in links],
        tasks=[
            {
                "id": item.pk,
                "title": item.title,
                "body": item.body,
                "reward": item.reward,
                "client": _person(item.client),
                "kind": item.get_kind_display(),
                "due": format_jalali(item.due_on),
                "done": item.completed_at is not None,
                "status": "completed" if item.completed_at else "pending",
                "status_label": "انجام‌شده" if item.completed_at else "باز",
            }
            for item in assigned
        ],
    )


def _receipt_row(item):
    return {
        "id": item.pk,
        "reference": item.reference,
        "amount": item.amount_label,
        "client": _person(item.booking.client),
        "status": item.status.lower(),
        "status_label": item.get_status_display(),
    }


@_therapist_required
@require_GET
def therapist_income_api(request):
    groups = income_groups(request.therapist_profile)
    return _ok(
        totals=groups["totals"],
        received=[_receipt_row(item) for item in groups["received"]],
        pending=[_receipt_row(item) for item in groups["pending"]],
        refunded=[_receipt_row(item) for item in groups["refunded"]],
    )


@_therapist_required
@require_http_methods(["GET", "POST"])
def therapist_profile_api(request):
    profile = request.therapist_profile
    if request.method == "GET":
        return _ok(
            profile={
                "display_name": profile.display_name,
                "gender": profile.gender,
                "languages": profile.languages or [],
                "years_experience": profile.years_experience,
                "license_type": profile.license_type,
                "license_number": profile.license_number,
                "license_country": profile.license_country,
                "phone": profile.phone,
                "phone": profile.phone,
                "specialties": profile.specialties or [],
        "education": profile.education or [],
                "approach": profile.approach,
                "introduction": profile.introduction,
                "currency": profile.currency,
                "session_price": str(profile.session_price),
                "timezone": profile.timezone,
                "status": profile.status.lower(),
                "status_label": profile.get_status_display(),
                "rejection": profile.get_rejection_code_display() if profile.rejection_code else "",
                "photo": reverse("therapist_photo", args=[profile.slug]) if profile.photo else "",
            },
            options=_option_payload(),
        )
    was = profile.status
    form = TherapistProfileForm(request.POST, request.FILES, instance=profile)
    if not form.is_valid():
        return _form_fail(form)
    updated = form.save(commit=False)
    uploaded_license = bool(request.FILES.get("license_file"))
    if was == TherapistProfile.Status.REJECTED or (uploaded_license and was == TherapistProfile.Status.APPROVED):
        updated.status = TherapistProfile.Status.PENDING
        updated.rejection_code = ""
        updated.reviewed_at = None
        message = "ذخیره شد و درخواست دوباره در صف بررسی است."
    else:
        message = "پروفایل ذخیره شد."
    updated.save()
    return _ok(message=message)


@_therapist_required
@require_http_methods(["GET", "POST"])
def therapist_hours_api(request):
    profile = request.therapist_profile
    if request.method == "POST":
        data = _body(request)
        if data.get("save-hours"):
            replace_cells(profile, _parse_cells(data.getlist("cells")))
            return _ok(message="ساعت‌ها ذخیره شد و وقت‌های ۳۰ روز آینده دوباره ساخته شد.")
        if data.get("delete-closure"):
            profile.closures.filter(pk=data.get("delete-closure")).delete()
            from therapy.services import rebuild_slots

            rebuild_slots(profile)
            return _ok(message="استثنا حذف شد.")
        form = ClosureForm(data)
        if not form.is_valid():
            return _form_fail(form)
        add_closure(profile, form.cleaned_data["day"], form.cleaned_data["start_time"])
        return _ok(message="استثنا ثبت شد.")
    closures = []
    for item in profile.closures.all():
        label = format_jalali(item.date)
        label += "، همهٔ روز" if item.start is None else f"، ساعت {item.start.strftime('%H:%M')}"
        closures.append({"id": item.pk, "label": label})
    from therapy.calendar import grid_starts

    return _ok(
        status=profile.status,
        open_count=profile.slots.filter(status=Slot.Status.OPEN, starts_at__gte=timezone.now()).count(),
        day_names=[DAY_LABELS[day] for day in DISPLAY_DAYS],
        rows=_hour_grid(profile),
        closures=closures,
        times=[item.strftime("%H:%M") for item in grid_starts()],
    )


@_therapist_required
@require_http_methods(["GET", "POST"])
def therapist_sessions_api(request):
    profile = request.therapist_profile
    if request.method == "POST":
        data = _body(request)
        booking = get_object_or_404(Booking, pk=data.get("booking"), therapist=profile)
        action = data.get("action")
        if action == "accept" and hasattr(booking, "receipt"):
            if not accept_receipt(booking.receipt):
                return _fail("این رسید دیگر قابل تأیید نیست.")
            return _ok(message="رسید تأیید شد.")
        if action == "reject" and hasattr(booking, "receipt"):
            if not reject_receipt(booking.receipt):
                return _fail("این رسید دیگر قابل رد نیست.")
            return _ok(message="رسید رد شد و وقت آزاد شد.")
        if action == "cancel":
            try:
                cancel_booking(booking, enforce_notice=False)
            except CancelError as exc:
                return _fail(str(exc))
            return _ok(message="جلسه لغو شد.")
        if action == "complete":
            try:
                complete_booking(booking)
            except CancelError as exc:
                return _fail(str(exc))
            return _ok(message="جلسه انجام‌شده شد.")
        if action == "update":
            form = SessionUpdateForm(data)
            if not form.is_valid():
                return _fail("پیوند جلسه معتبر نیست.")
            booking.meet_url = form.cleaned_data["meet_url"]
            booking.summary = form.cleaned_data["summary"]
            booking.save(update_fields=["meet_url", "summary"])
            return _ok(message="جلسه به‌روز شد.")
        return _fail("این کار شناخته نشد.")
    bookings = list(profile.bookings.select_related("client", "receipt").order_by("starts_at"))
    now = timezone.now()
    rows = []
    for booking in bookings:
        row = _booking_row(booking, profile.timezone, now)
        row["name"] = _person(booking.client)
        row["upcoming"] = booking.starts_at >= now
        rows.append(row)
    return _ok(upcoming=[item for item in rows if item["upcoming"]], earlier=list(reversed([item for item in rows if not item["upcoming"]])))

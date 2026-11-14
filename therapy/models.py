from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .choices import (
    APPROACHES,
    EDUCATION,
    CURRENCIES,
    DEFAULT_GAP_MINUTES,
    DEFAULT_HORIZON_DAYS,
    DEFAULT_NOTICE_HOURS,
    GENDERS,
    LICENSE_TYPES,
    REJECTION_CODES,
    TIMEZONES,
    format_money,
)


class TherapistProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "در انتظار بررسی"
        APPROVED = "APPROVED", "تأییدشده"
        REJECTED = "REJECTED", "ردشده"
        SUSPENDED = "SUSPENDED", "تعلیق‌شده"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="therapist_profile",
        verbose_name="کاربر",
    )
    display_name = models.CharField("نام نمایشی", max_length=150)
    slug = models.SlugField("نشانی", max_length=160, unique=True, allow_unicode=True)
    photo = models.FileField("عکس", upload_to="therapists/photos/", blank=True)
    gender = models.CharField("جنسیت", max_length=20, choices=GENDERS)
    languages = models.JSONField("زبان‌ها", default=list)
    years_experience = models.PositiveSmallIntegerField(
        "سال تجربه",
        validators=[MaxValueValidator(60)],
    )
    license_type = models.CharField("نوع مجوز", max_length=32, choices=LICENSE_TYPES)
    license_number = models.CharField("شماره مجوز", max_length=80)
    license_country = models.CharField("کشور صدور", max_length=80)
    phone = models.CharField("شماره تماس", max_length=20, blank=True)
    license_file = models.FileField("فایل مجوز", upload_to="therapists/licenses/")
    specialties = models.JSONField("تخصص‌ها", default=list)
    education = models.JSONField("تحصیلات", default=list)
    approach = models.CharField("رویکرد", max_length=32, choices=APPROACHES)
    introduction = models.TextField("معرفی", validators=[MaxLengthValidator(4000)])
    currency = models.CharField("ارز", max_length=8, choices=CURRENCIES, default="IRR")
    session_price = models.DecimalField(
        "قیمت جلسه",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(1)],
    )
    timezone = models.CharField("منطقه زمانی", max_length=64, choices=TIMEZONES, default="Asia/Tehran")
    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_code = models.CharField("علت رد", max_length=32, blank=True, choices=REJECTION_CODES)
    reviewed_at = models.DateTimeField("زمان بررسی", null=True, blank=True)
    min_notice_hours = models.PositiveSmallIntegerField("حداقل اطلاع قبلی (ساعت)", default=DEFAULT_NOTICE_HOURS)
    horizon_days = models.PositiveSmallIntegerField("افق باز (روز)", default=DEFAULT_HORIZON_DAYS)
    gap_minutes = models.PositiveSmallIntegerField("فاصله بین جلسات (دقیقه)", default=DEFAULT_GAP_MINUTES)
    created_at = models.DateTimeField("ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "درمانگر"
        verbose_name_plural = "لیست درمانگرها"
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == self.Status.REJECTED and self.rejection_code not in dict(REJECTION_CODES):
            raise ValidationError({"rejection_code": "برای رد، یکی از کدهای ثابت را انتخاب کنید."})
        if len(self.specialties or []) > 5:
            raise ValidationError({"specialties": "حداکثر ۵ تخصص مجاز است."})
        if len(self.education or []) > 5:
            raise ValidationError({"education": "حداکثر ۵ مورد تحصیلی مجاز است."})
        if any(item not in EDUCATION for item in (self.education or [])):
            raise ValidationError({"education": "تحصیلات را از فهرست انتخاب کنید."})

    @property
    def price_label(self):
        return format_money(self.session_price, self.currency)

    def save(self, *args, **kwargs):
        previous = None
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
        extra = set()
        if self.status != self.Status.REJECTED and self.rejection_code:
            self.rejection_code = ""
            extra.add("rejection_code")
        if previous != self.status and self.status in {
            self.Status.APPROVED,
            self.Status.REJECTED,
            self.Status.SUSPENDED,
        }:
            self.reviewed_at = timezone.now()
            extra.add("reviewed_at")
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and extra:
            kwargs["update_fields"] = set(update_fields) | extra
        super().save(*args, **kwargs)
        if previous != self.status:
            from therapy.services import handle_status_change

            handle_status_change(self, previous)



class TherapistReviewQueue(TherapistProfile):
    class Meta:
        proxy = True
        verbose_name = "صف تأیید"
        verbose_name_plural = "صف تأیید"


class AvailabilityCell(models.Model):
    profile = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name="cells")
    weekday = models.PositiveSmallIntegerField()
    start = models.TimeField()

    class Meta:
        verbose_name = "خانهٔ ساعت هفتگی"
        verbose_name_plural = "ساعت‌های هفتگی"
        constraints = [
            models.UniqueConstraint(fields=["profile", "weekday", "start"], name="unique_week_cell"),
        ]

    def __str__(self):
        return f"{self.profile_id} {self.weekday} {self.start}"


class AvailabilityClosure(models.Model):
    profile = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name="closures")
    date = models.DateField("تاریخ")
    start = models.TimeField("ساعت", null=True, blank=True)

    class Meta:
        verbose_name = "بستن وقت"
        verbose_name_plural = "استثناهای ساعت"
        ordering = ["date", "start"]

    def __str__(self):
        return f"{self.date} {self.start or 'all-day'}"


class Slot(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "آزاد"
        HELD = "HELD", "در انتظار رسید"
        BOOKED = "BOOKED", "رزروشده"

    profile = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name="slots")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)

    class Meta:
        verbose_name = "وقت"
        verbose_name_plural = "وقت‌ها"
        constraints = [
            models.UniqueConstraint(fields=["profile", "starts_at"], name="unique_slot_start"),
        ]
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.profile_id} {self.starts_at}"


class Booking(models.Model):
    class Status(models.TextChoices):
        AWAITING = "AWAITING", "در انتظار بررسی رسید"
        CONFIRMED = "CONFIRMED", "تأییدشده"
        COMPLETED = "COMPLETED", "انجام‌شده"
        CANCELLED = "CANCELLED", "لغوشده"
        REFUNDED = "REFUNDED", "بازپرداخت‌شده"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_bookings",
        verbose_name="مراجع",
    )
    therapist = models.ForeignKey(
        TherapistProfile,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="درمانگر",
    )
    slot = models.OneToOneField(Slot, null=True, blank=True, on_delete=models.SET_NULL, related_name="booking")
    starts_at = models.DateTimeField("شروع")
    ends_at = models.DateTimeField("پایان")
    status = models.CharField("وضعیت", max_length=16, choices=Status.choices, default=Status.AWAITING)
    price = models.DecimalField("مبلغ", max_digits=12, decimal_places=2)
    currency = models.CharField("ارز", max_length=8, choices=CURRENCIES)
    meet_url = models.URLField("پیوند جلسه", blank=True)
    summary = models.TextField("خلاصهٔ جلسه", blank=True, validators=[MaxLengthValidator(4000)])
    client_note = models.TextField("توضیح مراجع", blank=True, validators=[MaxLengthValidator(1000)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "رزرو"
        verbose_name_plural = "رزروها"
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["client", "starts_at"]),
            models.Index(fields=["therapist", "starts_at"]),
        ]

    def __str__(self):
        return f"{self.client_id} {self.starts_at}"

    @property
    def price_label(self):
        return format_money(self.price, self.currency)


class Receipt(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "ارسال‌شده"
        ACCEPTED = "ACCEPTED", "دریافت‌شده"
        REJECTED = "REJECTED", "ردشده"
        REFUNDED = "REFUNDED", "بازپرداخت‌شده"

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="receipt", verbose_name="رزرو")
    amount = models.DecimalField("مبلغ", max_digits=12, decimal_places=2)
    reference = models.CharField("شماره پیگیری", max_length=120)
    attachment = models.FileField("فایل رسید", upload_to="receipts/", blank=True)
    status = models.CharField("وضعیت", max_length=16, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "رسید"
        verbose_name_plural = "رسیدها"
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference

    @property
    def amount_label(self):
        return format_money(self.amount, self.booking.currency)


class ClientLink(models.Model):
    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name="students")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مراجع درمانگر"
        verbose_name_plural = "مراجعان درمانگرها"
        constraints = [
            models.UniqueConstraint(fields=["therapist", "client"], name="unique_therapist_client"),
        ]

    def __str__(self):
        return f"{self.therapist_id}:{self.client_id}"


class ClientRecord(models.Model):
    link = models.OneToOneField(ClientLink, on_delete=models.CASCADE, related_name="record")
    notes = models.TextField("یادداشت", blank=True, validators=[MaxLengthValidator(8000)])
    mind_map = models.TextField("نقشهٔ ذهن", blank=True, validators=[MaxLengthValidator(8000)])
    reports = models.TextField("گزارش‌ها", blank=True, validators=[MaxLengthValidator(8000)])
    pre_session_summary = models.TextField(
        "خلاصهٔ پیش از جلسه",
        blank=True,
        validators=[MaxLengthValidator(8000)],
    )

    class Meta:
        verbose_name = "پرونده"
        verbose_name_plural = "پرونده‌ها"

    def __str__(self):
        return f"record {self.link_id}"


class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile",
    )
    telegram_username = models.CharField("نام کاربری تلگرام", max_length=32, blank=True)
    phone = models.CharField("شماره تماس", max_length=20, blank=True)

    class Meta:
        verbose_name = "پروفایل مراجع"
        verbose_name_plural = "پروفایل مراجعان"

    def __str__(self):
        return self.user.get_username()


class MoodLog(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="moods")
    emoji = models.CharField(max_length=8)
    word = models.CharField(max_length=40)
    logged_on = models.DateField()

    class Meta:
        verbose_name = "حال روز"
        verbose_name_plural = "حال روزها"
        constraints = [
            models.UniqueConstraint(fields=["client", "logged_on"], name="one_mood_per_day"),
        ]
        ordering = ["-logged_on"]

    def __str__(self):
        return f"{self.client_id} {self.logged_on}"


class Task(models.Model):
    class Kind(models.TextChoices):
        PRACTICE = "practice", "تمرین"
        REMINDER = "reminder", "یادآور"
        DAILY = "daily", "کارت روزانه"
        CHALLENGE = "challenge", "چالش روزانه"

    therapist = models.ForeignKey(
        TherapistProfile,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assigned_tasks",
    )
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    title = models.CharField(max_length=120)
    body = models.TextField(validators=[MaxLengthValidator(2000)])
    reward = models.CharField(max_length=200, blank=True)
    due_on = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "کار"
        verbose_name_plural = "کارها"
        ordering = ["due_on", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "due_on"],
                condition=models.Q(therapist__isnull=True),
                name="one_system_task_per_day",
            ),
        ]

    def __str__(self):
        return self.title


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=140)
    body = models.TextField(validators=[MaxLengthValidator(1000)])
    link = models.CharField(max_length=240, blank=True)
    event_key = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class StoredFile(models.Model):
    name = models.CharField(max_length=255, unique=True)
    content = models.BinaryField()

    class Meta:
        verbose_name = "فایل ذخیره‌شده"
        verbose_name_plural = "فایل‌های ذخیره‌شده"

    def __str__(self):
        return self.name

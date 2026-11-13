from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from therapy.models import (
    AvailabilityCell,
    AvailabilityClosure,
    Booking,
    ClientLink,
    ClientProfile,
    ClientRecord,
    MoodLog,
    Notification,
    Receipt,
    Slot,
    Task,
    TherapistProfile,
    TherapistReviewQueue,
)
from therapy.services import review_deadline, review_is_late

# Waiting is amber, active is green, booked is blue, finished is gray, and blocked is red.
STATUS_CHIPS = {
    "PENDING": "warning",
    "APPROVED": "success",
    "REJECTED": "danger",
    "SUSPENDED": "danger",
    "OPEN": "success",
    "HELD": "warning",
    "BOOKED": "info",
    "AWAITING": "warning",
    "CONFIRMED": "success",
    "COMPLETED": "muted",
    "CANCELLED": "danger",
    "SUBMITTED": "warning",
    "ACCEPTED": "success",
    "REFUNDED": "danger",
    "UNREAD": "warning",
    "READ": "muted",
    "OPEN_TASK": "warning",
    "DONE": "muted",
    "LATE": "danger",
    "ON_TIME": "success",
}


def choice_chip(obj, field="status"):
    value = getattr(obj, field)
    label = dict(obj._meta.get_field(field).flatchoices).get(value, value)
    return value, label


def count_link(count, url_name, lookup, value):
    url = f"{reverse(url_name)}?{lookup}={value}"
    return format_html('<a href="{}">{}</a>', url, count)


@admin.register(TherapistProfile)
class TherapistProfileAdmin(ModelAdmin):
    list_display = (
        "display_name",
        "status_badge",
        "cell_count",
        "closure_count",
        "slot_count",
        "booking_count",
        "receipt_count",
        "student_count",
        "record_count",
        "task_count",
        "notification_count",
        "rejection_code",
        "review_state",
        "session_price",
        "currency",
    )
    list_filter = ("status",)
    search_fields = ("display_name", "license_number", "user__username", "user__email")
    readonly_fields = ("reviewed_at", "created_at", "review_state", "license_link")
    actions = ("approve_selected", "suspend_selected")
    fieldsets = (
        ("بررسی", {"fields": ("user", "display_name", "slug", "status", "rejection_code", "review_state", "reviewed_at", "created_at")}),
        ("پروفایل", {"fields": ("photo", "gender", "languages", "years_experience", "phone", "approach", "specialties", "education", "introduction")}),
        ("مجوز", {"fields": ("license_type", "license_number", "license_country", "license_file", "license_link")}),
        ("جلسه", {"fields": ("currency", "session_price", "timezone", "min_notice_hours", "horizon_days", "gap_minutes")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            cell_count=Count("cells", distinct=True),
            closure_count=Count("closures", distinct=True),
            slot_count=Count("slots", distinct=True),
            booking_count=Count("bookings", distinct=True),
            receipt_count=Count("bookings__receipt", distinct=True),
            student_count=Count("students", distinct=True),
            record_count=Count("students__record", distinct=True),
            task_count=Count("assigned_tasks", distinct=True),
            notification_count=Count("user__notifications", distinct=True),
        )

    @display(description="وضعیت", ordering="status", label=STATUS_CHIPS)
    def status_badge(self, obj):
        return choice_chip(obj)

    @admin.display(description="ساعت‌های هفتگی", ordering="cell_count")
    def cell_count(self, obj):
        return count_link(obj.cell_count, "admin:therapy_availabilitycell_changelist", "profile__id__exact", obj.pk)

    @admin.display(description="استثناهای ساعت", ordering="closure_count")
    def closure_count(self, obj):
        return count_link(obj.closure_count, "admin:therapy_availabilityclosure_changelist", "profile__id__exact", obj.pk)

    @admin.display(description="وقت‌ها", ordering="slot_count")
    def slot_count(self, obj):
        return count_link(obj.slot_count, "admin:therapy_slot_changelist", "profile__id__exact", obj.pk)

    @admin.display(description="رزروها", ordering="booking_count")
    def booking_count(self, obj):
        return count_link(obj.booking_count, "admin:therapy_booking_changelist", "therapist__id__exact", obj.pk)

    @admin.display(description="رسیدها", ordering="receipt_count")
    def receipt_count(self, obj):
        return count_link(obj.receipt_count, "admin:therapy_receipt_changelist", "booking__therapist__id__exact", obj.pk)

    @admin.display(description="مراجعان", ordering="student_count")
    def student_count(self, obj):
        return count_link(obj.student_count, "admin:therapy_clientlink_changelist", "therapist__id__exact", obj.pk)

    @admin.display(description="پرونده‌ها", ordering="record_count")
    def record_count(self, obj):
        return count_link(obj.record_count, "admin:therapy_clientrecord_changelist", "link__therapist__id__exact", obj.pk)

    @admin.display(description="کارها", ordering="task_count")
    def task_count(self, obj):
        return count_link(obj.task_count, "admin:therapy_task_changelist", "therapist__id__exact", obj.pk)

    @admin.display(description="اعلان‌ها", ordering="notification_count")
    def notification_count(self, obj):
        return count_link(obj.notification_count, "admin:therapy_notification_changelist", "user__id__exact", obj.user_id)

    @display(description="مهلت بررسی", label=STATUS_CHIPS)
    def review_state(self, obj):
        if not getattr(obj, "pk", None) or obj.status != TherapistProfile.Status.PENDING:
            return ""
        deadline = review_deadline(obj)
        if review_is_late(obj):
            return "LATE", f"دیرشده · {deadline.isoformat()}"
        return "ON_TIME", deadline.isoformat()

    @admin.display(description="دانلود مجوز")
    def license_link(self, obj):
        if not getattr(obj, "pk", None) or not obj.license_file:
            return "—"
        return format_html('<a href="{}">دانلود مجوز</a>', reverse("therapist_license", args=[obj.pk]))

    @admin.action(description="تأیید درمانگرهای انتخاب‌شده")
    def approve_selected(self, request, queryset):
        for profile in queryset:
            profile.status = TherapistProfile.Status.APPROVED
            profile.save()
        self.message_user(request, "درمانگرهای انتخاب‌شده تأیید شدند.")

    @admin.action(description="تعلیق، لغو رزروهای آینده و بازپرداخت")
    def suspend_selected(self, request, queryset):
        for profile in queryset:
            profile.status = TherapistProfile.Status.SUSPENDED
            profile.save()
        self.message_user(request, "تعلیق انجام شد. رزروهای آینده لغو و بازپرداخت شد.")


@admin.register(TherapistReviewQueue)
class TherapistReviewQueueAdmin(TherapistProfileAdmin):
    list_filter = ()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(status=TherapistProfile.Status.PENDING)


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ("id", "client", "therapist", "starts_at", "status_badge", "price", "currency")
    list_filter = ("status", "therapist", "client")
    search_fields = ("client__username", "therapist__display_name")
    raw_id_fields = ("client", "therapist", "slot")

    @display(description="وضعیت", ordering="status", label=STATUS_CHIPS)
    def status_badge(self, obj):
        return choice_chip(obj)

    def has_add_permission(self, request):
        return False


@admin.register(Receipt)
class ReceiptAdmin(ModelAdmin):
    list_display = ("reference", "booking", "amount", "status_badge", "created_at")
    list_filter = ("status", "booking__therapist", "booking__client")
    search_fields = ("reference", "booking__client__username")
    raw_id_fields = ("booking",)

    @display(description="وضعیت", ordering="status", label=STATUS_CHIPS)
    def status_badge(self, obj):
        return choice_chip(obj)

    def has_add_permission(self, request):
        return False


@admin.register(ClientLink)
class ClientLinkAdmin(ModelAdmin):
    list_display = ("therapist", "client", "created_at")
    list_filter = ("therapist", "client")
    search_fields = ("therapist__display_name", "client__username")
    raw_id_fields = ("therapist", "client")


@admin.register(AvailabilityCell)
class AvailabilityCellAdmin(ModelAdmin):
    list_display = ("profile", "weekday", "start")
    list_filter = ("profile", "weekday")
    search_fields = ("profile__display_name",)
    raw_id_fields = ("profile",)


@admin.register(AvailabilityClosure)
class AvailabilityClosureAdmin(ModelAdmin):
    list_display = ("profile", "date", "start")
    list_filter = ("profile",)
    search_fields = ("profile__display_name",)
    raw_id_fields = ("profile",)


@admin.register(Slot)
class SlotAdmin(ModelAdmin):
    list_display = ("profile", "starts_at", "ends_at", "status_badge")
    list_filter = ("status", "profile")
    search_fields = ("profile__display_name",)
    raw_id_fields = ("profile",)

    @display(description="وضعیت", ordering="status", label=STATUS_CHIPS)
    def status_badge(self, obj):
        return choice_chip(obj)


@admin.register(ClientRecord)
class ClientRecordAdmin(ModelAdmin):
    list_display = ("link",)
    list_filter = ("link__therapist", "link__client")
    search_fields = ("link__client__username", "link__therapist__display_name")
    raw_id_fields = ("link",)


@admin.register(ClientProfile)
class ClientProfileAdmin(ModelAdmin):
    list_display = (
        "user",
        "telegram_username",
        "booking_count",
        "receipt_count",
        "notification_count",
        "therapist_count",
        "record_count",
        "mood_count",
        "task_count",
    )
    search_fields = ("user__username", "telegram_username")
    raw_id_fields = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            booking_count=Count("user__client_bookings", distinct=True),
            receipt_count=Count("user__client_bookings__receipt", distinct=True),
            notification_count=Count("user__notifications", distinct=True),
            therapist_count=Count("user__care_links", distinct=True),
            record_count=Count("user__care_links__record", distinct=True),
            mood_count=Count("user__moods", distinct=True),
            task_count=Count("user__tasks", distinct=True),
        )

    @admin.display(description="رزروها", ordering="booking_count")
    def booking_count(self, obj):
        return count_link(obj.booking_count, "admin:therapy_booking_changelist", "client__id__exact", obj.user_id)

    @admin.display(description="رسیدها", ordering="receipt_count")
    def receipt_count(self, obj):
        return count_link(obj.receipt_count, "admin:therapy_receipt_changelist", "booking__client__id__exact", obj.user_id)

    @admin.display(description="اعلان‌ها", ordering="notification_count")
    def notification_count(self, obj):
        return count_link(obj.notification_count, "admin:therapy_notification_changelist", "user__id__exact", obj.user_id)

    @admin.display(description="درمانگرها", ordering="therapist_count")
    def therapist_count(self, obj):
        return count_link(obj.therapist_count, "admin:therapy_clientlink_changelist", "client__id__exact", obj.user_id)

    @admin.display(description="پرونده‌ها", ordering="record_count")
    def record_count(self, obj):
        return count_link(obj.record_count, "admin:therapy_clientrecord_changelist", "link__client__id__exact", obj.user_id)

    @admin.display(description="حال روزها", ordering="mood_count")
    def mood_count(self, obj):
        return count_link(obj.mood_count, "admin:therapy_moodlog_changelist", "client__id__exact", obj.user_id)

    @admin.display(description="کارها", ordering="task_count")
    def task_count(self, obj):
        return count_link(obj.task_count, "admin:therapy_task_changelist", "client__id__exact", obj.user_id)


@admin.register(MoodLog)
class MoodLogAdmin(ModelAdmin):
    list_display = ("client", "emoji", "word", "logged_on")
    list_filter = ("client",)
    search_fields = ("client__username", "word")
    raw_id_fields = ("client",)


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ("title", "client", "therapist", "kind", "due_on", "status_badge")
    list_filter = ("kind", "therapist", "client")
    search_fields = ("title", "client__username")
    raw_id_fields = ("client", "therapist")

    @display(description="وضعیت", ordering="completed_at", label=STATUS_CHIPS)
    def status_badge(self, obj):
        if obj.completed_at:
            return "DONE", "انجام‌شده"
        return "OPEN_TASK", "باز"


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "user", "event_key", "status_badge", "created_at")
    list_filter = ("user",)
    search_fields = ("title", "user__username", "event_key")
    raw_id_fields = ("user",)

    @display(description="وضعیت", ordering="read_at", label=STATUS_CHIPS)
    def status_badge(self, obj):
        if obj.read_at:
            return "READ", "خوانده‌شده"
        return "UNREAD", "خوانده‌نشده"

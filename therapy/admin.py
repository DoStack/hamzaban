from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from therapy.models import Booking, ClientLink, Receipt, TherapistProfile
from therapy.services import review_deadline, review_is_late


@admin.register(TherapistProfile)
class TherapistProfileAdmin(ModelAdmin):
    list_display = ("display_name", "status", "rejection_code", "review_state", "session_price", "currency")
    list_filter = ("status",)
    search_fields = ("display_name", "license_number", "user__username", "user__email")
    readonly_fields = ("reviewed_at", "created_at", "review_state", "license_link")
    actions = ("approve_selected", "suspend_selected")
    fieldsets = (
        ("بررسی", {"fields": ("user", "display_name", "slug", "status", "rejection_code", "review_state", "reviewed_at", "created_at")}),
        ("پروفایل", {"fields": ("photo", "gender", "languages", "years_experience", "approach", "specialties", "introduction")}),
        ("مجوز", {"fields": ("license_type", "license_number", "license_country", "license_file", "license_link")}),
        ("جلسه", {"fields": ("currency", "session_price", "timezone", "min_notice_hours", "horizon_days", "gap_minutes")}),
    )

    @admin.display(description="مهلت بررسی")
    def review_state(self, obj):
        if not getattr(obj, "pk", None) or obj.status != TherapistProfile.Status.PENDING:
            return "—"
        deadline = review_deadline(obj)
        if review_is_late(obj):
            return f"دیرشده · {deadline.isoformat()}"
        return deadline.isoformat()

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


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ("id", "client", "therapist", "starts_at", "status", "price", "currency")
    list_filter = ("status",)
    search_fields = ("client__username", "therapist__display_name")
    raw_id_fields = ("client", "therapist", "slot")

    def has_add_permission(self, request):
        return False


@admin.register(Receipt)
class ReceiptAdmin(ModelAdmin):
    list_display = ("reference", "booking", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "booking__client__username")
    raw_id_fields = ("booking",)

    def has_add_permission(self, request):
        return False


@admin.register(ClientLink)
class ClientLinkAdmin(ModelAdmin):
    list_display = ("therapist", "client", "created_at")
    search_fields = ("therapist__display_name", "client__username")
    raw_id_fields = ("therapist", "client")

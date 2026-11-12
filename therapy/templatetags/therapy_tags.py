from datetime import datetime

from django import template
from django.utils import timezone

from therapy.calendar import format_jalali

register = template.Library()


@register.filter
def jalali(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        local = timezone.localtime(value)
        return f"{format_jalali(local)}، ساعت {local.strftime('%H:%M')}"
    return format_jalali(value)

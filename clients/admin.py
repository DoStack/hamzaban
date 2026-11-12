from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from unfold.admin import ModelAdmin

for model, singular, plural in (
    (User.groups.through, "کاربر و گروه", "کاربران و گروه‌ها"),
    (User.user_permissions.through, "اجازهٔ کاربر", "اجازه‌های کاربران"),
    (Group.permissions.through, "اجازهٔ گروه", "اجازه‌های گروه‌ها"),
):
    model._meta.verbose_name = singular
    model._meta.verbose_name_plural = plural

admin.site.register(
    [
        Permission,
        ContentType,
        Session,
        LogEntry,
        User.groups.through,
        User.user_permissions.through,
        Group.permissions.through,
    ],
    ModelAdmin,
)

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path, register_converter

from config.converters import UnicodeSlugConverter

from clients.views import (
    HamzabanLoginView,
    data_file,
    data_index,
    favicon,
    home,
    register,
    therapist_detail,
    therapist_landing,
    therapist_list,
    therapist_register,
)
from therapy.views import book, license_file, manifest, receipt_file, service_worker, therapist_photo

admin.site.site_header = "هم‌زبان"
admin.site.site_title = "هم‌زبان"
admin.site.index_title = "داشبورد"

_admin_urls = admin.site.get_urls


def _admin_urls_with_data():
    return [
        path("data/", admin.site.admin_view(data_index), name="data_index"),
        path("data/<str:name>", admin.site.admin_view(data_file), name="data_file"),
    ] + _admin_urls()


admin.site.get_urls = _admin_urls_with_data

register_converter(UnicodeSlugConverter, "uslug")

urlpatterns = [
    path("favicon.ico", favicon, name="favicon"),
    path("manifest.webmanifest", manifest, name="manifest"),
    path("sw.js", service_worker, name="service_worker"),
    path("", home, name="home"),
    path("therapists/", therapist_list, name="therapist_list"),
    path("therapists/<uslug:slug>/photo/", therapist_photo, name="therapist_photo"),
    path("therapists/<uslug:slug>/book/<int:slot_id>/", book, name="book_slot"),
    path("therapists/<uslug:slug>/", therapist_detail, name="therapist_detail"),
    path("receipts/<int:pk>/file/", receipt_file, name="receipt_file"),
    path("licenses/<int:pk>/", license_file, name="therapist_license"),
    path("api/", include("therapy.api_urls")),
    path("admin/", admin.site.urls),
    path("accounts/login/", HamzabanLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/register/", register, name="register"),
    path("therapist/register/", therapist_register, name="therapist_register"),
    path("therapist/", therapist_landing, name="therapist_landing"),
    path("therapist/", include("therapy.urls")),
    path("profile/", include("clients.urls")),
]

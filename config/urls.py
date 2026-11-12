from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from clients.views import home, register, therapist_detail, therapist_list

admin.site.site_header = "هم‌زبان"
admin.site.site_title = "هم‌زبان"
admin.site.index_title = "داشبورد"

urlpatterns = [
    path("", home, name="home"),
    path("therapists/", therapist_list, name="therapist_list"),
    path("therapists/<slug:slug>/", therapist_detail, name="therapist_detail"),
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("accounts/register/", register, name="register"),
    path("profile/", include("clients.urls")),
]

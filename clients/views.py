import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import login, views as auth_views
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import translation
from django.views.decorators.http import require_GET, require_http_methods

from therapy.access import client_only, is_therapist
from therapy.forms import TherapistRegistrationForm
from therapy.services import open_slots_by_day, public_profile, search_public_therapists

from .catalog import FAQS, STATS
from .forms import ClientRegistrationForm


def data_directory():
    return Path(settings.BASE_DIR) / "data"


def html_documents():
    folder = data_directory()
    if not folder.is_dir():
        return []
    return sorted(path.name for path in folder.glob("*.html") if path.is_file())


def data_file_path(name):
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    folder = data_directory().resolve()
    candidate = (folder / name).resolve()
    if candidate.parent != folder or not candidate.is_file():
        return None
    return candidate


def account_home(user):
    if is_therapist(user):
        return "therapist_home"
    return "client_profile"


@require_GET
def favicon(request):
    return redirect(static("favicon.svg"))


@require_GET
def home(request):
    return render(request, "clients/home.html", {"stats": STATS, "faqs": FAQS})


@require_GET
def therapist_list(request):
    query = request.GET.get("q", "")
    return render(
        request,
        "clients/therapist_list.html",
        {"therapists": search_public_therapists(query), "query": query.strip()},
    )


@require_GET
def therapist_detail(request, slug):
    therapist = public_profile(slug)
    if therapist is None:
        raise Http404("درمانگر پیدا نشد.")
    return render(
        request,
        "clients/therapist_detail.html",
        {"therapist": therapist, "days": open_slots_by_day(therapist)},
    )


@client_only
def client_profile(request):
    return render(request, "clients/profile.html", {"section": "overview"})


@require_GET
def therapist_landing(request):
    return render(request, "therapists/landing.html")


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect(account_home(request.user))

    with translation.override("fa"):
        form = ClientRegistrationForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            login(request, form.save())
            return redirect("client_profile")

        return render(request, "registration/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def therapist_register(request):
    if request.user.is_authenticated:
        return redirect(account_home(request.user))

    with translation.override("fa"):
        form = TherapistRegistrationForm(
            request.POST if request.method == "POST" else None,
            request.FILES if request.method == "POST" else None,
        )
        if request.method == "POST" and form.is_valid():
            login(request, form.save())
            return redirect("therapist_home")

        return render(request, "therapists/register.html", {"form": form})


@require_GET
def data_index(request):
    return render(
        request,
        "admin/data_index.html",
        {**admin.site.each_context(request), "title": "data", "files": html_documents()},
    )


@require_GET
def data_file(request, name):
    path = data_file_path(name)
    if path is None:
        raise Http404("فایل پیدا نشد.")
    content_type = "text/html; charset=utf-8" if path.suffix.lower() == ".html" else mimetypes.guess_type(path.name)[0]
    return FileResponse(path.open("rb"), content_type=content_type or "application/octet-stream")


class HamzabanLoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def get_default_redirect_url(self):
        return reverse(account_home(self.request.user))

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import translation
from django.views.decorators.http import require_GET, require_http_methods

from .catalog import FAQS, STATS, get_therapist, search_therapists
from .forms import ClientRegistrationForm


@require_GET
def home(request):
    return render(request, "clients/home.html", {"stats": STATS, "faqs": FAQS})


@require_GET
def therapist_list(request):
    query = request.GET.get("q", "")
    return render(
        request,
        "clients/therapist_list.html",
        {"therapists": search_therapists(query), "query": query.strip()},
    )


@require_GET
def therapist_detail(request, slug):
    therapist = get_therapist(slug)
    if therapist is None:
        raise Http404("درمانگر پیدا نشد.")
    return render(request, "clients/therapist_detail.html", {"therapist": therapist})


@login_required
def client_profile(request):
    return render(request, "clients/profile.html")


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("client_profile")

    with translation.override("fa"):
        form = ClientRegistrationForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            login(request, form.save())
            return redirect("client_profile")

        return render(request, "registration/register.html", {"form": form})

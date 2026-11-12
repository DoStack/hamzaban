from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import translation

from clients.forms import THERAPIST_GROUP_NAME
from therapy.models import TherapistProfile


def is_therapist(user):
    return user.is_authenticated and user.groups.filter(name=THERAPIST_GROUP_NAME).exists()


def forbid(request):
    return render(request, "forbidden.html", status=403)


def therapist_only(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        with translation.override("fa"):
            if not is_therapist(request.user):
                return redirect("client_profile")
            try:
                request.therapist_profile = request.user.therapist_profile
            except TherapistProfile.DoesNotExist:
                return render(request, "therapists/missing_profile.html")
            return view(request, *args, **kwargs)

    return wrapped


def client_only(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        with translation.override("fa"):
            if is_therapist(request.user):
                return redirect("therapist_home")
            return view(request, *args, **kwargs)

    return wrapped

from therapy.access import is_therapist


def account_role(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"is_therapist": False}
    flag = getattr(request, "_is_therapist", None)
    if flag is None:
        flag = is_therapist(user)
        request._is_therapist = flag
    return {"is_therapist": flag}

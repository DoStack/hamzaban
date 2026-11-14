import json
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone

from therapy.calendar import format_jalali

SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.email"
STATE_SALT = "google-calendar"


class GoogleCalendarError(Exception):
    pass


def configured():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def redirect_uri(request):
    return request.build_absolute_uri(reverse("therapist_google_callback"))


def authorization_url(request):
    state = signing.dumps({"uid": request.user.pk}, salt=STATE_SALT)
    query = urllib.parse.urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri(request),
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def read_state(value, user_id):
    try:
        state = signing.loads(value or "", salt=STATE_SALT, max_age=600)
    except signing.BadSignature as exc:
        raise GoogleCalendarError("این اتصال منقضی شد. دوباره تلاش کنید.") from exc
    if state.get("uid") != user_id:
        raise GoogleCalendarError("این اتصال برای حساب دیگری است.")
    return state


def connect_profile(profile, code, redirect):
    token = _post(
        "https://oauth2.googleapis.com/token",
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        },
    )
    access = token.get("access_token")
    refresh = token.get("refresh_token") or profile.google_refresh_token
    if not access or not refresh:
        raise GoogleCalendarError("گوگل اجازهٔ ماندگار نداد. دوباره اتصال را بزنید.")
    info = _get("https://www.googleapis.com/oauth2/v2/userinfo", access)
    email = (info.get("email") or "").strip().lower()
    if not email:
        raise GoogleCalendarError("گوگل ایمیل این حساب را برنگرداند.")
    _get("https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=1", access)
    profile.google_email = email
    profile.google_refresh_token = refresh
    profile.save(update_fields=["google_email", "google_refresh_token"])
    return email


def publish_booking(booking):
    """Put one confirmed session on the therapist calendar and keep its Meet link."""
    profile = booking.therapist
    if booking.google_event_id or not configured() or not profile.google_refresh_token:
        return False
    access = _access_token(profile)
    zone = ZoneInfo(profile.timezone)
    start = timezone.localtime(booking.starts_at, zone)
    end = timezone.localtime(booking.ends_at, zone)
    title, details = event_copy(booking)
    payload = {
        "summary": title,
        "description": details,
        "start": {"dateTime": start.isoformat(), "timeZone": profile.timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": profile.timezone},
        "conferenceData": {
            "createRequest": {
                "requestId": f"hamzaban-{booking.pk}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    client_email = _guest_email(booking.client.email)
    if client_email:
        payload["attendees"] = [{"email": client_email}]
    updates = "all" if client_email else "none"
    event = _json(
        "POST",
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1&sendUpdates={updates}",
        access,
        payload,
    )
    event_id = event.get("id") or ""
    if not event_id:
        raise GoogleCalendarError("گوگل رویداد را نساخت.")
    booking.google_event_id = event_id
    booking.meet_url = _meet_link(event)
    booking.save(update_fields=["google_event_id", "meet_url"])
    return True


def drop_booking_event(booking):
    """Remove the calendar event after the session is cancelled."""
    profile = booking.therapist
    if not booking.google_event_id or not configured() or not profile.google_refresh_token:
        return False
    access = _access_token(profile)
    event_id = urllib.parse.quote(booking.google_event_id, safe="")
    _json(
        "DELETE",
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}?sendUpdates=all",
        access,
        missing_ok=True,
    )
    booking.google_event_id = ""
    booking.meet_url = ""
    booking.save(update_fields=["google_event_id", "meet_url"])
    return True


def client_calendar_url(booking):
    """A Google Calendar link the client can open for this confirmed session."""
    if booking.status != "CONFIRMED" or not booking.meet_url:
        return ""
    start = booking.starts_at.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    end = booking.ends_at.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    title, details = event_copy(booking)
    query = urllib.parse.urlencode(
        {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start}/{end}",
            "details": details,
            "location": booking.meet_url,
        }
    )
    return f"https://calendar.google.com/calendar/render?{query}"


def event_copy(booking):
    """Title and description sent to Google for this session."""
    therapist_name = booking.therapist.display_name
    client_name = booking.client.get_full_name() or booking.client.get_username()
    start = timezone.localtime(booking.starts_at, ZoneInfo(booking.therapist.timezone))
    lines = [
        f"درمانگر: {therapist_name}",
        f"مراجع: {client_name}",
        f"زمان: {format_jalali(start)}، ساعت {start.strftime('%H:%M')}",
    ]
    note = (booking.client_note or "").strip()
    if note:
        lines.append(f"توضیح مراجع: {note}")
    return f"جلسهٔ {therapist_name} با {client_name}", "\n".join(lines)


def _guest_email(value):
    email = (value or "").strip().lower()
    if not email or email.endswith("@imported.hamzaban.invalid"):
        return ""
    return email


def _meet_link(event):
    link = event.get("hangoutLink") or ""
    if link:
        return link
    for entry in (event.get("conferenceData") or {}).get("entryPoints") or []:
        if entry.get("entryPointType") == "video" and entry.get("uri"):
            return entry["uri"]
    return ""


def _access_token(profile):
    token = _post(
        "https://oauth2.googleapis.com/token",
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": profile.google_refresh_token,
            "grant_type": "refresh_token",
        },
    )
    access = token.get("access_token")
    if not access:
        raise GoogleCalendarError("اتصال تقویم منقضی شد. دوباره وصل کنید.")
    return access


def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    return _read(urllib.request.Request(url, data=body))


def _get(url, access):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access}"})
    return _read(request)


def _json(method, url, access, payload=None, missing_ok=False):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
    )
    return _read(request, missing_ok=missing_ok)


def _read(request, missing_ok=False):
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        if missing_ok and exc.code in {404, 410}:
            return {}
        detail = exc.read().decode(errors="replace")
        raise GoogleCalendarError(_google_message(detail)) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GoogleCalendarError("ارتباط با گوگل برقرار نشد.") from exc


def _google_message(detail):
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return "گوگل این اتصال را نپذیرفت."
    error = payload.get("error")
    if isinstance(error, dict):
        reasons = " ".join(str(item.get("reason", "")) for item in error.get("details") or [])
        if "SERVICE_DISABLED" in reasons or "accessNotConfigured" in reasons:
            return "Google Calendar API در پروژه خاموش است."
        return "دسترسی تقویم داده نشد."
    if error in {"access_denied", "invalid_grant"}:
        return "گوگل این اتصال را نپذیرفت."
    return "گوگل این اتصال را نپذیرفت."

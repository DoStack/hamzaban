import re
from datetime import datetime, time
from html import unescape
from zoneinfo import ZoneInfo

from therapy.calendar import grid_starts, latin_digits

_TAG_MAP = {
    "اضطراب": "اضطراب",
    "استرس": "استرس شغلی",
    "مهاجرت": "مهاجرت",
    "افسردگی": "خلق",
    "وسواس": "وسواس",
    "زوجدرمانی": "رابطه",
    "روابط": "رابطه",
    "کودک": "کودک و نوجوان",
    "خانواده": "رابطه",
    "شخصیت": "خلق",
    "تروما": "تروما",
    "مسائل جنسی": "رابطه",
    "نوجوان": "کودک و نوجوان",
}
_LANGUAGES = {"فارسی", "انگلیسی", "عربی", "ترکی", "آلمانی", "فرانسوی"}


def _plain(value):
    text = re.sub(r"<[^>]+>", "", value or "")
    return unescape(text).strip()


def _key(value):
    return _plain(value).replace("\u200c", "")


def directory_slugs(html):
    found = []
    for slug in re.findall(r'href="/therapists/([^"#?]+)"', html):
        if "." in slug or slug in found:
            continue
        found.append(slug)
    return found


def parse_profile(html, slug):
    main = html[html.find("<main") : html.find("</main>")]
    name = _field(r"<h1[^>]*>(.*?)</h1>", main)
    headline = _field(r'<div class="muted">(.*?)</div>', main)
    bio = _field(r'<div class="tags"[^>]*>.*?</div>\s*<p[^>]*>(.*?)</p>', main)
    pills = [_plain(item) for item in re.findall(r'<span class="pill gray">(.*?)</span>', main)]
    rows = {_key(label): _plain(value) for label, value in re.findall(r"<th>(.*?)</th><td>(.*?)</td>", main)}
    price = _field(r"\$<!-- -->(\d+)", main) or "25"
    zone = _field(r'name="zone" value="([^"]+)"', main) or "America/Toronto"
    image = _field(r'<img class="avatar lg" src="([^"]+)"', main)
    slots = re.findall(r'name="startsAt" value="([^"]+)"', main)
    languages = [part.strip() for part in re.split(r"[،,]", rows.get("زبان", "فارسی")) if part.strip() in _LANGUAGES]
    return {
        "slug": slug,
        "display_name": name or slug,
        "headline": headline,
        "bio": bio,
        "rows": rows,
        "specialties": _specialties(pills),
        "approach": _approach(rows.get("رویکرد", ""), headline, pills),
        "languages": languages or ["فارسی"],
        "license_type": _license_type(headline, rows.get("شمارهی نظام", "")),
        "license_number": _license_number(rows.get("شمارهی نظام", "")),
        "introduction": _introduction(headline, bio, rows),
        "currency": "USD",
        "session_price": price,
        "timezone": zone if zone in {"America/Toronto", "Asia/Tehran", "UTC"} else "America/Toronto",
        "draft": "پیش نویس" in _plain(main) or "واقعی نیست" in (headline or ""),
        "test_profile": "واقعی نیست" in (headline or ""),
        "image": image,
        "cells": _cells(slots, zone),
    }


def _field(pattern, html):
    match = re.search(pattern, html, re.S)
    return _plain(match.group(1)) if match else ""


def _specialties(pills):
    chosen = []
    for pill in pills:
        mapped = _TAG_MAP.get(pill.replace("\u200c", ""))
        if mapped and mapped not in chosen:
            chosen.append(mapped)
        if len(chosen) == 5:
            break
    return chosen or ["اضطراب"]


def _approach(approach_text, headline, pills):
    text = f"{approach_text} {headline} {' '.join(pills)}"
    if "طرحواره" in text:
        return "schema"
    if "شناختی" in text or "CBT" in text:
        return "cbt"
    if "تحلیل" in text:
        return "psychodynamic"
    if "زوج" in text or "هیجان" in text:
        return "couple"
    return "integrative"


def _license_type(headline, license_text):
    text = f"{headline} {license_text}".replace("\u200c", "")
    if "روانپزشک" in text:
        return "psychiatry"
    if "روانشناس" in text or "روانشناسی" in text:
        return "psychology"
    if "مشاور" in text:
        return "counseling"
    return "other"


def _license_number(value):
    digits = re.findall(r"[0-9۰-۹]+", latin_digits(value))
    if not digits:
        return "ثبت نشده"
    return "، ".join(digits)[:80]


def _introduction(headline, bio, rows):
    parts = [part for part in (headline, bio) if part]
    for key, label in (
        ("تحصیلات", "تحصیلات"),
        ("تخصصها", "تخصص‌ها"),
        ("رویکرد", "رویکرد"),
        ("مراجع از", "مراجع از"),
        ("محل کار", "محل کار"),
    ):
        if rows.get(key):
            parts.append(f"{label}: {rows[key]}")
    return "\n\n".join(parts)[:4000]


def _cells(slots, zone_name):
    try:
        zone = ZoneInfo(zone_name)
    except Exception:
        zone = ZoneInfo("America/Toronto")
    allowed = set(grid_starts())
    chosen = set()
    for raw in slots:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(zone)
        start = time(moment.hour, moment.minute)
        if start in allowed:
            chosen.add((moment.weekday(), start))
    return sorted(chosen)

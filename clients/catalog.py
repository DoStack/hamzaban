STATS = (
    {"value": "۲۴", "label": "درمانگر"},
    {"value": "۱٬۲۰۰", "label": "جلسه"},
    {"value": "۳۲", "label": "شهر"},
    {"value": "۴٫۸", "label": "رضایت"},
)

FAQS = (
    {
        "question": "هم‌زبان برای چیست؟",
        "answer": "هم‌زبان جایی برای دیدن درمانگر، انتخاب زمان جلسه و نگه داشتن حساب مراجع است. مسیر اول، تراپی است.",
    },
    {
        "question": "چطور درمانگر پیدا کنم؟",
        "answer": "در فهرست درمانگرها نام، موضوع یا شهر را جستجو کنید و صفحهٔ هر درمانگر را باز کنید.",
    },
    {
        "question": "زمان‌های صفحهٔ درمانگر قطعی است؟",
        "answer": "خیر. این زمان‌ها نمونهٔ برنامه هستند. رزرو نهایی هنوز به حساب و پرداخت وصل نشده است.",
    },
    {
        "question": "بدون حساب هم می‌توانم درمانگرها را ببینم؟",
        "answer": "بله. دیدن فهرست و صفحهٔ درمانگر برای همه باز است. ساخت حساب برای فضای شخصی مراجع است.",
    },
)

THERAPISTS = (
    {
        "slug": "sara-nikfar",
        "name": "سارا نیک‌فر",
        "title": "روان‌درمانگر",
        "focus": "اضطراب و خلق",
        "city": "تهران",
        "sessions": "۴۸۰ جلسه",
        "about": "سارا با مراجع‌های بزرگسال دربارهٔ اضطراب، بی‌خوابی و تغییر خلق کار می‌کند. جلسه‌ها آرام و مرحله‌به‌مرحله پیش می‌روند.",
        "schedule": (
            {"day": "شنبه", "times": ("۱۶:۰۰", "۱۸:۰۰")},
            {"day": "دوشنبه", "times": ("۱۰:۰۰", "۱۲:۳۰")},
            {"day": "چهارشنبه", "times": ("۱۷:۰۰",)},
        ),
    },
    {
        "slug": "kian-moradi",
        "name": "کیان مرادی",
        "title": "زوج‌درمانگر",
        "focus": "رابطه و گفت‌وگو",
        "city": "اصفهان",
        "sessions": "۳۱۰ جلسه",
        "about": "کیان به زوج‌ها کمک می‌کند اختلاف را روشن‌تر بگویند و برای قدم بعدی به توافق برسند.",
        "schedule": (
            {"day": "یکشنبه", "times": ("۱۱:۰۰", "۱۹:۰۰")},
            {"day": "سه‌شنبه", "times": ("۱۵:۰۰", "۱۷:۳۰")},
        ),
    },
    {
        "slug": "leila-bahrami",
        "name": "لیلا بهرامی",
        "title": "درمانگر کودک و نوجوان",
        "focus": "کودک و نوجوان",
        "city": "شیراز",
        "sessions": "۲۶۰ جلسه",
        "about": "لیلا با کودک، نوجوان و والدینشان کار می‌کند. موضوع‌های رایج، اضطراب مدرسه و رابطهٔ خانه است.",
        "schedule": (
            {"day": "شنبه", "times": ("۰۹:۳۰",)},
            {"day": "دوشنبه", "times": ("۱۴:۰۰", "۱۶:۰۰")},
            {"day": "پنجشنبه", "times": ("۱۱:۰۰",)},
        ),
    },
    {
        "slug": "arman-salehi",
        "name": "آرمان صالحی",
        "title": "روان‌شناس",
        "focus": "استرس شغلی",
        "city": "تهران",
        "sessions": "۱۹۰ جلسه",
        "about": "آرمان روی فشار کار، فرسودگی و تصمیم‌های شغلی کار می‌کند. جلسه‌ها کوتاه، مشخص و عملی هستند.",
        "schedule": (
            {"day": "یکشنبه", "times": ("۱۸:۰۰", "۲۰:۰۰")},
            {"day": "چهارشنبه", "times": ("۰۸:۳۰", "۱۳:۰۰")},
        ),
    },
)


def _normalize(value):
    return (
        value.strip()
        .replace("\u200c", "")
        .replace("ي", "ی")
        .replace("ك", "ک")
        .casefold()
    )


def search_therapists(query):
    needle = _normalize(query)
    if not needle:
        return THERAPISTS
    matches = []
    for therapist in THERAPISTS:
        haystack = _normalize(
            " ".join((therapist["name"], therapist["title"], therapist["focus"], therapist["city"]))
        )
        if needle in haystack:
            matches.append(therapist)
    return tuple(matches)


def get_therapist(slug):
    for therapist in THERAPISTS:
        if therapist["slug"] == slug:
            return therapist
    return None

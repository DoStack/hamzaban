from decimal import Decimal

SPECIALTIES = (
    "اضطراب",
    "خلق",
    "رابطه",
    "کودک و نوجوان",
    "تروما",
    "سوگ",
    "مهاجرت",
    "استرس شغلی",
    "خواب",
    "وسواس",
)
SPECIALTY_CHOICES = tuple((item, item) for item in SPECIALTIES)

EDUCATION = (
    "کارشناسی",
    "کارشناسی ارشد",
    "دکتری",
    "تخصص روان‌پزشکی",
    "فلوشیپ",
)
EDUCATION_CHOICES = tuple((item, item) for item in EDUCATION)

LANGUAGES = ("فارسی", "انگلیسی", "عربی", "ترکی", "آلمانی", "فرانسوی")
LANGUAGE_CHOICES = tuple((item, item) for item in LANGUAGES)

GENDERS = (
    ("female", "زن"),
    ("male", "مرد"),
    ("unspecified", "ترجیح می‌دهم نگویم"),
)

LICENSE_TYPES = (
    ("psychology", "روان‌شناسی"),
    ("counseling", "مشاوره"),
    ("psychiatry", "روان‌پزشکی"),
    ("other", "سایر"),
)

APPROACHES = (
    ("cbt", "شناختی‌رفتاری"),
    ("psychodynamic", "روان‌پویشی"),
    ("schema", "طرحواره‌درمانی"),
    ("act", "پذیرش و تعهد"),
    ("couple", "زوج‌درمانی"),
    ("integrative", "یکپارچه‌نگر"),
)

CURRENCIES = (
    ("IRR", "تومان"),
    ("EUR", "یورو"),
    ("USD", "دلار"),
)

TIMEZONES = (
    ("Asia/Tehran", "تهران"),
    ("Europe/Berlin", "برلین"),
    ("Europe/London", "لندن"),
    ("America/Toronto", "تورنتو"),
    ("America/Los_Angeles", "لس‌آنجلس"),
    ("UTC", "UTC"),
)

REJECTION_CODES = (
    ("unreadable", "مدرک ناخوانا"),
    ("unverifiable", "مجوز قابل راستی‌آزمایی نیست"),
    ("expired", "مجوز منقضی"),
    ("name_mismatch", "مغایرت نام"),
    ("other", "سایر"),
)

MOODS = (
    ("😊", "آفتابی"),
    ("😐", "ابری"),
    ("😔", "گرفته"),
    ("😣", "طوفانی"),
    ("😴", "خسته"),
)

DAY_LABELS = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنجشنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه",
}
DISPLAY_DAYS = (5, 6, 0, 1, 2, 3, 4)

SLOT_MINUTES = 30
DEFAULT_NOTICE_HOURS = 12
DEFAULT_HORIZON_DAYS = 30
DEFAULT_GAP_MINUTES = 10

UPLOAD_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def format_money(amount, currency):
    label = dict(CURRENCIES).get(currency, currency)
    if currency == "IRR":
        text = f"{Decimal(amount).quantize(Decimal('1')):,.0f}"
    else:
        text = f"{Decimal(amount):,.2f}"
    return f"{text} {label}"

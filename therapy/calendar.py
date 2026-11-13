from datetime import date, datetime, time, timedelta

MONTHS = (
    "",
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)
WEEKDAY_NAMES = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")

_G_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
_J_DAYS = [0, 31, 62, 93, 124, 155, 186, 216, 246, 276, 306, 336]
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def latin_digits(value):
    return str(value).translate(_DIGITS).strip()


def gregorian_to_jalali(gy, gm, gd):
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + _G_DAYS[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + (days % 31)
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + 78 + jd + _J_DAYS[jm - 1]
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    months = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > months[gm]:
        gd -= months[gm]
        gm += 1
    return gy, gm, gd


def month_length(jy, jm):
    for day in (31, 30, 29):
        gy, gm, gd = jalali_to_gregorian(jy, jm, day)
        if gregorian_to_jalali(gy, gm, gd) == (jy, jm, day):
            return day
    raise ValueError("ماه شمسی معتبر نیست.")


def parse_jalali_date(value):
    text = latin_digits(value)
    parts = text.split("-")
    if len(parts) != 3:
        raise ValueError
    jy, jm, jd = (int(part) for part in parts)
    if not 1 <= jm <= 12 or jd < 1 or jd > month_length(jy, jm):
        raise ValueError
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    return date(gy, gm, gd)


def format_jalali(value):
    if isinstance(value, datetime):
        value = value.date()
    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    return f"{jd} {MONTHS[jm]} {jy}"


def shift_month(jy, jm, delta):
    index = jy * 12 + (jm - 1) + delta
    return index // 12, index % 12 + 1


def month_bounds(jy, jm):
    length = month_length(jy, jm)
    start = date(*jalali_to_gregorian(jy, jm, 1))
    end = date(*jalali_to_gregorian(jy, jm, length))
    return start, end + timedelta(days=1)


def month_weeks(jy, jm):
    length = month_length(jy, jm)
    first = date(*jalali_to_gregorian(jy, jm, 1))
    pad = (first.weekday() - 5) % 7
    cells = [None] * pad + list(range(1, length + 1))
    while len(cells) % 7:
        cells.append(None)
    return [cells[index : index + 7] for index in range(0, len(cells), 7)]


def grid_starts():
    starts = []
    minute = 9 * 60
    while minute <= 22 * 60:
        starts.append(time(minute // 60, minute % 60))
        minute += 30
    return starts


def add_business_days(start, days):
    """Iranian business days: Thursday and Friday are the weekend."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() not in {3, 4}:
            added += 1
    return current

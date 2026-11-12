import os
import urllib.parse
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file():
    """Load simple KEY=VALUE entries from a local, ignored .env file."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env_file()


def csv_env(name, default=""):
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]


DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY and not DEBUG:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DEBUG is disabled.")
SECRET_KEY = SECRET_KEY or "dev-only-change-me"
ALLOWED_HOSTS = csv_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")
if os.environ.get("VERCEL"):
    ALLOWED_HOSTS.append(".vercel.app")
    vercel_url = os.environ.get("VERCEL_URL", "")
    if vercel_url and vercel_url not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(vercel_url)
        CSRF_TRUSTED_ORIGINS.append(f"https://{vercel_url}")

if not DEBUG and not os.environ.get("DATABASE_URL"):
    required_database_values = ("PGDATABASE", "PGUSER", "PGPASSWORD", "PGHOST")
    missing_database_values = [key for key in required_database_values if not os.environ.get(key)]
    if missing_database_values:
        missing = ", ".join(missing_database_values)
        raise ImproperlyConfigured(f"Set PostgreSQL settings for production: {missing}.")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "clients",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

def postgres_from_url(database_url):
    parsed = urllib.parse.urlparse(database_url)
    database = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": urllib.parse.unquote(parsed.username or ""),
        "PASSWORD": urllib.parse.unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }
    options = {
        key: values[-1]
        for key, values in urllib.parse.parse_qs(parsed.query).items()
        if key in {"sslmode", "sslrootcert", "channel_binding"}
    }
    if options:
        database["OPTIONS"] = options
    return database


DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASES = {
    "default": postgres_from_url(DATABASE_URL) if DATABASE_URL else {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "hamzaban"),
        "USER": os.environ.get("PGUSER", "postgres"),
        "PASSWORD": os.environ.get("PGPASSWORD", "postgres" if DEBUG else ""),
        "HOST": os.environ.get("PGHOST", "127.0.0.1"),
        "PORT": os.environ.get("PGPORT", "5433" if DEBUG else "5432"),
    }
}

LANGUAGE_CODE = "fa"
LANGUAGES = [("fa", "فارسی"), ("en", "English")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/profile/"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

UNFOLD = {
    "SITE_TITLE": "Hamzaban",
    "SITE_HEADER": "هم‌زبان",
    "SITE_SUBHEADER": "پنل مدیریت",
    "SITE_SYMBOL": "psychology",
    "COLORS": {
        "primary": {
            "50": "236 253 248",
            "100": "204 251 241",
            "200": "153 246 228",
            "300": "94 210 186",
            "400": "58 186 158",
            "500": "58 165 140",
            "600": "45 140 118",
            "700": "36 115 97",
            "800": "29 90 76",
            "900": "24 74 62",
            "950": "13 42 35",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "مدیریت",
                "separator": True,
                "collapsible": False,
                "items": [
                    {"title": "داشبورد", "icon": "dashboard", "link": reverse_lazy("admin:index")},
                    {
                        "title": "کاربران",
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "گروه‌ها",
                        "icon": "admin_panel_settings",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
    "STYLES": [lambda request: static("css/admin.css")],
    "SCRIPTS": [
        lambda request: static("js/admin-mobile-table.js"),
        lambda request: static("js/admin-logout-confirm.js"),
    ],
}

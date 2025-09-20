from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------------------
# django-environ Setup
# ------------------------------------------------------------------------------
env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_TIME_ZONE=(str, "Europe/Zurich"),
    DJANGO_USE_TZ=(bool, True),

    # WhiteNoise: in Prod standardmäßig an, in Dev standardmäßig aus
    DJANGO_USE_WHITENOISE=(bool, None),  # None = "auto": !DEBUG -> True, DEBUG -> False

    # Security (Prod-Defaults konservativ)
    DJANGO_SECURE_SSL_REDIRECT=(bool, None),  # None = auto: !DEBUG -> True, DEBUG -> False
    DJANGO_SESSION_COOKIE_SECURE=(bool, None),
    DJANGO_CSRF_COOKIE_SECURE=(bool, None),
    DJANGO_SECURE_HSTS_SECONDS=(int, 3600),
    DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),
    DJANGO_SECURE_HSTS_PRELOAD=(bool, True),

    # Optional: CSRF Trusted Origins
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# ------------------------------------------------------------------------------
# Core
# ------------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# ------------------------------------------------------------------------------
# Apps
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "moods",
]

# ------------------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise fügen wir ggf. weiter unten konditional ein
    "django.contrib.sessions.middleware.SessionMiddleware",
    # i18n: muss NACH SessionMiddleware und VOR CommonMiddleware stehen
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Wenn du ausschließlich App-Templates nutzt, kannst du DIRS auf [] setzen
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",  # <— i18n
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"

# ------------------------------------------------------------------------------
# Datenbank
#   - Default: SQLite
#   - Optional: via DATABASE_URL (z. B. postgresql://user:pass@host:5432/dbname)
# ------------------------------------------------------------------------------
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
DATABASES = {
    "default": env.db("DATABASE_URL", default=DEFAULT_SQLITE_URL),
}

# ------------------------------------------------------------------------------
# Auth / Passwords
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------------------
# i18n / TZ / Formate
# ------------------------------------------------------------------------------
# Hinweis: Für unsere Sprachauswahl nutzen wir 'de' als Default-UI-Sprache.
LANGUAGE_CODE = "de"

# Alle unterstützten Sprachen (für das Dropdown)
LANGUAGES = [
    ("de", "Deutsch"),
    ("gsw", "Schwiizerdütsch"),
    ("pl", "Polski"),
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),
]

# Pfad für Übersetzungsdateien
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = env("DJANGO_TIME_ZONE")
USE_I18N = True
USE_TZ = env.bool("DJANGO_USE_TZ")

DATE_FORMAT = "d.m.Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = "d.m.Y H:i"
SHORT_DATE_FORMAT = "d.m.Y"
SHORT_DATETIME_FORMAT = "d.m.Y H:i"

# ------------------------------------------------------------------------------
# Static Files
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
# Falls du nur App-Static nutzt, kannst du STATICFILES_DIRS auskommentieren
# STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise-Schalter (auto: in Prod aktiv, in Dev aus)
_use_whitenoise = env("DJANGO_USE_WHITENOISE")
if _use_whitenoise is None:
    USE_WHITENOISE = not DEBUG
else:
    USE_WHITENOISE = bool(_use_whitenoise)

if USE_WHITENOISE:
    # Middleware direkt nach SecurityMiddleware einfügen
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    # Django 5: STORAGES statt STATICFILES_STORAGE
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# --- WhiteNoise Feintuning (harmlos, auch wenn WhiteNoise aus ist) ---
# In Dev schnelleres Feedback; in Prod moderate Max-Age für nicht-gehashte Dateien.
WHITENOISE_AUTOREFRESH = DEBUG and USE_WHITENOISE
WHITENOISE_MAX_AGE = 60 if DEBUG else 3600  # 1 min Dev, 1 h Prod (gehashte Dateien bekommen far-future)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------------------
# Auth Redirects
# ------------------------------------------------------------------------------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ------------------------------------------------------------------------------
# Logging (einfach)
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple", "level": "INFO"}
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ------------------------------------------------------------------------------
# Security (Prod-Defaults automatisch)
# ------------------------------------------------------------------------------
def _auto(default_if_prod: bool) -> bool:
    """Hilfslogik: None = auto: Prod->True, Dev->False"""
    return default_if_prod if not DEBUG else False

_SEC_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = env("DJANGO_SESSION_COOKIE_SECURE") if _SEC_SSL_REDIRECT is not None else _auto(True)
CSRF_COOKIE_SECURE = env("DJANGO_CSRF_COOKIE_SECURE") if _SEC_SSL_REDIRECT is not None else _auto(True)

if _SEC_SSL_REDIRECT is None:
    SECURE_SSL_REDIRECT = _auto(True)
else:
    SECURE_SSL_REDIRECT = bool(_SEC_SSL_REDIRECT)

# HSTS nur sinnvoll in Prod
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD")

# CSRF Trusted Origins (z.B. https://app.example.com)
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

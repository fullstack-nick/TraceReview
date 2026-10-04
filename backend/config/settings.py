import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_DIR = BASE_DIR / ".local"
LOCAL_DIR.mkdir(exist_ok=True)
SECRET_FILE = LOCAL_DIR / "secret_key"
if not SECRET_FILE.exists():
    try:
        with SECRET_FILE.open("x", encoding="utf-8") as file:
            file.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
SECRET_KEY = SECRET_FILE.read_text(encoding="utf-8").strip()
DEBUG = os.environ.get("TRACEREVIEW_DEBUG") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.staticfiles", "rest_framework", "review",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "review.middleware.RequestLimitsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.environ.get("TRACEREVIEW_DB", str(LOCAL_DIR / "tracereview.sqlite3")),
    "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 5},
    "TEST": {"NAME": str(LOCAL_DIR / "unit-test.sqlite3")},
}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_NAME = "tracereview_sessionid"
CSRF_COOKIE_NAME = "tracereview_csrftoken"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:5173", "http://127.0.0.1:5174"] if DEBUG else []
CSRF_FAILURE_VIEW = "review.errors.csrf_failure"
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288
FILE_UPLOAD_MAX_MEMORY_SIZE = 262144
DATA_UPLOAD_MAX_NUMBER_FILES = 1
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10
FILE_UPLOAD_HANDLERS = [
    "review.middleware.BoundedUploadHandler",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "review.errors.exception_handler",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}
STATIC_URL = "/static/"
STATIC_ROOT = LOCAL_DIR / "static"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STATICFILES_DIRS = [("app", FRONTEND_DIST)] if FRONTEND_DIST.exists() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"file": {"class": "logging.FileHandler", "filename": str(LOCAL_DIR / "server.log")}},
    "loggers": {"django.request": {"handlers": ["file"], "level": "WARNING", "propagate": False}},
}


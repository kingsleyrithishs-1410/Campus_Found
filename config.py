"""Application configuration.

Values come from environment variables (or a local .env file). SQLite is used
when DATABASE_URL is not set; set DATABASE_URL to a MySQL URL for production,
for example: mysql+pymysql://user:password@localhost/lost_found?charset=utf8mb4
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

import campus_data

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# DATA_DIR = one folder for everything that must survive restarts (database +
# uploads). On hosts like Railway, mount a persistent volume and point this at it.
DATA_DIR = os.environ.get("DATA_DIR", "").strip()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-insecure-key-change-me"

    # ---- Database -------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(DATA_DIR, "lost_found.db") if DATA_DIR else None
    ) or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "lost_found.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # ---- Uploads (kept outside /static so nothing is served directly) ---
    UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT") or os.path.join(DATA_DIR or BASE_DIR, "uploads")
    # Set TRUST_PROXY=1 when running behind a hosting proxy (Railway, Render, Nginx)
    # so client IPs (rate limits, audit log) and https are detected correctly.
    TRUST_PROXY = _bool("TRUST_PROXY", False)
    MAX_IMAGE_BYTES = 5 * 1024 * 1024          # 5 MB per image
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024       # whole request (image + form fields)
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    IMAGE_MAX_DIMENSION = 1600                 # images are re-encoded and downscaled

    # ---- Accounts -------------------------------------------------------
    # Comma-separated list, e.g. "mycollege.edu,students.mycollege.edu".
    # Empty means any email domain is accepted (handy for local development).
    # Not set = the university domain from campus_data.py. Set it to an empty
    # value (ALLOWED_EMAIL_DOMAINS=) to allow any email address.
    ALLOWED_EMAIL_DOMAINS = [
        d.strip().lower().lstrip("@")
        for d in os.environ.get("ALLOWED_EMAIL_DOMAINS", ",".join(campus_data.EMAIL_DOMAINS)).split(",")
        if d.strip()
    ]
    EMAIL_VERIFICATION_REQUIRED = _bool("EMAIL_VERIFICATION_REQUIRED", False)
    ADMIN_NAME = os.environ.get("ADMIN_NAME", "Campus Admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    # ---- Mail (verification links). Empty MAIL_SERVER = print to console --
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_FROM = os.environ.get("MAIL_FROM", "lost-found@localhost")

    # ---- Sessions & security -------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 8 * 3600
    RATELIMIT_ENABLED = _bool("RATELIMIT_ENABLED", True)

    # ---- Campus (admins can change these in Admin -> Settings) ----------
    CAMPUS_NAME = os.environ.get("CAMPUS_NAME", campus_data.CAMPUS_NAME)
    CAMPUS_LAT = _float("CAMPUS_LAT", campus_data.CAMPUS_LAT)
    CAMPUS_LNG = _float("CAMPUS_LNG", campus_data.CAMPUS_LNG)
    CAMPUS_ZOOM = int(os.environ.get("CAMPUS_ZOOM", campus_data.CAMPUS_ZOOM))

    # ---- Display & matching ---------------------------------------------
    DISPLAY_TIMEZONE = os.environ.get("DISPLAY_TIMEZONE", "Asia/Kolkata")
    MATCH_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", "45"))
    NEARBY_METERS = int(os.environ.get("NEARBY_METERS", "250"))
    FEED_PAGE_SIZE = 12


class DevelopmentConfig(Config):
    DEBUG = True


class LocalConfig(Config):
    """Production behaviour on your own computer or campus network over plain
    HTTP (used by the start scripts). Behind HTTPS, use "production"."""
    DEBUG = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    ALLOWED_EMAIL_DOMAINS = []
    EMAIL_VERIFICATION_REQUIRED = False


CONFIGS = {
    "development": DevelopmentConfig,
    "local": LocalConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

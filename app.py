"""Campus Lost & Found Management System - application factory.

Run locally:
    pip install -r requirements.txt
    flask --app app init-db          # creates tables + default campus locations
    flask --app app create-admin     # prompts for an admin account
    flask --app app run
"""
import os

import click
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError, generate_csrf

import campus_data
from config import CONFIGS
from extensions import csrf, db
from models import CATEGORIES, CATEGORY_ICONS, CampusLocation, ItemStatus, Role, User
from services.notifications import ICONS as NOTIFICATION_ICONS
from services.notifications import unread_count
from services.settings import get_setting, map_config
from services.uploads import ensure_upload_dirs
from utils import template_helpers



def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_CONFIG", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIGS[config_name])

    if config_name == "production" and app.config["SECRET_KEY"].startswith("dev-only"):
        raise RuntimeError("Set a strong SECRET_KEY environment variable in production.")

    if app.config.get("TRUST_PROXY"):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)
    data_dir = os.environ.get("DATA_DIR", "").strip()
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)
    template_helpers.register(app)

    from routes import admin, auth, chat, claims, items, main
    for module in (main, auth, items, claims, chat, admin):
        app.register_blueprint(module.bp)

    with app.app_context():
        ensure_upload_dirs()
        if config_name != "testing":
            db.create_all()
            seed_locations()
            ensure_admin_from_env(app)

    register_hooks(app)
    register_errors(app)
    register_cli(app)
    return app


# --------------------------------------------------------------------------
def register_hooks(app):
    @app.before_request
    def first_run_setup():
        """Until an administrator exists, every page leads to the setup page."""
        if app.config.get("TESTING") or app.config.get("_HAS_ADMIN"):
            return None
        if User.query.filter_by(role=Role.ADMIN).first() is not None:
            app.config["_HAS_ADMIN"] = True
            return None
        if request.endpoint not in ("auth.setup", "static"):
            return redirect(url_for("auth.setup"))
        return None

    @app.before_request
    def load_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id is None:
            return
        user = db.session.get(User, user_id)
        if user is None or not user.is_active:
            session.clear()
            if user is not None:
                flash("This account has been blocked by an administrator.", "error")
            return
        g.user = user

    @app.context_processor
    def inject_globals():
        return {
            "current_user": g.get("user"),
            "unread_notifications": unread_count(g.get("user")),
            "CATEGORIES": CATEGORIES,
            "CATEGORY_ICONS": CATEGORY_ICONS,
            "NOTIFICATION_ICONS": NOTIFICATION_ICONS,
            "NOTE_ICONS": {
                "possible_match": "bell", "claim_received": "user", "claim_approved": "lock",
                "claim_rejected": "x", "new_message": "chat", "item_returned": "check",
                "admin_warning": "info", "admin_notice": "shield",
            },
            "ItemStatus": ItemStatus,
            "campus_name": get_setting("campus_name"),
            "college_email_only": bool(app.config.get("ALLOWED_EMAIL_DOMAINS")),
            "map_config": map_config(),
            "csrf_token": generate_csrf,
        }

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if g.get("user") is not None:
            response.headers.setdefault("Cache-Control", "private, no-store")
        return response


def register_errors(app):
    def render_error(code, title, message):
        return render_template("error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def bad_request(e):
        return render_error(400, "Something in that request wasn't right", "Go back, check the form and try again.")

    @app.errorhandler(403)
    def forbidden(e):
        return render_error(403, "You don't have access to this page", "This area is limited to the people involved and administrators.")

    @app.errorhandler(404)
    def not_found(e):
        return render_error(404, "Page not found", "The page doesn't exist, or the report is no longer public.")

    @app.errorhandler(413)
    def too_large(e):
        flash("That upload is too large. Photos must be 5 MB or smaller.", "error")
        return redirect(request.referrer or url_for("main.feed")), 303

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        flash("Your form expired. Please try again.", "error")
        return redirect(request.referrer or url_for("main.index")), 303

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_error(500, "Something went wrong on our side", "Try again in a moment.")


# --------------------------------------------------------------------------
def seed_locations():
    """Load the campus places from campus_data.py on first start."""
    if CampusLocation.query.first() is not None:
        return
    for name, lat, lng, handover in campus_data.LOCATIONS:
        db.session.add(CampusLocation(name=name, latitude=lat, longitude=lng,
                                      is_handover_point=handover))
    db.session.commit()


def ensure_admin_from_env(app):
    """Create the first admin from ADMIN_EMAIL / ADMIN_PASSWORD if set."""
    email = (app.config.get("ADMIN_EMAIL") or "").strip().lower()
    password = app.config.get("ADMIN_PASSWORD")
    if not email or not password or User.query.filter_by(email=email).first():
        return
    admin = User(name=app.config["ADMIN_NAME"], email=email, role=Role.ADMIN, email_verified=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    app.logger.info("Created admin account %s", email)


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables and the default campus locations."""
        db.create_all()
        seed_locations()
        click.echo("Database ready.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Create an administrator (or promote an existing user)."""
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = Role.ADMIN
            click.echo(f"{email} promoted to admin.")
        else:
            if len(password) < 8:
                raise click.BadParameter("Password must be at least 8 characters.")
            user = User(name=name.strip(), email=email, role=Role.ADMIN, email_verified=True)
            user.set_password(password)
            db.session.add(user)
            click.echo(f"Admin {email} created.")
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))

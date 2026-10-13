"""Start campusfound.

    python run.py              # serves on port 5000 for this computer and your Wi-Fi network
    python run.py --port 8080

On first start this creates a .env file with a random secret key, creates the
database with the default campus locations, and then asks you (in the browser)
to create the administrator account.
"""
import argparse
import os
import secrets
import socket
import sys
import threading
import webbrowser

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def ensure_env_file():
    if os.path.exists(ENV_PATH):
        # Earlier versions wrote a .env that only allowed one university's
        # emails. Open sign-up to every address (Gmail included).
        with open(ENV_PATH, encoding="utf-8") as fh:
            text = fh.read()
        if "ALLOWED_EMAIL_DOMAINS=hindustanuniv.ac.in" in text:
            text = text.replace("ALLOWED_EMAIL_DOMAINS=hindustanuniv.ac.in", "ALLOWED_EMAIL_DOMAINS=")
            with open(ENV_PATH, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("Updated .env: any email address (Gmail included) can now register.")
        return
    with open(ENV_PATH, "w", encoding="utf-8") as fh:
        fh.write(
            "# Created automatically on first start. Keep this file private.\n"
            "FLASK_CONFIG=local\n"
            f"SECRET_KEY={secrets.token_hex(32)}\n"
            "# To allow only your college emails, list the domain(s), e.g.\n"
            "# ALLOWED_EMAIL_DOMAINS=mycollege.edu\n"
            "ALLOWED_EMAIL_DOMAINS=\n"
        )
    print("Created .env with a new secret key.")


def lan_address():
    """Best guess at this computer's address on the local network."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))   # no packets are sent for UDP connect
            return s.getsockname()[0]
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Start campusfound")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    parser.add_argument("--host", default="0.0.0.0", help="0.0.0.0 = reachable from your Wi-Fi network")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    hosted = bool(os.environ.get("PORT"))   # set by hosting platforms
    if not hosted:
        ensure_env_file()               # hosts provide settings as environment variables
    sys.path.insert(0, BASE_DIR)
    from app import app  # creates tables and campus locations on first start

    try:
        from waitress import serve
    except ImportError:
        print("waitress is not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    local_url = f"http://127.0.0.1:{args.port}"
    print("\n  campusfound is running")
    print(f"  On this computer:      {local_url}")
    ip = None if hosted else lan_address()
    if ip and args.host == "0.0.0.0":
        print(f"  On phones (same Wi-Fi): http://{ip}:{args.port}")
    print("  Press Ctrl+C to stop.\n")

    if not args.no_browser and not hosted:
        threading.Timer(1.5, lambda: webbrowser.open(local_url)).start()
    serve(app, host=args.host, port=args.port, threads=8)


if __name__ == "__main__":
    main()

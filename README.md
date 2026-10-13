# campusfound: Campus Lost & Found Management System

A Flask web app for a college campus. People can report lost and found items, tag where it happened on a campus map, get possible matches, and claim items with private proof. Each claim gets its own conversation, and items are returned through a tracked hand-over.

**Report → Locate → Match → Verify → Communicate → Return → Complete**

## Design

The interface uses a green campus theme: cream paper, deep teal (`#1E6B5E`), a mustard accent, Outfit for text, Instrument Serif italics and JetBrains Mono labels.
- Board page: a large hero, a live board of report cards and a "Browse by location" map card.
- "I lost something" / "I found something" open the report form as a pop-up. Without JavaScript they open the same form as a page.
- Sign in and register use a split dark/light layout.
- Fonts are self-hosted in `static/fonts` (SIL Open Font License), so the app needs no external font service. The design tokens are at the top of `static/css/style.css`.

## Start it (Windows, macOS, Linux)

You need **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/); on Windows tick "Add python.exe to PATH").

- **Windows:** double-click `start.bat`.
- **macOS / Linux:** run `./start.sh` in a terminal.

The first start takes a minute: it creates a private `.venv`, installs the packages and makes a `.env` with a random secret key. It also creates the database with the default campus locations. Your browser then opens on **campusfound** and asks you to create the **administrator account**. After that, students register with their college email.

The terminal shows two addresses:
- `http://127.0.0.1:5000` for your computer.
- `http://<your-ip>:5000` for phones on the **same Wi-Fi**. Windows may ask to allow Python through the firewall; allow it on private networks.

Keep the window open while you use the app. Close it or press Ctrl+C to stop. Your data stays in `instance/lost_found.db` and `uploads/`.

Run the tests (optional): `pip install -r requirements-dev.txt` then `python -m pytest -q`.

## Your campus

The first start loads the 12 default places from `campus_data.py`: Main Gate, Main Block, Library, Canteen, Cafeteria, Laboratory, Computer Science Block, Administrative Block, Auditorium, Ground, Parking and Hostel.

- **Move them onto your campus:** set the map centre in **Admin → Settings**. Then, in **Admin → Campus locations**, click the map to reposition, rename, add or hide places, and tick the approved hand-over points.
- **Limit sign-ups:** by default any email can register. To allow only college emails, set `ALLOWED_EMAIL_DOMAINS=yourcollege.edu` in `.env` and restart.
- **Map background:** it needs internet (OpenStreetMap tiles). Everything else works offline.

## Put it online (Railway)

The project includes a `Dockerfile`, so Railway, Render, Fly.io, Koyeb or any Docker host can run it. **Railway** is the simplest fit: its plans include a persistent volume, so the database and uploaded photos survive restarts and redeploys. Railway's pricing changes, so check railway.com before relying on the free credit.

1. Put the project on GitHub (see "Push to GitHub" below).
2. On railway.com, sign in with GitHub, then **New Project → Deploy from GitHub repo** and pick the repository. Railway finds the `Dockerfile` and builds it.
3. In the service's **Variables**, add `SECRET_KEY` with a long random value. You can make one with `python -c "import secrets; print(secrets.token_hex(32))"`. The Dockerfile already sets `FLASK_CONFIG=production`, `TRUST_PROXY=1` and `DATA_DIR=/data`.
4. Add a **Volume** to the service with mount path **`/data`**. The database and photos live there.
5. In **Settings → Networking**, click **Generate Domain**. Open the `https://…up.railway.app` link and create the admin account.

To limit sign-ups to your college, also add `ALLOWED_EMAIL_DOMAINS=yourcollege.edu` in Variables.

**Without a volume, data is lost on every redeploy.** The same applies to Render's free plan, which can't attach a disk. There, the app works but forgets posts and photos.

### Push to GitHub

```
git init -b main
git add -A
git commit -m "campusfound"
git remote add origin https://github.com/YOUR-USERNAME/campusfound.git
git push -u origin main
```

## MySQL (production)

```sql
CREATE DATABASE lost_found CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lostfound'@'localhost' IDENTIFIED BY 'a-strong-password';
GRANT ALL ON lost_found.* TO 'lostfound'@'localhost';
```

```
DATABASE_URL=mysql+pymysql://lostfound:a-strong-password@localhost/lost_found?charset=utf8mb4
FLASK_CONFIG=production
```

Then run `flask --app app init-db`. Tables are created with `db.create_all()`. If the schema changes later, add Flask-Migrate (Alembic) for migrations.

Run behind HTTPS, for example `gunicorn -w 3 -b 127.0.0.1:8000 app:app` behind Nginx with TLS. The production config sets secure cookies and HSTS, and refuses to start without a real `SECRET_KEY`.

## How it works

| Area | Where |
|---|---|
| App factory, security headers, CLI | `app.py` |
| Settings from env | `config.py` |
| Tables (User, Item, Claim, Message, Report, Notification, CampusLocation, AuditLog, AppSetting) | `models.py` |
| Claim/item status rules (one place) | `services/workflow.py` |
| Possible matching (category, name, description, location distance, date) | `services/matching.py` |
| Chat safety filter | `services/moderation.py` |
| Notifications (in-app, pluggable channels) | `services/notifications.py` |
| Upload validation and EXIF stripping | `services/uploads.py` |
| Routes | `routes/` (`auth`, `main`, `items`, `claims`, `chat`, `admin`) |
| Templates / CSS / JS | `templates/`, `static/` (Leaflet 1.9.4 bundled in `static/vendor`) |

### Item status

`ACTIVE → CLAIM_REQUESTED → CLAIM_APPROVED → COMPLETED`. If a claim is rejected and no other claim is open, the item returns to `ACTIVE`. Only `ACTIVE` items appear in the public feed. Completed, closed and removed records are never deleted, and admins can see them under **Completed history**.

The model also defines a `RETURNED` status, but nothing sets it: when the finder clicks **Mark item as returned**, the item goes straight to `COMPLETED` (with `completed_at`) and the claim becomes `returned`.

### Decisions you may want to revisit

- **Claimed items leave the feed.** The spec says only `ACTIVE` items are public, so an item disappears from the feed as soon as someone claims it. Other people can still reach it through possible matches and claim it too. When the finder approves one claim, the other open claims are closed automatically.
- **Roles.** Users are stored as `user` or `admin`. "Finder" is not a stored role: it means whoever reported the found item.
- **Chat rules.** Phone numbers, links, email/UPI addresses, payment requests and abusive words are **blocked**. Mentions of addresses, off-campus meetings or money are **saved but flagged** for admins. The word lists in `services/moderation.py` are a starting point; extend them for your campus languages.
- **Proof privacy.** Proof text and photos are visible only to the finder, the claimant and admins. Proof photos are stored in `uploads/private/proofs` and served only through an authorization check. Item photos are visible to logged-in users only, and closed items hide their photos from outsiders.
- **Map privacy.** Public maps show a ~110 m circle instead of the exact pin.
- **Chat delivery** polls every 5 s. The JSON endpoints (`/claims/<id>/messages`, `/messages.json`) can move to WebSockets later.

## Security checklist

Done in code: Werkzeug password hashing, session fixation protection, login/admin decorators, CSRF on every form (Flask-WTF), per-IP/per-user rate limits, upload type/size checks with Pillow re-encoding (which strips EXIF/GPS), private proof storage, a CSP and other security headers, audit logs, and 404s (not 403s) for private claims.

For production you still need to:
- Serve over HTTPS.
- Set `EMAIL_VERIFICATION_REQUIRED=true` with real SMTP settings.
- Use a shared rate-limit store if you run several workers. The built-in limiter is in-memory per process.
- Plug a virus scanner into `scan_for_malware()` in `services/uploads.py` if your policy requires one.
- Move `UPLOAD_ROOT` outside the code folder and back it up.

## Future AI hooks

- `services/matching.SCORERS`: append an image- or text-similarity scorer.
- `services/moderation.EXTRA_CHECKS`: add a scam-detection classifier.
- `routes/chat.suggestions_for`: replace with smart suggestions.
- `services/notifications.CHANNELS`: add email or push delivery.

Matching only recommends. Ownership is always approved by a person.

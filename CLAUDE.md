# CLAUDE.md — nagoya-travel

This file documents the codebase for AI assistants (Claude Code, etc.).

## Project Overview

A FastAPI web application for managing and displaying a travel itinerary for a Nagoya trip (May 3–4, 2025). It has two surfaces:

- **Public site** — read-only view of travel days and spots
- **Admin panel** — password-protected CRUD for days and spots

Deployed on [Render.com](https://render.com) (free tier) with PostgreSQL.

---

## Repository Structure

```
nagoya-travel/
├── main.py              # FastAPI app — all routes and business logic
├── models.py            # SQLAlchemy ORM models (Day, Spot)
├── database.py          # DB engine, session factory, Base
├── requirements.txt     # Python dependencies (pinned)
├── render.yaml          # Render.com deployment config
├── install.cmd          # Claude Code Windows installer (unrelated to the app)
├── .env.example         # Environment variable template
├── .gitignore
├── templates/
│   ├── base.html        # Shared layout (Bootstrap 5 navbar + footer)
│   ├── index.html       # Home page — card grid of travel days
│   ├── day.html         # Day detail — timeline of spots
│   └── admin/
│       ├── login.html
│       ├── dashboard.html
│       ├── day_form.html
│       ├── spot_form.html
│       └── spots.html
└── static/
    └── css/
        └── style.css    # Custom styles (hero, category badges, spot cards)
```

> `install.cmd` is a Claude Code Windows bootstrap installer that was committed to the repo but is **not** part of the travel application.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115 |
| Templating | Jinja2 3.1 via `fastapi.templating` |
| ORM | SQLAlchemy 2.0 |
| Local DB | SQLite (`nagoya_travel.db`) |
| Production DB | PostgreSQL (Render managed) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons 1.11 (CDN) |
| Server | Uvicorn |
| Python | 3.12.3 |

---

## Data Models (`models.py`)

### `Day`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `date` | String(20) | e.g. `"2025-05-03"` |
| `title` | String(100) | |
| `description` | Text | defaults to `""` |
| `spots` | relationship | ordered by `order_index`, cascade delete |

### `Spot`
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `day_id` | Integer FK → `days.id` | |
| `name` | String(100) | |
| `category` | String(50) | one of the five categories below |
| `time` | String(10) | e.g. `"10:51"` |
| `notes` | Text | |
| `map_url` | String(500) | optional Google Maps link |
| `order_index` | Integer | display order within a day |

### Spot categories
The valid category values (defined as `CATEGORIES` in `main.py`) are:
```python
["観光", "食事", "カフェ", "宿泊", "移動"]
```
These drive CSS class names for badge/card/icon styling (e.g. `.badge-観光`, `.spot-観光`, `.cat-icon-観光`).

---

## Database Setup (`database.py`)

- Reads `DATABASE_URL` from the environment; defaults to `sqlite:///./nagoya_travel.db`.
- Automatically rewrites `postgres://` → `postgresql://` for Render's legacy connection strings.
- `connect_args={"check_same_thread": False}` is applied only for SQLite.
- `get_db()` is a FastAPI dependency that yields a `SessionLocal` and closes it after the request.
- Tables are created at startup via `models.Base.metadata.create_all(bind=engine)` in `main.py`.

---

## Application Entry Point (`main.py`)

### Startup behaviour
1. `models.Base.metadata.create_all(bind=engine)` — creates tables if missing.
2. `seed_initial_data()` — inserts the two-day itinerary if `days` table is empty. Safe to call on every restart.

### Authentication
- Cookie-based; cookie name `nagoya_admin`, value `"ok"`.
- Password compared against `ADMIN_PASSWORD` env var (default `"changeme"` — **must be changed in production**).
- `is_admin(request)` helper is called at the top of every admin route.
- No session store; the cookie value is not a token — anyone who sets the cookie to `"ok"` is authenticated. This is intentional for a simple personal app.

### Route map

**Public**
| Method | Path | Template |
|---|---|---|
| GET | `/` | `templates/index.html` |
| GET | `/day/{day_id}` | `templates/day.html` |

**Admin — auth**
| Method | Path | Notes |
|---|---|---|
| GET | `/admin/login` | Redirects to `/admin` if already logged in |
| POST | `/admin/login` | Sets cookie on success, redirects to `/admin/login?error=1` on failure |
| GET | `/admin/logout` | Deletes cookie, redirects to `/` |

**Admin — Day CRUD**
| Method | Path | Action |
|---|---|---|
| GET | `/admin` | Dashboard — list all days |
| GET | `/admin/days/new` | New day form |
| POST | `/admin/days` | Create day |
| GET | `/admin/days/{day_id}/edit` | Edit day form |
| POST | `/admin/days/{day_id}/edit` | Update day |
| POST | `/admin/days/{day_id}/delete` | Delete day (cascades to spots) |

**Admin — Spot CRUD**
| Method | Path | Action |
|---|---|---|
| GET | `/admin/days/{day_id}/spots` | List spots for a day |
| GET | `/admin/days/{day_id}/spots/new` | New spot form |
| POST | `/admin/days/{day_id}/spots` | Create spot |
| GET | `/admin/spots/{spot_id}/edit` | Edit spot form |
| POST | `/admin/spots/{spot_id}/edit` | Update spot |
| POST | `/admin/spots/{spot_id}/delete` | Delete spot |

> FastAPI is used purely as an HTML server here — no JSON API endpoints exist.

---

## Templates & Frontend

- All templates extend `templates/base.html`.
- Bootstrap 5.3 and Bootstrap Icons 1.11 are loaded from CDN — no npm/build step.
- Custom styles live entirely in `static/css/style.css`.
- Category-specific styling uses Japanese strings directly as CSS class suffixes (e.g. `badge-観光`). When adding a new category, update `CATEGORIES` in `main.py` **and** add corresponding CSS rules in `style.css`.
- The hero gradient (`#b71c1c → #880e4f`) is defined both in `style.css` (`.hero`) and inline in `base.html`'s navbar.

---

## Local Development

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set ADMIN_PASSWORD to something secure

# 4. Run the dev server (auto-reload)
uvicorn main:app --reload
```

The app will be available at `http://localhost:8000`.
Admin panel: `http://localhost:8000/admin` (password from `.env`).

SQLite database file (`nagoya_travel.db`) is created automatically on first run and is gitignored.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_PASSWORD` | `changeme` | Password for the admin panel |
| `DATABASE_URL` | `sqlite:///./nagoya_travel.db` | SQLAlchemy database URL |

On Render, `ADMIN_PASSWORD` is auto-generated and `DATABASE_URL` is injected from the managed PostgreSQL instance.

---

## Deployment (Render.com)

Configuration is in `render.yaml`:

- **Web service** `nagoya-travel` (free plan, Python 3.12.3)
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Database** `nagoya-travel-db` (PostgreSQL, free plan)

To deploy: push to `main`. Render auto-deploys on push.

The `postgres://` → `postgresql://` rewrite in `database.py` handles Render's legacy connection string format.

---

## Key Conventions

1. **No test suite** — the project has no automated tests. Verify changes manually.
2. **No migrations** — schema changes require dropping and recreating tables, or manual `ALTER TABLE`. `create_all` is additive-only.
3. **POST for deletes** — HTML forms cannot send DELETE requests; all delete actions use `POST`.
4. **`order_index` is set on creation only** — new spots are appended (`order_index = len(day.spots)`). There is no reorder endpoint.
5. **Seed data is idempotent** — `seed_initial_data()` checks `Day.count() > 0` before inserting; safe to run on every boot.
6. **Admin auth is stateless** — the session cookie holds a literal `"ok"` value, not a signed token. Do not use this pattern for sensitive data.
7. **Commit messages** follow Conventional Commits (`feat:`, `fix:`, `docs:`, etc.).
8. **Japanese UI strings** — the app UI is entirely in Japanese. Keep new UI text in Japanese.

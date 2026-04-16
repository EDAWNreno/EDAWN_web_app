# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About the Project

EDAWN Business Builders Portal — a Django web app for managing volunteer outreach to businesses in Northern Nevada. Volunteers are assigned companies, log contact attempts and visits, and earn badges for milestones. Staff admins manage companies, assignments, and user accounts.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (requires SECRET_KEY env var)
SECRET_KEY=any-local-key python manage.py runserver

# System check
SECRET_KEY=any-local-key python manage.py check

# Apply migrations
python manage.py migrate

# Seed test data (creates companies, users, assignments)
python manage.py seed_data

# Create a local superuser
python manage.py createsuperuser

# Production build (Render runs this via build.sh)
./build.sh
```

There are no tests — `core/tests.py` is empty.

## Environment Variables

`SECRET_KEY` is required; the app raises `RuntimeError` at startup without it. All others are optional locally.

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | — | **Required** |
| `DEBUG` | `False` | Set to `true` for local dev |
| `DATABASE_URL` | SQLite `db.sqlite3` | Render injects PostgreSQL URL |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | |
| `CSRF_TRUSTED_ORIGINS` | — | Needed for HTTPS deployments |
| `DJANGO_SUPERUSER_PASSWORD` | — | Triggers superuser creation in `build.sh` |

## Architecture

**Stack:** Django 5 / Python 3.12, server-rendered templates, Bootstrap 5.3 (CDN), no JS framework. Deployed on Render with PostgreSQL + WhiteNoise for static files.

**Template layout:** All authenticated pages extend `templates/base.html`, which renders the sidebar, flash messages, and the `{% block content %}` area. Unauthenticated pages (login, register) use `{% block auth_content %}` — a plain centered container with no sidebar. The public landing page (`templates/core/landing.html`) is a fully standalone HTML document that does not extend `base.html`.

**URL layout:**
- `/` → dashboard (login required)
- `/about/` → public landing page
- `/login/`, `/register/`, `/logout/` → auth
- `/companies/`, `/companies/<id>/`, `/companies/<id>/contact/`, `/companies/<id>/visit/` → volunteer workflows
- `/badges/`, `/leaderboard/`, `/messages/` → engagement features
- `/admin-actions/*` → staff-only quick actions (add company, assign, invite, create-admin)
- `/admin/` → Django admin

**Access control:** `@login_required` on all volunteer views. `@staff_member_required` on all `/admin-actions/` views. Private messages are filtered in the view: `is_private=True` messages are visible only to the sender and staff.

## Core Data Model

The central entity is **Assignment** — it links a **Company** to a volunteer (**User**). Most other models hang off Assignment:

- **ContactAttempt** → Assignment: phone/email/in-person outreach attempts
- **VisitNote** → Assignment: records a completed visit

**Status lifecycles are driven by model `save()` hooks, not views:**

- `ContactAttempt.save()` — after 3 attempts on an active assignment, auto-sets `assignment.status = LOST` and `company.status = LOST`, then calls `check_and_award_badges(user)`.
- `VisitNote.save()` — auto-sets `assignment.status = COMPLETED`, `company.status = VISITED`, `assignment.completed_date = now()`, then calls `check_and_award_badges(user)`.

Company status flow: `unassigned → assigned → visited / lost`
Assignment status flow: `active → completed / lost`

**Badge awarding** (`core/badges.py` → `check_and_award_badges(user)`): called from the two save hooks above. Compares the user's current stats (visits completed, contact attempts, assignments received) against all non-manual Badge thresholds. Creates a `UserBadge` record and posts a public `Message` announcement for each newly earned badge. `criteria_value = 0` means manual-award only.

**Registration** is invite-code gated. `RegisterForm.clean_invite_code()` validates the code and stores the `InviteCode` object as `self._invite`; `RegisterForm.save()` marks it consumed by setting `used_by` and `used_at`.

**Messaging:** `Message.is_private=False` is a group discussion board; `is_private=True` is a direct message to admins. The `message_list` view filters private messages to sender + staff only.

## Rate Limiting

`core/ratelimit.py` provides a `@ratelimit(max_attempts, window, key_prefix)` decorator that tracks POST requests per client IP via Django's cache. Returns HTTP 403 on breach. Applied to: login (5/5min), register (5/5min), message_create (10/5min).

## Deployment

Render runs `./build.sh` on deploy (install → collectstatic → migrate → create superuser). Static files are served by WhiteNoise. `DEBUG=False` enables HSTS, SSL redirect, and secure cookies automatically via `settings.py`.

# MoodApp – Team Mood (Django 5)

<p align="right">
  <a href="./docs/en/README.en.md">English</a> ·
  <a href="./docs/de/README.de.md">Deutsch</a> ·
</p>

A small, pragmatic app where team members record their **mood** daily (or weekly).
The team view shows **aggregate values only** (average/median/distribution), no user list.

[![Screenshot: MoodApp – Teamview](./docs/assets/screenshot_team_view.png)](./assets/screenshot.png)

## TL;DR

```bash
# 1) Local (without Docker)
python -m venv .venv && . .venv/bin/activate    # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env   # edit file (see below)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Optional: demo data
python manage.py seed_moods --users 10 --days 60 --bias neutral

# 2) Docker Desktop (local)
docker compose up --build -d
```

---

## Features

- 9-step scale: −4 … 0 … +4 with playful labels
- **Today** (set your mood), **My History** (bar chart + table), **Team** (aggregates: time range / week)
- Past entries are **read-only**
- **i18n**: German, Swiss German, English, French, Spanish, Polish
- **Light/Dark Mode** (system default, UI toggle)
- **WhiteNoise**: serve static files directly from Django (simple deployments)
- Seed/Reset commands for demo/tests

---

## Project Structure (excerpt)

```
app/                     # Django project
moods/                   # App
  ├─ templates/moods/    # base, today, history, team_*.html
  ├─ static/moods/css/   # theme.css (Light/Dark, colors, tabs, charts)
  ├─ management/commands/
  │   ├─ seed_moods.py   # seed & reset (see below)
  │   └─ clear_demo_moods.py (optional)
  ├─ models.py           # MoodEntry (+ IntegerChoices)
  ├─ forms.py
  ├─ views.py
Dockerfile
docker-compose.yml
entrypoint.sh
requirements.txt
locale/                  # translations (de, gsw, en, fr, es, pl, ...)
.env.example
.env.docker
```

---

## 1) Local development (without Docker)

### Prerequisites
- Python **3.12/3.13**
- `pip`, `venv`
- For translations: **gettext** (Linux/Mac standard; Windows via WSL/Chocolatey)

### Setup
```bash
python -m venv .venv
# Linux/Mac
. .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### `.env.example` (sample)
```ini
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=dev-insecure-change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_TIME_ZONE=Europe/Zurich
DJANGO_USE_TZ=1

# WhiteNoise (auto: in DEV off, in PROD on – override here if needed)
DJANGO_USE_WHITENOISE=

# Security (leave empty in DEV; see PROD below)
DJANGO_SECURE_SSL_REDIRECT=
DJANGO_SESSION_COOKIE_SECURE=
DJANGO_CSRF_COOKIE_SECURE=
DJANGO_CSRF_TRUSTED_ORIGINS=

# DB (empty => SQLite). For Postgres e.g.:
# DATABASE_URL=postgresql+psycopg://mood:moodpass@localhost:5432/moodapp

# Default UI language
LANGUAGE_CODE=en
```

### Demo data (Seed/Reset)
```bash
# 60 days, 12 users, neutral distribution (weekdays only)
python manage.py seed_moods --users 12 --days 60

# strong negative bias, incl. weekends
python manage.py seed_moods --users 10 --days 30 --bias neg --include-weekends

# Reset (entries only), keep demo users
python manage.py seed_moods --reset --reset-only

# Reset + delete demo users
python manage.py seed_moods --reset --delete-users --reset-only

# Reset & immediately reseed
python manage.py seed_moods --reset --delete-users --users 10 --days 90 --bias pos
```

### Internationalization (i18n)

We use `LocaleMiddleware`, the `i18n` context processor and `LOCALE_PATHS`.
Languages: `de`, `gsw`, `en`, `fr`, `es`, `pl`

```bash
# extract strings
django-admin makemessages -l de -l gsw -l en -l fr -l es -l pl
# translate in locale/<lang>/LC_MESSAGES/django.po
# then compile:
django-admin compilemessages
```

> **Windows:** install `gettext` + `msgfmt` via WSL/Git-Bash/Chocolatey.  
> Templates include `set_language` (flag dropdown).

---

## 2) Docker & Compose (local)

### .env for Docker
See `./.env.docker` (example):
```ini
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_TIME_ZONE=Europe/Zurich
DJANGO_USE_TZ=1
DJANGO_USE_WHITENOISE=1
DJANGO_SECURE_SSL_REDIRECT=0
DJANGO_SESSION_COOKIE_SECURE=0
DJANGO_CSRF_COOKIE_SECURE=0
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000
DATABASE_URL=postgresql+psycopg://mood:moodpass@db:5432/moodapp
LANGUAGE_CODE=en
POSTGRES_DB=moodapp
POSTGRES_USER=mood
POSTGRES_PASSWORD=moodpass
```

> **Note:** The Docker image runs `collectstatic` **at build time** (WhiteNoise manifest).  
> The `entrypoint.sh` runs **migrations** on start; `collectstatic` can be toggled with `RUN_COLLECTSTATIC=1` if you enable that logic.

### Start
```bash
# first time (or after code changes affecting the image)
docker compose --env-file .env.docker up --build -d

# view logs
docker compose logs -f web

# stop
docker compose down
```

App will be available at http://localhost:8000

---

## 3) Portainer (options)

Depending on your setup there are three paths:

### A) **Repository stack** (recommended if Git is available)
- Portainer → *Stacks → Add from repository*
- Repository URL + branch
- Compose path: `docker-compose.yml`
- Deploy (Portainer builds the image on the target endpoint).

### B) **Import a local image** (no registry)
- Build locally:
  ```bash
  docker build -t moodapp:1.0.0 .
  docker save -o moodapp_1.0.0.tar moodapp:1.0.0
  ```
- Portainer → *Images → Import* → upload `moodapp_1.0.0.tar`.
- Stack (web editor) using:
  ```yaml
  services:
    web:
      image: moodapp:1.0.0
      # optionally: pull_policy: if_not_present
  ```
- Deploy (Portainer uses the **local** image of the endpoint).

### C) **Web editor with build** (only if Portainer has access to Dockerfile/context)
- Works when files are pulled from a **Git repo** (see A).  
  With raw copy & paste there’s no build context → “open Dockerfile…” error.

> Important: The **endpoint** in Portainer must see the image/repo.  
> Different hosts → different local image stores.

---

## 4) Production (quick notes)

- `DJANGO_DEBUG=0`
- set **SECRET_KEY**
- set `DJANGO_ALLOWED_HOSTS` correctly
- use **TLS/reverse proxy** in front (Nginx/Caddy) or platform TLS
- for external domains: configure `DJANGO_CSRF_TRUSTED_ORIGINS`
- WhiteNoise enabled; `collectstatic` done at build time

---

## 5) Admin & Anonymity

- `/admin` is enabled (user management). Create a superuser:
  ```bash
  python manage.py createsuperuser
  ```
- `MoodEntry` is **not** registered in admin → no per-user mood inspection via backend.
- Note: a superuser **can** read the database. True “zero-knowledge” would require client-side crypto — **out of scope** for this app.

---

## 6) Handy management commands (cheatsheet)

```bash
# migrations
python manage.py makemigrations
python manage.py migrate

# superuser
python manage.py createsuperuser

# static files (usually not needed in dev)
python manage.py collectstatic

# seed/reset (see above)
python manage.py seed_moods --users 12 --days 60
python manage.py seed_moods --reset --delete-users --reset-only

# i18n
django-admin makemessages -l de -l gsw -l en -l fr -l es -l pl
django-admin compilemessages
```

---

## 7) Troubleshooting

- **Login/Logout 405**  
  Ensure your `app/urls.py` includes:
  ```python
  from django.contrib import admin
  from django.urls import path, include

  urlpatterns = [
      path("admin/", admin.site.urls),
      path("", include("moods.urls", namespace="moods")),
      path("accounts/", include("django.contrib.auth.urls")),  # login/logout/password
      path("i18n/", include("django.conf.urls.i18n")),         # set_language
  ]
  ```

- **Language doesn’t change**  
  `LocaleMiddleware` must be **after** `SessionMiddleware` and **before** `CommonMiddleware`.  
  Also enable `django.template.context_processors.i18n`.

- **Static files missing in Docker**  
  Check that the build step `collectstatic` succeeded and `USE_WHITENOISE=1` is active.

- **Portainer can’t find the image**  
  Import the image on the **correct endpoint** or use a repo stack (see above).

- **Architecture mismatch (arm64/amd64)**  
  Cross-build:
  ```bash
  docker buildx build --platform linux/amd64 -t moodapp:1.0.0 .
  ```

---

## License

MIT (unless otherwise agreed).

Have fun — **geilomatico 🚀**!

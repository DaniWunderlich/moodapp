# MoodApp – Team-Stimmung (Django 5)

<p align="right">
  <a href="./docs/en/README.en.md">English</a> ·
  <a href="./docs/de/README.de.md">Deutsch</a> ·
</p>

Eine kleine, pragmatische App, in der Teammitglieder täglich (oder wöchentlich) ihren **Mood** eintragen.
Die Teamansicht zeigt **ausschliesslich Aggregatwerte** (Durchschnitt/Median/Verteilung), keine Nutzerliste.

[![Screenshot: MoodApp – Teamview](./docs/assets/screenshot_team_view.png)](./assets/screenshot.png)

## TL;DR

```bash
# 1) Lokal (ohne Docker)
python -m venv .venv && . .venv/bin/activate    # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env   # Datei anpassen (unten)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Optional: Demodaten
python manage.py seed_moods --users 10 --days 60 --bias neutral

# 2) Docker Desktop (lokal)
docker compose up --build -d
```

---

## Features

- 9-stufige Skala: −4 … 0 … +4 mit humorvollen Labels
- **Heute** (Mood setzen), **Mein Verlauf** (Balken-Chart + Tabelle), **Team** (Aggregat: Zeitraum/Week)
- Einträge der Vergangenheit sind **read-only**
- **i18n**: Deutsch, Schwiizerdütsch, Englisch, Französisch, Spanisch, Polnisch
- **Light/Dark Mode** (System-Default, Toggle in der UI)
- **WhiteNoise**: statische Dateien direkt aus Django (für einfache Deployments)
- Seed/Reset-Commands für Demo/Tests

---

## Projektstruktur (Auszug)

```
app/                     # Django Project
moods/                   # App
  ├─ templates/moods/    # base, today, history, team_*.html
  ├─ static/moods/css/   # theme.css (Light/Dark, Farben, Tabs, Charts)
  ├─ management/commands/
  │   ├─ seed_moods.py   # Seed & Reset (siehe unten)
  │   └─ clear_demo_moods.py (optional)
  ├─ models.py           # MoodEntry (+ IntegerChoices)
  ├─ forms.py
  ├─ views.py
Dockerfile
docker-compose.yml
entrypoint.sh
requirements.txt
locale/                  # Übersetzungen (de, gsw, en, fr, es, pl, ...)
.env.example
.env.docker
```

---

## 1) Lokale Entwicklung (ohne Docker)

### Voraussetzungen
- Python **3.12/3.13**
- `pip`, `venv`
- Für Übersetzungen: **gettext** (Linux/Mac vorhanden; Windows via WSL/Chocolatey)

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

### `.env.example` (Beispiel)
```ini
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=dev-insecure-change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_TIME_ZONE=Europe/Zurich
DJANGO_USE_TZ=1

# WhiteNoise (auto: in DEV aus, in PROD an – hier überschreibbar)
DJANGO_USE_WHITENOISE=

# Security (in DEV leer lassen; PROD siehe unten)
DJANGO_SECURE_SSL_REDIRECT=
DJANGO_SESSION_COOKIE_SECURE=
DJANGO_CSRF_COOKIE_SECURE=
DJANGO_CSRF_TRUSTED_ORIGINS=

# DB (leer => SQLite). Für Postgres z.B.:
# DATABASE_URL=postgresql+psycopg://mood:moodpass@localhost:5432/moodapp

# Sprache (Default UI)
LANGUAGE_CODE=de
```

### Demodaten (Seed/Reset)
```bash
# 60 Tage, 12 User, neutrale Verteilung (nur Werktage)
python manage.py seed_moods --users 12 --days 60

# starke Negativtendenz, inkl. Wochenenden
python manage.py seed_moods --users 10 --days 30 --bias neg --include-weekends

# Reset (nur Einträge), Demo-User behalten
python manage.py seed_moods --reset --reset-only

# Reset + Demo-User löschen
python manage.py seed_moods --reset --delete-users --reset-only

# Reset & direkt neu seeden
python manage.py seed_moods --reset --delete-users --users 10 --days 90 --bias pos
```

### Internationalisierung (i18n)

Wir nutzen `LocaleMiddleware`, `i18n`-Context-Processor und `LOCALE_PATHS`.

Sprachen: `de`, `gsw`, `en`, `fr`, `es`, `pl`

```bash
# Strings extrahieren
django-admin makemessages -l de -l gsw -l en -l fr -l es -l pl
# Übersetzen in locale/<lang>/LC_MESSAGES/django.po
# dann kompilieren:
django-admin compilemessages
```

> **Windows:** `gettext` + `msgfmt` via WSL/Git-Bash/Chocolatey installieren.  
> In den Templates ist `set_language` integriert (Flaggen-Dropdown).

---

## 2) Docker & Compose (lokal)

### .env für Docker
Siehe `./.env.docker` (Beispiel):
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
LANGUAGE_CODE=de
POSTGRES_DB=moodapp
POSTGRES_USER=mood
POSTGRES_PASSWORD=moodpass
```

> **Hinweis:** Im Docker-Image wird `collectstatic` **beim Build** ausgeführt (WhiteNoise Manifest).  
> Im `entrypoint.sh` laufen **Migrationen** automatisch; `collectstatic` ist optional über `RUN_COLLECTSTATIC=1` aktivierbar (Standard: aus).

### Starten
```bash
# Erstes Mal (oder bei Codeänderungen am Image)
docker compose --env-file .env.docker up --build -d

# Logs ansehen
docker compose logs -f web

# Stoppen
docker compose down
```

Die App läuft auf http://localhost:8000

---

## 3) Portainer (Optionen)

Je nach Setup gibt’s drei Wege:

### A) **Repository-Stack** (empfohlen, wenn Git verfügbar)
- Portainer → *Stacks → Add from repository*
- Repository-URL + Branch
- Compose path: `docker-compose.yml`
- Deploy (Portainer baut das Image auf dem Ziel-Endpoint).

### B) **Lokales Image importieren** (ohne Registry)
- Lokal bauen:
  ```bash
  docker build -t moodapp:1.0.0 .
  docker save -o moodapp_1.0.0.tar moodapp:1.0.0
  ```
- Portainer → *Images → Import* → `moodapp_1.0.0.tar` hochladen.
- Stack im Web-Editor mit:
  ```yaml
  services:
    web:
      image: moodapp:1.0.0
      # ggf.: pull_policy: if_not_present
  ```
- Deploy (Portainer nutzt das **lokale** Image des Endpoints).

### C) **Web-Editor mit Build** (nur wenn Portainer Zugriff auf Dockerfile/Context hat)
- Funktioniert, wenn die Dateien aus einem **Git-Repo** gezogen werden (siehe A).  
  Mit reinem Copy&Paste ist kein Build-Kontext vorhanden → „open Dockerfile…“ Fehler.

> Wichtig: Der **Endpoint** in Portainer muss das Image/Repo sehen.  
> Unterschiedliche Hosts → unterschiedlicher Image-Lokalspeicher.

---

## 4) Produktion (Kurznotizen)

- `DJANGO_DEBUG=0`
- **SECRET_KEY** setzen
- `DJANGO_ALLOWED_HOSTS` korrekt setzen
- **TLS/Proxy** davor (Nginx/Caddy) oder Plattform-TLS verwenden
- Bei externen Domains: `DJANGO_CSRF_TRUSTED_ORIGINS` pflegen
- WhiteNoise ist aktiv; `collectstatic` beim Build erledigt

---

## 5) Admin & Anonymität

- `/admin` ist aktiv (Userverwaltung). Lege einen Superuser an:
  ```bash
  python manage.py createsuperuser
  ```
- `MoodEntry` ist **nicht** im Admin registriert → keine Einzeldateneinsicht über das Backend.
- Hinweis: Ein Superuser **kann** grundsätzlich die DB lesen. Für absolute „Zero-Knowledge“ wären clientseitige Keys nötig – **nicht** Ziel dieser App.

---

## 6) Nützliche Management-Befehle (Cheatsheet)

```bash
# Migrationen
python manage.py makemigrations
python manage.py migrate

# Superuser
python manage.py createsuperuser

# Statische Dateien (DEV i.d.R. nicht nötig)
python manage.py collectstatic

# Seed/Reset (siehe oben)
python manage.py seed_moods --users 12 --days 60
python manage.py seed_moods --reset --delete-users --reset-only

# i18n
django-admin makemessages -l de -l gsw -l en -l fr -l es -l pl
django-admin compilemessages
```

---

## 7) Troubleshooting

- **Login/Logout 405**  
  Stelle sicher, dass in `app/urls.py` enthalten ist:
  ```python
  from django.contrib import admin
  from django.urls import path, include

  urlpatterns = [
      path("admin/", admin.site.urls),
      path("", include("moods.urls", namespace="moods")),
      path("accounts/", include("django.contrib.auth.urls")),  # Login/Logout/Password
      path("i18n/", include("django.conf.urls.i18n")),         # set_language
  ]
  ```

- **Sprache wechselt nicht**  
  `LocaleMiddleware` muss **nach** `SessionMiddleware` und **vor** `CommonMiddleware` stehen.  
  Außerdem `django.template.context_processors.i18n` aktivieren.

- **Statische Dateien fehlen in Docker**  
  Prüfe, dass der Build-Schritt `collectstatic` erfolgreich war und `USE_WHITENOISE=1` aktiv ist.

- **Portainer findet Image nicht**  
  Image am **richtigen Endpoint** importieren oder Repo-Stack nutzen (siehe oben).

- **Architektur-Mismatch (arm64/amd64)**  
  Cross-Build:
  ```bash
  docker buildx build --platform linux/amd64 -t moodapp:1.0.0 .
  ```

---

## Lizenz

MIT (falls nichts anderes vereinbart).

Viel Spass – **geilomatico 🚀**!

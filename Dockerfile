# Use the same Python version as locally
FROM python:3.13-slim

# Saner defaults for Python & pip inside containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on \
    PYTHONPATH=/app

# System packages:
# - tzdata: proper time zone handling
# - gettext: provides `msgfmt` used by `compilemessages`
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tzdata gettext \
 && rm -rf /var/lib/apt/lists/*

# App directory and non-root user
WORKDIR /app
RUN useradd -m -u 10001 appuser

# Install Python dependencies first for better layer caching
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the application code
COPY . /app

# Normalize line endings for the entrypoint on Windows checkouts and make it executable
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Build-time Django settings to compile assets/translations deterministically
# DEBUG must be off so WhiteNoise's Manifest storage is active for `collectstatic`
ENV DJANGO_DEBUG=0 \
    DJANGO_USE_WHITENOISE=1

# Compile translations (.po -> .mo). No DB needed, just gettext + settings.
RUN python manage.py compilemessages

# Collect static files (served by WhiteNoise in the container)
# Done in entrypoint.sh to ensure it's always up to date with the latest code.
# RUN python manage.py collectstatic --noinput

# Switch to non-root for runtime
RUN chown -R appuser:appuser /app
USER appuser

# Expose application port
EXPOSE 8000

# Default entrypoint:
# - waits for DB, runs migrations (and optionally collectstatic if you kept it there)
ENTRYPOINT ["./entrypoint.sh"]

# Gunicorn as the WSGI server
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]

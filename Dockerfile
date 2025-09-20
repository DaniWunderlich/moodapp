# Python wie lokal (du nutzt 3.13.x)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    PYTHONPATH=/app

# Systempakete für Builds / Laufzeit (schlank halten)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# App-Verzeichnisse
WORKDIR /app
RUN useradd -m -u 10001 appuser
COPY requirements.txt /app/

# Abhängigkeiten
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# App-Code
COPY . /app
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Für collectstatic sollte WhiteNoise aktiv sein und DEBUG=0 gelten
ENV DJANGO_DEBUG=0 DJANGO_USE_WHITENOISE=1
RUN python manage.py collectstatic --noinput

# Non-root
RUN chown -R appuser:appuser /app
USER appuser

# Port & Default-Start; Migration/Collectstatic macht unser entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]

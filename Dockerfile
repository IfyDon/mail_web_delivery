# ── Stage 1: build ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libjpeg-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements/prod.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .

# GeoIP2 database — downloaded at build time from MaxMind.
# Requires MAXMIND_LICENSE_KEY build arg (get a free key at maxmind.com/en/geolite2/signup).
# If not provided, geo tracking silently returns {} — non-fatal.
ARG MAXMIND_LICENSE_KEY=""
RUN mkdir -p /app/geoip && \
    if [ -n "$MAXMIND_LICENSE_KEY" ]; then \
      curl -fsSL "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz" \
        | tar -xz -C /app/geoip --strip-components=1 --wildcards "*/GeoLite2-City.mmdb" && \
      echo "GeoLite2-City.mmdb downloaded."; \
    else \
      echo "MAXMIND_LICENSE_KEY not set — geo tracking will return empty results."; \
    fi

# collectstatic runs at build time — use base settings (SQLite, no external deps)
# so the build succeeds without runtime secrets being available.
RUN DJANGO_SETTINGS_MODULE=config.settings.base \
    SECRET_KEY=build-time-placeholder-not-used-at-runtime \
    python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-4} --timeout ${GUNICORN_TIMEOUT:-120} --log-file -"]

# ── Stage 1: CSS build ───────────────────────────────────────────────
# static/css/output.css is Tailwind's compiled output, checked into git so
# `collectstatic` (below) has something to hash even without this stage.
# Compiling it fresh here means a template class that isn't in the last
# committed output.css still ships correctly — nobody has to remember to
# run the Tailwind CLI locally before every deploy.
FROM node:20-slim AS css-builder
WORKDIR /app
COPY tailwind.config.js ./
COPY static/css/input.css static/css/
COPY templates/ templates/
COPY static/js/ static/js/
RUN npx --yes tailwindcss@^3 -i static/css/input.css -o static/css/output.css --minify

# ── Stage 2: build ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libjpeg-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements/prod.txt

# ── Stage 3: runtime ──────────────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
COPY --from=css-builder /app/static/css/output.css static/css/output.css

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

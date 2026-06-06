# web_mail

A Postmark-like transactional email service built with Django + DRF + Celery + React.

## Quick Start (Development)

```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. Copy env template and fill in secrets
cp .env.example .env

# 3. Apply migrations
python manage.py migrate

# 4. Create a superuser
python manage.py createsuperuser

# 5. Start Django
python manage.py runserver

# 6. Start Celery worker (separate terminal)
celery -A config.celery worker --loglevel=info

# 7. Start Celery Beat scheduler (separate terminal)
celery -A config.celery beat --loglevel=info

# 8. Start React frontend (separate terminal)
cd frontend && npm install && npm start
```

## Docker (when ready)

```bash
cp .env.example .env   # fill in real secrets first
docker-compose up --build
```

## Project Layout

See the WorkFlow document for a full phase-by-phase breakdown of what to build and in what order.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2, DRF, Celery, Redis, PostgreSQL |
| Auth | django-allauth, django-otp (2FA), API keys |
| Email relay | AWS SES (boto3) / django-anymail |
| Frontend | React, Tailwind CSS, Axios, Recharts |
| Monitoring | Sentry, Celery Flower, Prometheus |
| Deployment | Docker, Nginx, Gunicorn |

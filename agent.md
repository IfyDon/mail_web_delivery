markdown
# Agent.md – Web Mail (Email Delivery Service)

## Project Overview

**Web Mail** is a production‑ready email delivery service similar to Postmark, SendGrid, or Resend. It allows users to send transactional and promotional emails via a REST API or SMTP, manage sending domains, create email templates, track opens/clicks, and receive delivery events via webhooks.

The system consists of:
- **Django backend** (REST API + web dashboard + marketing site)
- **React frontend** (user dashboard – optional but included)
- **Celery** for asynchronous email sending and webhook dispatch
- **Redis** as message broker and cache
- **PostgreSQL** (production) / SQLite (development)
- **Docker** for containerisation

---

## Tech Stack

| Layer               | Technology                                                                 |
|---------------------|----------------------------------------------------------------------------|
| Backend framework   | Django 4.2+, Django REST Framework (DRF)                                   |
| Async tasks         | Celery + Redis                                                             |
| Database            | PostgreSQL (prod), SQLite (dev)                                            |
| Cache & broker      | Redis                                                                      |
| Email relay         | AWS SES (via boto3), can be swapped for SMTP or Mailgun/SendGrid           |
| Frontend            | React 18 + Tailwind CSS + Axios + React Router                             |
| Task scheduling     | Celery Beat (periodic tasks)                                               |
| API documentation   | drf-spectacular (OpenAPI + Swagger UI)                                     |
| Monitoring          | Sentry (errors), Celery Flower (tasks), Prometheus + Grafana (optional)    |
| Containerisation    | Docker + Docker Compose                                                    |
| Testing             | pytest, pytest-django, Selenium/Playwright (e2e)                           |
| Code quality        | Black, isort, flake8, pre-commit hooks                                     |

---

## Folder Structure (Top Level)
web_mail/
├── .env.example # Environment variables template
├── docker-compose.yml # Multi-container: web, worker, redis, db
├── Dockerfile # Django + Gunicorn image
├── Dockerfile.frontend # React build image (optional)
├── manage.py
├── requirements/ # Python dependencies (base, dev, prod)
├── config/ # Django project settings (base.py, dev.py, prod.py)
├── core/ # Shared utilities (middleware, permissions, helpers)
├── apps/ # All Django apps (authentication, accounts, domains, ...)
├── api/ # Versioned REST API (v1)
├── web/ # Marketing site + dashboard views (non‑API)
├── templates/ # Django HTML templates (marketing, legal, base)
├── static/ # Compiled static assets (CSS, JS, images)
├── services/ # Business logic layer (email sending, tracking, webhooks)
├── workers/ # Celery tasks (send_email, webhook_dispatch, ...)
├── integrations/ # External service adapters (SES, SMTP, S3)
├── tracking/ # Open/click tracking endpoints (lightweight)
├── tests/ # Unit, integration, and e2e tests
└── frontend/ # React dashboard application

text

> See the full detailed tree in the project’s documentation.

---

## Key Components & Responsibilities

| Component                | Responsibility                                                                 |
|--------------------------|--------------------------------------------------------------------------------|
| `config/`                | Django settings split by environment; Celery initialisation.                   |
| `core/`                  | Low‑level utilities (DNS verification, rate limiting, API key middleware).    |
| `apps/authentication/`   | User registration, login, email verification, 2FA.                             |
| `apps/accounts/`         | API key management (hashed), quota tracking.                                   |
| `apps/domains/`          | Sending domains – add, verify (DKIM/SPF/DMARC).                                |
| `apps/email_messages/`   | Stores every sent message (status, attempts, etc.).                            |
| `apps/events/`           | Tracks opens, clicks, bounces, complaints.                                     |
| `apps/webhooks/`         | User‑configured webhooks + dispatch log.                                       |
| `apps/suppressions/`     | Bounce/complaint/unsubscribe suppression lists.                                |
| `services/`              | Business logic (e.g., `email_service.send()` calls Celery).                    |
| `workers/tasks/`         | Async tasks – sending email via relay, dispatching webhooks.                   |
| `tracking/`              | Lightweight pixel and redirect endpoints (no DRF overhead).                    |
| `api/v1/`                | DRF views – `/send`, `/messages`, `/domains`, `/stats`, etc.                   |
| `web/`                   | Marketing landing page, legal pages, and dashboard views (if not using React). |
| `frontend/`              | React single‑page application for the user dashboard.                          |

---

## Development Setup (Local)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis (or use Docker)
- (Optional) PostgreSQL – otherwise SQLite works

### Backend Setup

```bash
# Clone and enter project
cd web_mail

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements/dev.txt

# Copy environment variables
cp .env.example .env
# Edit .env – at minimum set DJANGO_SECRET_KEY, DEBUG=True

# Run migrations (SQLite by default in dev)
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
Frontend Setup (React Dashboard)
bash
cd frontend
npm install
npm start   # runs on http://localhost:3000
Celery Worker (separate terminal)
bash
# Requires Redis running (docker run -p 6379:6379 redis)
celery -A config worker --loglevel=info
Using Docker Compose (all services together)
bash
docker-compose up --build
Coding Conventions
Python (Django)
Follow PEP 8.

Use Black for formatting (black .).

Use isort for import sorting (isort .).

Use flake8 for linting.

Type hints are encouraged for all functions/methods.

Docstrings for public classes and methods (Google style preferred).

JavaScript / React
Use ESLint (Airbnb style) + Prettier.

Functional components with hooks (no class components).

Use Tailwind CSS for styling – avoid custom CSS files.

Naming Conventions
Django models: singular, PascalCase (e.g., Domain, ApiKey).

Django apps: plural, snake_case (e.g., email_messages, suppressions).

DRF serializers: XyzSerializer.

Celery tasks: verb + noun (e.g., send_email_task, dispatch_webhook_task).

React components: PascalCase (e.g., DomainList, TemplateEditor).

Environment Variables (.env)
Variable	Description	Example
DJANGO_SECRET_KEY	Django secret key (long random string)	django-insecure-...
DEBUG	Set to True for development	True
DATABASE_URL	PostgreSQL connection string (prod)	postgres://user:pass@db:5432/..
REDIS_URL	Redis connection (Celery broker)	redis://redis:6379/0
AWS_ACCESS_KEY_ID	AWS SES credentials (optional)	AKIA...
AWS_SECRET_ACCESS_KEY	...	
SENTRY_DSN	Sentry error tracking DSN (optional)	https://...@sentry.io/...
See .env.example for full list.

Testing
bash
# Run all tests
pytest

# Run specific app tests
pytest apps/domains/tests/

# With coverage
pytest --cov=. --cov-report=html

# End‑to‑end tests (requires Selenium/Playwright)
pytest tests/e2e/
Write tests for:

Models (custom methods, constraints)

Services (email sending logic, webhook payload)

API endpoints (authentication, rate limits, CRUD)

Celery tasks (mocked relay client)

Common Workflows for AI Agents
Adding a new API endpoint
Create or update a DRF view in api/v1/views/.

Add a serializer in the corresponding app’s serializers.py.

Register the route in api/v1/urls.py.

Add business logic to a service in services/ (if needed).

Write tests in tests/integration/test_api.py.

Adding a new Celery task
Create task function in workers/tasks/ (e.g., my_task.py).

Decorate with @shared_task and define retry/backoff.

Call the task from a view or service using .delay().

Test with pytest using celery_worker fixture.

Modifying a Django model
Edit models.py in the relevant app.

Run python manage.py makemigrations (and commit the migration).

Update serializers, views, and services accordingly.

Update tests.

Debugging Celery tasks locally
Ensure Redis is running.

Start worker with celery -A config worker --loglevel=info.

Use celery flower to monitor tasks (optional).

Building the React dashboard
The React app expects the Django API at /api/v1/ (proxy in dev).

In development, run npm start and ensure API requests go to http://localhost:8000/api/v1/ (configure proxy in frontend/package.json).

For production, build static files (npm run build) and serve them via Django’s WhiteNoise or Nginx.

Deployment
Containerised: Use docker-compose.prod.yml with PostgreSQL, Redis, and multiple workers.

Cloud: Deploy to AWS ECS, Google Cloud Run, or a VPS with Docker.

Environment: Set DEBUG=False, configure ALLOWED_HOSTS, enable HTTPS, set up database backups.

See deployment/ folder (to be created) for Terraform/Ansible scripts.

Useful Django Management Commands (custom)
Command	Purpose
python manage.py verify_all_domains	Re‑verify domain DNS records
python manage.py clean_old_logs --days 30	Delete old message/event records
python manage.py retry_failed_webhooks	Re‑send failed webhook events
Code Example – Sending an Email (Service Layer)
python
# services/email_service.py
from apps.email_messages.models import Message
from workers.tasks.send_email import send_email_task

def send_email(user, from_email, to_email, subject, html_body, text_body=None):
    message = Message.objects.create(
        user=user,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        status='queued'
    )
    send_email_task.delay(message.id)
    return message.id
Support & Questions
Project documentation: docs/ folder (to be created).

CI/CD: GitHub Actions (.github/workflows/ci.yml).

Agent instructions: When asked to implement a feature, always consider:

Does it belong in an existing app or a new app?

Are there async requirements? → Use Celery.

Is it exposed via API? → Add DRF endpoint + docs.

Is it user‑facing in the dashboard? → Add React component.

Last updated: 2026-05-28
Maintainer: Development Team

text

**Instructions:**  
Create a new file named `agent.md` in the root directory of your `web_mail/` project and paste the content above. This file will guide any AI coding agent (or new team member) through the project’s structure, conventions, and workflows.
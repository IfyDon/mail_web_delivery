# web_mail

A Postmark-like transactional email service built with Django + DRF + Celery + React.

## Prerequisites

- Python 3.12
- Node.js 18+ and npm
- PostgreSQL 16 and Redis 7 (or use Docker compose)
- Git
- Optional: Docker and Docker Compose for containerized local testing

## Local Development Setup

1. Clone the repository and enter the project directory:

```bash
git clone https://github.com/IfyDon/mail_web_delivery.git
cd mail_web_delivery
```

2. Create and activate a Python virtual environment:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

3. Install backend dependencies:

```bash
pip install --upgrade pip
pip install -r requirements/dev.txt
```

4. Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

5. Copy the environment template and configure local values:

```bash
cp .env.example .env
```

Then update `.env` as needed for local development. The default `.env.example` already points to `localhost` for the database and Redis.

6. Start local PostgreSQL and Redis, if not using Docker.

7. Run Django migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

## Running the Project for Browser Testing

### Start the backend

```bash
python manage.py runserver 0.0.0.0:8000
```

This starts the Django API and admin server at:

- API: `http://localhost:8000/api/v1`
- Admin: `http://localhost:8000/admin/`

### Start Celery worker and scheduler

Open separate terminal windows and run:

```bash
celery -A config.celery worker --loglevel=info
celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Start the frontend

```bash
cd frontend
npm start
```

Then open the browser at:

- Frontend: `http://localhost:3000`

The React dev server will proxy API requests to the backend when configured, so you can test the application in a browser before deployment.

## Browser Testing Checklist

- Verify the frontend loads at `http://localhost:3000`
- Ensure the backend API responds at `http://localhost:8000/api/v1`
- Confirm admin access at `http://localhost:8000/admin/`
- Validate email, domain, and template flows through the UI
- Check Celery tasks are processed by submitting jobs that require background execution

## Docker Compose (Local Test Environment)

For a containerized local test environment, use Docker Compose.

1. Copy the env template:

```bash
cp .env.example .env
```

2. Build and start services:

```bash
docker compose up --build
```

3. Open the application in a browser:

- Backend / API: `http://localhost:8000`
- Flower monitoring: `http://localhost:5555`

> Note: The provided Docker Compose configuration starts the Django backend, Postgres, Redis, Celery worker, Celery beat, Flower, and Nginx. The React frontend is typically run separately using `npm start` during development.

## Production Considerations

Before deploying to production:

- Set `DEBUG=False` in `.env`
- Use a secure `SECRET_KEY`
- Configure `ALLOWED_HOSTS` for your domain
- Use real AWS SES / SendGrid credentials or another email relay provider
- Set `STRIPE_*` credentials for billing integration
- Ensure `CORS_ALLOWED_ORIGINS` includes the deployed frontend URL
- Run `python manage.py collectstatic --noinput`
- Use HTTPS and secure Nginx configuration

## Project Layout

- `api/` — REST API endpoints
- `apps/` — Django applications for account, billing, domains, messages, templates, etc.
- `config/` — Django configuration and settings
- `core/` — shared utilities, middleware, permissions
- `frontend/` — React single-page application
- `requirements/` — Python dependency files
- `templates/`, `static/` — Django template and static assets

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django, Django REST Framework, Celery |
| Database | PostgreSQL |
| Cache / Broker | Redis |
| Frontend | React, Tailwind CSS, Axios |
| Deployment | Docker, Gunicorn, Nginx |
| Email relay | AWS SES / SendGrid |

## API Documentation

The API is fully documented with interactive Swagger UI and ReDoc:

- **Swagger UI** — http://localhost:8000/api/docs/
- **ReDoc** — http://localhost:8000/api/redoc/
- **OpenAPI Schema** — http://localhost:8000/api/schema/

### Main Endpoints

**Authentication**
- `POST /api/v1/auth/login/` — User login
- `POST /api/v1/auth/signup/` — User registration
- `POST /api/v1/auth/verify-email/` — Verify email address

**Messages**
- `GET /api/v1/messages/` — List sent messages (paginated)
- `POST /api/v1/send/` — Send a single email
- `POST /api/v1/send/batch/` — Send batch emails
- `GET /api/v1/messages/{id}/` — Get message details with event timeline

**Domains**
- `GET /api/v1/domains/` — List domains
- `POST /api/v1/domains/` — Create domain
- `POST /api/v1/domains/{id}/verify/` — Verify DNS records

**Templates**
- `GET /api/v1/templates/` — List email templates
- `POST /api/v1/templates/` — Create template
- `PATCH /api/v1/templates/{id}/` — Update template

**Webhooks**
- `GET /api/v1/webhooks/` — List webhooks
- `POST /api/v1/webhooks/` — Create webhook
- `POST /api/v1/webhooks/{id}/test/` — Send test event

**Stats & Analytics**
- `GET /api/v1/stats/` — Get email metrics (filtered by date range)
- `GET /api/v1/suppressions/` — List suppressed email addresses

See [API Documentation](http://localhost:8000/api/docs/) for complete endpoint reference.

## Architecture

### Backend
The Django backend (`config/`, `apps/`, `core/`, `services/`) provides:
- RESTful API with DRF and OpenAPI/Swagger documentation
- User and domain management with DNS verification
- Email template rendering and validation
- Async email delivery via Celery tasks
- Event tracking (open, click, bounce, complaint)
- Webhook dispatch to customer endpoints
- Billing and suppression list management

**Key Apps:**
- `accounts/` — User and API key management
- `authentication/` — Email/password auth, 2FA
- `domains/` — Domain verification and DNS
- `email_messages/` — Message model and status tracking
- `email_templates/` — Template storage and rendering
- `events/` — Event models for tracking
- `suppressions/` — Bounce/complaint/unsubscribe handling
- `webhooks/` — Webhook configuration and dispatch

### Frontend
The React frontend (`frontend/src/`) provides:
- Single-page application with React Router
- Authentication with JWT tokens
- Dashboard with email metrics and charts
- Domain/template/webhook management UI
- Message timeline with event details
- Settings for API keys and 2FA

See [Frontend README](./frontend/README.md) for details.

### Database Schema
- **Users** — Account owners with email and 2FA secrets
- **Domains** — Sending domains with DKIM keys and verification status
- **Templates** — Email templates with versioning
- **Messages** — Sent emails with status tracking
- **Events** — Message events (sent, delivered, opened, clicked, bounced, complained)
- **Webhooks** — Customer endpoints for event delivery
- **Suppressions** — Bounced, complained, or unsubscribed email addresses

## Environment Variables

### Required
```env
SECRET_KEY=your-secret-key-here
DEBUG=False  # Set to True for development
DJANGO_SETTINGS_MODULE=config.settings.dev  # or config.settings.prod
```

### Database
```env
DATABASE_URL=postgres://user:password@localhost:5432/webmail
# Or for SQLite (dev only):
# DATABASE_URL=sqlite:///db.sqlite3
```

### Cache & Broker
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Email Delivery
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend  # dev
# For production:
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
# AWS_SES_REGION_NAME=us-east-1
# AWS_SES_REGION_ENDPOINT=email.us-east-1.amazonaws.com
```

### Billing
```env
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

### CORS & Security
```env
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.yourdomain.com
```

### Monitoring (Optional)
```env
SENTRY_DSN=https://key@sentry.io/project
```

See `.env.example` for all available options.

## Troubleshooting

### "Module not found" or Import errors
```bash
# Backend
pip install -r requirements/dev.txt

# Frontend
cd frontend && npm install
```

### Django migrations not applied
```bash
python manage.py migrate
```

### Celery worker not processing tasks
```bash
# Check broker connection:
celery -A config.celery inspect active

# Check worker status:
celery -A config.celery inspect stats

# Restart worker:
celery -A config.celery worker --loglevel=info
```

### API returns 401 Unauthorized
1. Ensure you're logged in (token in localStorage)
2. Check that `Authorization: Bearer <token>` header is sent
3. Try logging out and back in to refresh token

### Frontend can't connect to backend
1. Verify Django is running: `python manage.py runserver`
2. Check `http://localhost:8000/api/v1` is accessible
3. Verify CORS is configured: `CORS_ALLOWED_ORIGINS` in `.env`
4. Check browser console for CORS errors

### Port already in use
```bash
# Find and kill process on port 8000:
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

## Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and test**
   ```bash
   python manage.py runserver      # Backend
   cd frontend && npm start        # Frontend
   pytest                          # Run tests
   ```

3. **Commit with clear message**
   ```bash
   git add .
   git commit -m "feat: add feature X"
   ```

4. **Push and create pull request**
   ```bash
   git push origin feature/my-feature
   ```

## Testing

### Backend
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_auth.py

# With coverage
pytest --cov=apps --cov=services
```

### Frontend
```bash
npm test
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make changes and add tests
4. Commit with clear messages (`git commit -m 'feat: add amazing feature'`)
5. Push to your fork (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

## License

Proprietary — WebMail Platform. All rights reserved.

## Support & Issues

- **Documentation** — See [README.md](./README.md) and [Frontend README](./frontend/README.md)
- **API Docs** — http://localhost:8000/api/docs/
- **Issues** — GitHub Issues on this repository
- **Email** — support@webmail-platform.local

## Repository

**GitHub** — https://github.com/IfyDon/mail_web_delivery

**Clone:**
```bash
git clone https://github.com/IfyDon/mail_web_delivery.git
cd mail_web_delivery
```

---

**Last Updated:** June 6, 2026  
**Version:** 1.0.0  
**Status:** In Active Development

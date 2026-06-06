# Tasks — WebMail Platform
> Actionable coding checklist · Track with ✅ when done  
> **Current position: Phase 6.5** (marked with 👉)

## 📌 Session Summary — Latest Changes (2024-06-06)

**Completed:**
- ✅ GitHub repo created: https://github.com/IfyDon/mail_web_delivery
- ✅ Local dev environment setup documented in README.md
- ✅ API endpoints fixed: `/api/` and `/api/v1/` now return proper JSON responses
- ✅ React Dashboard.js compilation error fixed (statusBadge function added)
- ✅ Backend (Django) + Frontend (React) both running locally without errors

**Full Details:** See **Phase 6.5 CHANGELOG** section below (scroll down)

---

## Phase 1 · Project Foundation & Environment
> Goal: Running Django + React with correct app names and SQLite · **COMPLETE**

### 1.1 Scaffold
- [x] `django-admin startproject config .`
- [x] `npx create-react-app frontend` (or Vite equivalent)
- [x] Create virtual env + `pip install -r requirements/dev.txt`
- [x] Initialise git, add `.gitignore`, commit initial scaffold

### 1.2 Database Configuration
- [x] Set `DATABASES` in `config/settings/base.py` to SQLite (`db.sqlite3`)
- [x] Confirm `dev.py` inherits base and overrides nothing for DB

### 1.3 App Folder Renames & Registry
- [x] Create `apps/authentication/` (not `auth/` — reserved by Django)
- [x] Create `apps/email_messages/` (not `messages/` — reserved by Python)
- [x] Register all apps in `INSTALLED_APPS` in `base.py`
- [x] Create `apps/__init__.py` and per-app `apps.py` with correct `name` attribute

### 1.4 First Run Verification
- [x] `python manage.py makemigrations` — zero errors
- [x] `python manage.py migrate` — all tables created
- [x] `python manage.py runserver` — no startup errors
- [x] React dev server starts on separate port

**✅ Checkpoint: Django + React both run without errors**

---

## Phase 2 · Core Backend — Auth, Domains, Templates, Suppression
> Goal: All shared backend models and services with no API yet

### 2.1 User & API Key Management
- [x] Custom `User` model with `email` as `USERNAME_FIELD` in `apps/authentication/models.py`
- [x] `EmailVerification` model (token, expiry, used flag)
- [x] `TwoFactorSecret` model linked to User (`django-otp` integration)
- [x] `APIKey` model in `apps/accounts/models.py` — UUID pk, `key_hash` (SHA-256), `name`, `last_used_at`, `is_active`
- [x] DRF authentication class `APIKeyAuthentication` in `core/middleware/api_key_middleware.py`
- [x] `Quota` model — tracks emails sent this billing period
- [x] Rate limiting setup via `django-ratelimit` (100 req/min per key)
- [x] DRF views: `SignupView`, `LoginView`, `EmailVerifyView`, `PasswordResetView`
- [x] URLs mounted at `/api/v1/auth/`
- [x] `django-otp` 2FA views: setup, verify, disable

### 2.2 Domain Verification (DNS)
- [x] `Domain` model — `name`, `verification_status`, `dkim_private_key`, `dkim_public_key`, `created_at`
- [x] DKIM key-pair generation on domain creation (`cryptography` lib or `openssl`)
- [x] `dns_utils.py` in `core/utils/` — SPF, DKIM, DMARC TXT lookup via `dnspython`
- [x] DRF views: list, create, retrieve, delete, trigger verify
- [x] `verify` endpoint calls `dns_utils.verify_domain()` and updates `verification_status`
- [x] URLs mounted at `/api/v1/domains/`

### 2.3 Email Templates Engine
- [x] `Template` model — `name`, `subject`, `html_body`, `text_body`, `version` (int), `created_at`
- [x] `TemplateVersion` model for history (optional but recommended)
- [x] `template_service.py` in `services/` — render with Python `string.Template` or Jinja2 context substitution
- [x] Optional: MJML compile step (call `mjml` CLI or `mjml` npm package via `subprocess`)
- [x] DRF CRUD views + serializers
- [x] URLs mounted at `/api/v1/templates/`

### 2.4 Suppression List & Compliance
> ⚠️ Partially implemented — skipped items carried forward to Phase 6.5B
- [x] `Bounce`, `Complaint`, `Unsubscribe` models exist in `apps/suppressions/models.py`
- [x] Unsubscribe landing page exists in `apps/suppressions/views.py`
- [x] `List-Unsubscribe` + `List-Unsubscribe-Post` headers built in `email_service.py`
- [x] DRF views: list suppressions, delete — in `api/v1/views/suppressions.py`
- [x] URLs mounted at `/api/v1/suppressions/`
- [x] `makemigrations apps.suppressions` + `migrate`
- [ ] **SKIPPED** → Phase 6.5B: `Suppression` model with `user` FK, `reason`, `unique_together = ('user', 'email')` (current models are user-less — global suppression, not per-user)
- [ ] **SKIPPED** → Phase 6.5B: `suppression_service.py` — `is_suppressed(user, email) → bool` + `add_suppression()`
- [ ] **SKIPPED** → Phase 6.5B: Pre-send suppression check scoped to the sending user
- [ ] **SKIPPED** → Phase 6.5B: Inbound SES/SNS handler creating Suppression records on bounce/complaint
- [ ] **SKIPPED** → Phase 6.5B: Fix `unsubscribe_url = None` in `send_email_task` — generate real HMAC-signed token

**✅ Checkpoint: Users, API keys, domains (DNS verify ready), templates, suppression all work from Python shell / basic DRF views**

---

## Phase 3 · Email Sending Pipeline & Events
> Goal: Async dispatch, open/click tracking, outbound webhooks · **COMPLETE**

### 3.1 Async Send Service
- [x] `config/celery.py` — Celery app, `broker_url` from env, `result_backend` Redis
- [x] `requirements/base.txt` — `celery`, `redis`, `boto3`, `Jinja2` confirmed/added
- [x] `integrations/ses/client.py` — `send_raw_email(message)` wrapping `boto3` SES
- [x] `integrations/smtp/client.py` — fallback SMTP relay using `smtplib`
- [x] `services/email_service.py` — `queue_email(message_id)` enqueues Celery task
- [x] `workers/tasks/send_email.py` — `send_email_task` with retry, tracking injection, status updates
- [x] Celery worker start command in `docker-compose.yml` (pre-existing)

### 3.2 Message & Event Models
- [x] `Message` model in `apps/email_messages/models.py` (UUID pk, all fields, DB indexes)
- [x] `Event` model in `apps/events/models.py` — FK to `Message`, `type`, `timestamp`, `metadata` JSONField
- [x] `makemigrations` + `migrate`
- [x] DB indexes: `Message.user_id`, `Message.created_at`, `Event.created_at`

### 3.3 Open & Click Tracking
- [x] `tracking/tokens.py` — `generate_open_token` + `generate_click_token`
- [x] `services/tracking_service.py` — `inject_tracking(html, message_id)`
- [x] `tracking/views.py` — `OpenTrackingView`, `ClickTrackingView`
- [x] `tracking/urls.py` — `/tracking/open/<token>/`, `/tracking/click/<token>/`
- [x] De-duplicate opens within 24h same recipient
- [x] `send_email_task` wired to call `inject_tracking` before relay dispatch

### 3.4 Webhook Dispatch
- [x] `Webhook` model — `user` FK, `url`, `secret`, `event_types` JSONField, `is_active`
- [x] `WebhookDispatchLog` model — all fields including `last_attempted_at`
- [x] `workers/tasks/webhook_dispatch.py` — HMAC-signed POST, 10 retries, full logging
- [x] `services/webhook_service.py` — `build_event_payload()` + `trigger_webhooks()`
- [x] `makemigrations webhooks` + `migrate`

**✅ Checkpoint: Send email via Python shell → queued → dispatched → events stored → webhooks fire**

---

## Phase 4 · REST API & Documentation
> Goal: Versioned, documented, secure REST API · **COMPLETE**

### 4.1 API Scaffolding
- [x] `api/urls.py` — mount `/api/v1/` prefix
- [x] `api/v1/urls.py` — all endpoint URL patterns imported
- [x] `APIKeyAuthentication` wired as default DRF auth class in `base.py`
- [x] Custom DRF throttle class `PerAPIKeyThrottle` (100 req/min) in `core/throttling.py`
- [x] Custom exception handler in `core/exceptions/handlers.py`

### 4.2 Core Endpoints
- [x] `POST /v1/send` + `POST /v1/send/batch`
- [x] `GET /v1/messages` (paginated, filterable) + `GET /v1/messages/{id}` (detail + timeline)
- [x] Templates CRUD · Domains CRUD + verify

### 4.3 Stats & Webhooks Endpoints
- [x] `GET /v1/stats` — per-day breakdown
- [x] `POST /v1/webhooks` · `DELETE /v1/webhooks/{id}` · `POST /v1/webhooks/{id}/test`

### 4.4 OpenAPI Documentation
- [x] `drf-spectacular` — Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/`

**✅ Checkpoint: All endpoints testable via Swagger UI; rate limiting confirmed via curl**

---

## Phase 5 · Public Marketing Website
> Goal: Postmark-style landing page · **COMPLETE**

- [x] Landing page — hero, features, CTA, testimonials, logo cloud
- [x] Code integration tabs (curl, Python, Node.js, Ruby, .NET, PHP) via Alpine.js + highlight.js
- [x] Cookie consent banner (4 categories) + legal pages (terms, privacy, GDPR)
- [x] Pricing page — Free / Startup / Enterprise tiers + FAQ accordion

**✅ Checkpoint: Landing page is polished, cookie banner works, visitors can reach signup**

---

## Phase 6 · Dashboard & Frontend (React)
> Goal: Authenticated React dashboard consuming the DRF API

### 6.1 React Setup & Routing · **COMPLETE**
- [x] `npm install axios react-router-dom @tanstack/react-query recharts tailwindcss postcss autoprefixer`
- [x] Tailwind CSS configured (`tailwind.config.js`, `postcss.config.js`)
- [x] `frontend/src/api/client.js` — Axios + `Authorization: Bearer` interceptor + 401 redirect
- [x] React Router with `PrivateRoute` wrapper; all pages registered
- [x] Per-resource API modules: `auth.js`, `domains.js`, `templates.js`, `messages.js`, `stats.js`, `webhooks.js`, `suppressions.js`

### 6.2 Authentication UI · **COMPLETE**
- [x] `LoginForm.js` — email + password, calls `/api/v1/auth/login/`
- [x] `SignupForm.js` — registration + email verification notice
- [x] `TwoFactorSetup.js` — QR code display + backup codes + code confirmation
- [x] `Settings.js` page — 2FA tab + change password tab; accessible via sidebar
- [x] `ApiKeys.js` — generate, **copy to clipboard**, revoke with confirmation dialog

### 6.3 Dashboard Overview & Analytics · **COMPLETE**
- [x] `Dashboard.js` — date range selector (7d/30d/90d) + 6 metric cards
- [x] Recharts `AreaChart` (sent/delivered/opened/clicked) with gradient fills
- [x] Recent messages table (last 10, "View all →" link to `/messages`)

### 6.4 Domain & Template Management UI · **COMPLETE**
- [x] `Domains.js` — card list with expandable DNS panel; auto-expands on add
- [x] `DnsRecordDisplay.js` — SPF / DKIM / DMARC with individual Copy buttons per host + value; ✓/✗ status icons
- [x] "Verify" button → POST `/api/v1/domains/{id}/verify/`; status help text per state
- [x] `TemplateEditor.js` — Editor/Preview tab toggle; live preview via `<iframe srcDoc>`; "Saved!" flash
- [x] `TemplateEdit.js` page — shared route for `/templates/new` and `/templates/:id`
- [x] `TestEmailButton.js` — inline recipient prompt; fires immediately

### 6.5 · Skipped Fixes + Frontend Completion 👉 **YOU ARE HERE**
> Consolidates all skipped Phase 2.4 items, Code Review fixes, analytics gap, and remaining frontend work

#### 📋 CHANGELOG — Session 2024-06-06
> Git initialization, GitHub repo creation, local test environment setup, and bug fixes

**Infrastructure & Documentation:**
- [x] Initialize git repository: `git init` → commit 44a388f with project files
- [x] Create GitHub repository: https://github.com/IfyDon/mail_web_delivery (public, with README)
- [x] Push to GitHub: `git remote add origin https://github.com/IfyDon/mail_web_delivery.git && git push -u origin main`
- [x] Update `.gitignore` to exclude `.continue/` and `celerybeat-schedule*` (local runtime artifacts)
- [x] Rewrite `README.md` with comprehensive local development setup and browser testing instructions
- [x] Document separate terminal commands for Django backend, Celery worker, Celery beat, React frontend
- [x] Add "Browser Testing Checklist" section with URLs to verify: `localhost:3000`, `localhost:8000/api/v1`, `localhost:8000/admin/`
- [x] Verify Python 3.12 in `.venv` with all requirements/dev.txt packages installed (Django 4.2.30, DRF 3.17.1, etc.)
- [x] Verify Node.js npm 11.12.1 with all frontend/node_modules installed (React 18.3.1, Tailwind 3.4.3, etc.)
- [x] Confirm SQLite database (db.sqlite3) with all 13 app migrations applied

**API Endpoint Fixes:**
- [x] Add missing `/api/` root endpoint handler: `api_root()` function in `config/urls.py` at path `"api/"` — returns JSON with API version, status, documentation links, and available versions
- [x] Add missing `/api/v1/` root endpoint handler: `api_root()` function in `api/v1/urls.py` at path `""` — returns JSON with available v1 endpoints (messages, domains, templates, etc.)
- [x] Verify endpoint responses: GET `http://localhost:8000/api/` and GET `http://localhost:8000/api/v1/` both return 200 with descriptive JSON

**React Component Fixes:**
- [x] Fix Dashboard.js ESLint error "statusBadge is not defined": add `statusBadge()` function mapping message statuses to Tailwind CSS classes
  - Maps: `sent`→`'bg-blue-100 text-blue-800'`, `delivered`→`'bg-green-100 text-green-800'`, `opened`→`'bg-purple-100 text-purple-800'`, `clicked`→`'bg-indigo-100 text-indigo-800'`, `bounced`→`'bg-orange-100 text-orange-800'`, `failed/complained`→`'bg-red-100 text-red-800'`, default→`'bg-gray-100 text-gray-800'`
  - Used at line 268 in JSX: `<span className={statusBadge(m.status)}>`
  - React component now compiles without ESLint errors

**Current Status — Local Environment Ready:**
- ✅ Django backend running on http://localhost:8000 (API available at /api/v1, admin at /admin/)
- ✅ React frontend running on http://localhost:3000 (all components compile)
- ✅ SQLite database ready (no external PostgreSQL needed for local testing)
- 🟡 Celery worker and beat schedulers (PowerShell activation and startup attempted; exact status unknown)
- ⚠️ Email service integration (currently uses console backend in dev; no SES/SendGrid credentials configured)

**Files Modified This Session:**
1. `config/urls.py` — Added `api_root()` view function and registered at `path("api/", ...)`
2. `api/v1/urls.py` — Added `api_root()` view function and registered at `path("", ...)`
3. `frontend/src/pages/Dashboard.js` — Added `statusBadge()` function mapping message status strings to Tailwind CSS classes
4. `README.md` — Completely rewritten with setup instructions, local dev commands, browser testing checklist, Docker Compose info, production considerations
5. `.gitignore` — Added `.continue/` and `celerybeat-schedule*` entries for local runtime artifacts
6. `.env` — Already configured for local development with `DJANGO_SETTINGS_MODULE=config.settings.dev`, `DEBUG=True`, `ALLOWED_HOSTS=localhost,127.0.0.1`

**Next Steps (On-Demand):**
- Verify Celery worker/beat are fully running: `& .\.venv\Scripts\Activate.ps1; celery -A config.celery worker --loglevel=info` (in separate terminal)
- Conduct full browser E2E test: signup → login → add domain → send email → view in dashboard
- Configure email service (AWS SES or SendGrid credentials) if testing email delivery
- Proceed with Phase 6.5B (Suppression system), 6.5C (Analytics models), 6.5D (remaining UI), 6.5E (Postmark dashboard parity)

#### 6.5A · Dependency & Security Fixes (CR-1, CR-2, CR-3)
> Must be resolved before any production deploy

- [ ] **CR-1** Add `dj-database-url>=2.1` to `requirements/prod.txt` — `prod.py:11` hard-imports it; clean install crashes with `ModuleNotFoundError`
- [ ] **CR-1** Verify `requirements/base.txt` is not empty in git — working tree shows it modified; confirm committed content is correct
- [ ] **CR-2** Raise Django floor: `Django>=4.2,<5.0` → `Django>=4.2.16,<5.0` — patches CVE-2024-38875 (ReDoS in urlize) and CVE-2024-41989/41990/45230
- [ ] **CR-2** Raise Pillow floor: `Pillow>=10.3` → `Pillow>=12.2.0` — CVE-2023-50447 (RCE via ImageMath.eval); add `libjpeg-dev zlib1g-dev` to Dockerfile so version-chasing doesn't recur
- [ ] **CR-2** Activate Argon2: add `PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher', 'django.contrib.auth.hashers.PBKDF2PasswordHasher']` to `config/settings/base.py` — `argon2-cffi` is already in requirements but Django silently falls back to PBKDF2 without this
- [ ] **CR-2** Raise allauth: `django-allauth>=0.61` → `django-allauth>=0.63.3` — CSRF bypass (SAML RelayState) + XSS (Facebook provider) fixed in 0.63.3/0.63.6
- [ ] **CR-3** Raise Celery: `celery[redis]>=5.3` → `celery[redis]>=5.4` — 5.3.x Kombu references `HiredisParser` removed in redis-py 5.0; workers crash at startup with `AttributeError`
- [ ] **CR-3** Move `psycopg2-binary` from `requirements/base.txt` → `requirements/dev.txt` only — both `psycopg2-binary` (base) and `psycopg2` (prod) install in production, non-deterministically shadowing each other
- [ ] **CR-3** Remove duplicate `django-redis>=5.4` from `requirements/prod.txt` — `base.txt` already pins `django-redis==5.4.0`; loose prod pin diverges from tested dev version on `pip install -U`
- [ ] Run `pip install -r requirements/dev.txt` and confirm zero errors after all changes above

#### 6.5B · Suppression System Fix (Phase 2.4 skipped)
> Current models are user-less (global suppression); design requires per-user scoping

- [ ] Add unified `Suppression` model to `apps/suppressions/models.py`:
  - Fields: `user = ForeignKey(User)`, `email = EmailField(db_index=True)`, `reason` (`bounce`/`complaint`/`unsubscribe`), `created_at`
  - `unique_together = ('user', 'email')` · composite DB index on `(user_id, email)`
  - Keep existing `Bounce`, `Complaint`, `Unsubscribe` models for raw event storage; `Suppression` is the derived lookup table
- [ ] Implement `services/suppression_service.py` (currently a stub):
  - `is_suppressed(user, email) → bool` — checks `Suppression` table
  - `add_suppression(user, email, reason)` — upsert with `get_or_create`
- [ ] Wire `is_suppressed()` into pre-send check in `services/email_service.py` with `user` argument
- [ ] Add `POST /api/v1/webhooks/ses/` inbound handler (`api/v1/views/ses_inbound.py`):
  - Verify SNS signature
  - Parse `Bounce` (hard bounce → `add_suppression`) and `Complaint` notifications
  - Return 200 to SNS immediately
- [ ] Fix `unsubscribe_url = None` in `workers/tasks/send_email.py`:
  - Generate HMAC-signed token: `tracking/tokens.py` → `generate_unsubscribe_token(user_id, email)`
  - Build full URL: `{BASE_URL}/unsubscribe/{token}/`
  - Pass to `make_list_unsubscribe_header()` so the One-Click header is functional
- [ ] Verify `/unsubscribe/<token>/` URL is mounted in `config/urls.py` at root (not under a prefix)
- [ ] `makemigrations apps.suppressions` + `migrate`
- [ ] Shell test: `add_suppression(user, "test@x.com", "bounce")` → `is_suppressed(user, "test@x.com")` returns `True`; send attempt returns `suppressed` status

#### 6.5C · Analytics Models (design.md §3 — currently empty stub)
> `apps/analytics/models.py` is `# Create your models here.` — analytics views/tasks exist but have no tables

- [ ] Implement `DailyStats` model in `apps/analytics/models.py`:
  - Fields: `user FK`, `date`, `stream`, `sent`, `delivered`, `opened`, `clicked`, `bounced`, `complained`
  - `unique_together = ('user', 'date', 'stream')` · index on `(user_id, date)`
- [ ] Implement `HourlyStats` model (optional — for sub-day resolution):
  - Fields: `user FK`, `hour = DateTimeField`, `sent`, `delivered`, `opened`, `clicked`
- [ ] `makemigrations apps.analytics` + `migrate`
- [ ] Wire `workers/tasks/aggregate_stats.py` to populate `DailyStats` from the `Event` table
- [ ] Update `api/v1/views/stats.py` to query `DailyStats` (pre-aggregated) when available, fall back to raw `Event` query

#### 6.5D · Frontend Completion
> Remaining Phase 6.5 items + gaps found in audit

- [ ] **Messages detail panel** — `Messages.js`: clicking a row expands or navigates to `/messages/:id`
  - Show: `to_address`, `from_address`, `subject`, full `html_body` preview, raw headers
  - Ordered event timeline: each `Event` row shows type, timestamp, metadata (IP, UA, URL clicked)
  - Add `/messages/:id` route in `App.js` + new `MessageDetail.js` page
  - "Resend" button visible only for `permanently_failed` messages
- [ ] **Webhooks active/inactive badge** — `Webhooks.js`: add `is_active` status badge column and `last_attempted_at` timestamp from `WebhookDispatchLog`; show dead-letter count for failed dispatches
- [ ] **Streams page** — new `Streams.js` page + sidebar link:
  - List streams (transactional / promotional) with send counts
  - Create/delete stream; show which relay/IP pool each uses
  - Add `/streams` route + `GET /api/v1/streams/` API call
- [ ] **Billing real data** — `Billing.js`: replace static hardcoded values with live API data
  - Fetch current plan + emails sent this month from `/api/v1/billing/` or `/api/v1/stats/`
  - Usage bar turns orange at ≥80% of monthly limit, red at ≥95%
  - Link "Upgrade" / "Contact us" buttons to Stripe/Paddle or contact page

#### 6.5E · Postmark Dashboard Parity (US-22 → US-28)
> Features present in Postmark admin dashboard not yet implemented in WebMail

**Suppression List Page (US-22)**
- [ ] New `Suppressions.js` page at `/suppressions` with sidebar link and count badge
- [ ] Table: email, reason badge, suppressed date; filter by reason; search by email
- [ ] "Remove" button → `DELETE /api/v1/suppressions/` (reactivates delivery)
- [ ] "Add manually" button → `POST /api/v1/suppressions/` with `reason=manual`
- [ ] Clicking a row shows originating message link (if within 45-day retention window)
- [ ] Backend: add `manual` as valid `reason` choice to `Suppression` model + `add_suppression()` service
- [ ] Backend: `POST /api/v1/suppressions/` endpoint accepting `{email, reason}` for manual suppression

**Message Detail & Event Timeline (US-24)**
- [ ] New `MessageDetail.js` page at `/messages/:id`; register route in `App.js`
- [ ] Display: recipient, sender, subject, stream, domain, sent time, status badge
- [ ] Sandboxed `<iframe srcDoc>` for HTML body preview; plain-text tab toggle
- [ ] Collapsible raw headers panel
- [ ] Event timeline: icon + type + timestamp + metadata per event (bounce code, IP, UA, clicked URL)
- [ ] "Resend" button for `permanently_failed` only → `POST /api/v1/messages/{id}/resend/`
- [ ] Backend: `POST /api/v1/messages/{id}/resend/` view that re-enqueues `send_email_task`

**Webhook Dispatch Log UI (US-25)**
- [ ] `Webhooks.js`: add `is_active` badge + `last_attempted_at` + dead-letter count per row
- [ ] Expandable panel per webhook showing last 20 `WebhookDispatchLog` entries: timestamp, HTTP status, response body (truncated to 200 chars), attempt number
- [ ] Failed rows highlighted red; "Retry now" button → `POST /api/v1/webhooks/{id}/retry/`
- [ ] "Disable" toggle → `PATCH /api/v1/webhooks/{id}/` with `{is_active: false}`
- [ ] Backend: `GET /api/v1/webhooks/{id}/logs/` endpoint returning paginated `WebhookDispatchLog`
- [ ] Backend: `POST /api/v1/webhooks/{id}/retry/` re-enqueues last failed dispatch payload

**Sending Health Card (US-26)**
- [ ] `Dashboard.js`: add "Sending Health" card alongside existing 6 metric cards
- [ ] Card shows bounce rate % and complaint rate % for selected date range, per stream (or all streams)
- [ ] Colour coding: green / amber / red using Postmark thresholds (bounce 10%, complaint 0.1%)
- [ ] Red state renders an inline `AlertBanner` component: "Your bounce rate exceeds the safe threshold. Review your suppression list."
- [ ] Rates computed from `DailyStats` (falls back to raw `Event` query until 6.5C lands)
- [ ] Backend: `GET /api/v1/stats/` extended to return `bounce_rate` and `complaint_rate` fields

**Stream Filter on Analytics (US-28)**
- [ ] `Dashboard.js` and `Analytics.js`: add "Stream" dropdown filter alongside date range selector
- [ ] Default: "All streams"; selecting a stream re-fetches all charts/cards scoped to that stream
- [ ] Backend: `GET /api/v1/stats/?stream=<id>&days=30` — add optional `stream` query param to stats view

**Per-Stream Health Indicators on Streams Page (US-23)**
- [ ] `Streams.js`: bounce rate and complaint rate badge per stream row with same green/amber/red thresholds
- [ ] Colour-coded badge turns red + tooltip: "Sending may be suspended if this rate is not reduced"
- [ ] Per-stream settings sub-panel: open tracking toggle, click tracking toggle

**Team / Users Management (US-27)**
- [ ] `TeamMember` model in `apps/authentication/models.py`: `account_owner FK`, `member FK (null)`, `email`, `role` (`admin`/`viewer`), `invited_at`, `accepted_at`, `invite_token` (HMAC-signed, 48h TTL)
- [ ] `makemigrations apps.authentication` + `migrate`
- [ ] `services/team_service.py`:
  - `invite_member(owner, email, role)` — create `TeamMember`, generate token, send invitation email
  - `accept_invite(token)` — set `accepted_at`, link `member` FK to new/existing `User`
  - `remove_member(owner, team_member_id)` — delete record
- [ ] Backend endpoints:
  - `GET /api/v1/team/` — list members + pending invites (owner/admin only)
  - `POST /api/v1/team/invite/` — send invite `{email, role}`
  - `PATCH /api/v1/team/{id}/` — change role
  - `DELETE /api/v1/team/{id}/` — remove member or cancel invite
  - `GET /accept-invite/<token>/` — public Django view that completes acceptance
- [ ] New `Settings/Team.js` React page at `/settings/team` (tab in existing Settings sidebar section)
  - Table: member email, role badge, status (active / pending), invited date, Remove button
  - "Invite teammate" button opens modal: email input + role selector (Admin / Viewer)
  - Pending rows show "Resend invitation" and "Cancel" controls
  - Owner row is non-removable, no role dropdown
- [ ] Permission guard: `TeamMemberPermission` DRF class — `admin` role gets same API access as account owner; `viewer` role restricted to GET endpoints on messages, stats, suppressions, webhooks

**✅ Checkpoint: Full user journey works in React — signup → add domain → send email → see analytics. Suppression blocks correctly. One-Click unsubscribe functional. Health indicators warn on high bounce/complaint rates. Team members can be invited and given scoped access.**

---

## Phase 7 · Production Readiness & Docker
> Goal: Hardened, monitored, one-command deployment

### 7.1 Security & Compliance
- [x] `SECURE_HSTS_SECONDS=31536000`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` — already set in `prod.py`
- [x] `django-cors-headers` — `CORS_ALLOWED_ORIGINS` set from env in `prod.py`
- [x] Sentry SDK initialised in `prod.py` (conditional on `SENTRY_DSN` env var)
- [ ] Physical address injected into every outgoing email footer (CAN-SPAM compliance)
- [ ] GDPR data export view — `GET /account/export/` returns JSON of all user data
- [ ] GDPR data delete view — `DELETE /account/` removes all user PII and queues data wipe

### 7.2 Caching, Optimisation & Background Jobs
- [ ] Configure `django-redis` as Django cache backend in `base.py` (`CACHES` setting)
- [ ] Register Celery Beat schedule in `config/settings/base.py` (`CELERY_BEAT_SCHEDULE`):
  - [ ] `cleanup_old_events` — archive `Event` rows older than 90 days (runs nightly)
  - [ ] `retry_stuck_messages` — re-queue `Message` rows stuck in `queued` > 1 hour (runs every 15 min)
  - [ ] `aggregate_daily_stats` — roll up `Event` table into `DailyStats` (runs hourly)
- [ ] Add `select_related` / `prefetch_related` on all list API query sets
- [ ] Confirm DB indexes: `Message.user_id`, `Message.created_at`, `Event.created_at`, `Suppression.(user_id, email)`

### 7.3 Monitoring & Logging
- [ ] Add `python-json-logger>=2.0` to `requirements/prod.txt`; replace plain text `logging.StreamHandler` in `prod.py` with JSON formatter for ELK/Loki ingestion
- [ ] `core/middleware/request_id.py` — generate UUID per request, inject as `X-Request-ID` header in both request and response; include in structured logs
- [ ] `/health/` endpoint (`web/views/health.py`) — returns `200 {"db": "ok", "redis": "ok", "celery": "ok"}` or `503` if any check fails; used as container liveness/readiness probe
- [ ] Celery Flower service in `docker-compose.yml` at port `5555`
- [ ] Prometheus metrics endpoint (optional — `django-prometheus`)

### 7.4 Docker & Orchestration
- [ ] `Dockerfile` — Python 3.12 slim base; install `libjpeg-dev zlib1g-dev` for Pillow; `pip install -r requirements/prod.txt`; `collectstatic`; run Gunicorn on port 8000
- [ ] `Dockerfile.frontend` — Node 20 build stage; `npm ci && npm run build`; copy `build/` to Nginx static dir
- [ ] `docker-compose.yml` — services: `web`, `worker`, `beat`, `redis`, `db` (PostgreSQL), `nginx`, `flower`
- [ ] `nginx/nginx.conf` — proxy `/api/` + `/tracking/` + `/unsubscribe/` → Gunicorn; serve `/static/` and `/media/` directly; TLS termination
- [ ] `.env.example` — document every required env var (DATABASE_URL, REDIS_URL, AWS_*, SENTRY_DSN, SECRET_KEY, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS)
- [ ] `docker-compose up --build` — full stack starts without errors
- [ ] Smoke test: `curl http://localhost/health/` returns 200 · `curl http://localhost/api/docs/` loads Swagger UI

**✅ Checkpoint: `docker-compose up` runs the entire stack. App is production-ready.**

---

## Code Review Fixes — Address Before Next Deploy
> Status updated after audit · Ordered most-severe first

### CR-1 · Critical (Breaks Production)
- [ ] Add `dj-database-url>=2.1` to `requirements/prod.txt` — `prod.py:11` imports it at module level; clean install crashes with `ModuleNotFoundError` → **carried into Phase 6.5A**
- [ ] Verify `requirements/base.txt` is not empty in git (working tree shows as modified) → confirm committed file has correct package list

### CR-2 · Security
- [ ] `Django>=4.2.16,<5.0` — CVE-2024-38875, CVE-2024-41989/41990/45230 → **Phase 6.5A**
- [ ] `Pillow>=12.2.0` + add `libjpeg-dev zlib1g-dev` to Dockerfile → **Phase 6.5A**
- [ ] Activate Argon2: set `PASSWORD_HASHERS` in `base.py` (argon2-cffi already in requirements) → **Phase 6.5A**
- [ ] `django-allauth>=0.63.3` — CSRF bypass + XSS fixed → **Phase 6.5A**

### CR-3 · Dependency Correctness
- [ ] `celery[redis]>=5.4` — Kombu 5.3 / HiredisParser incompatibility with redis-py 5 → **Phase 6.5A**
- [ ] Move `psycopg2-binary` to `requirements/dev.txt` only → **Phase 6.5A**
- [ ] Remove duplicate `django-redis>=5.4` from `requirements/prod.txt` → **Phase 6.5A**
- [x] `redis>=5.0` — no upper cap present (confirmed; no action needed)

---

## Ongoing / Cross-Cutting

### Tests
- [ ] `pytest` + `pytest-django` configured (already in `requirements/dev.txt`)
- [ ] Unit tests for all `services/` and `core/utils/` functions
- [ ] Integration tests for every API endpoint (auth required, correct status codes)
- [ ] Celery task tests using `task.apply()` (sync mode)
- [ ] E2E: Playwright test for signup → send email → see in dashboard
- [ ] CI pipeline (GitHub Actions) — run tests + lint on every push to main/PR

### Code Quality
- [ ] `black` + `ruff` configured in `pyproject.toml` (already in `requirements/dev.txt`)
- [ ] Pre-commit hooks installed (`pre-commit` already in dev.txt)
- [ ] `eslint` + `prettier` configured for React codebase
- [ ] All secrets via env vars — no hardcoded keys anywhere

---

> **Legend:**  ✅ Done  ·  👉 Current  ·  `[ ]` Not started  ·  `[x]` Complete

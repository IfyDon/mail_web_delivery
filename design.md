# Design — WebMail Platform
> Technical Architecture & Implementation Approach

---

## 1. High-Level Architecture

```
                         ┌─────────────────────────────────┐
                         │         Nginx (Reverse Proxy)    │
                         │  SSL termination · static files  │
                         └────────────┬────────────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                       │
      ┌────────▼────────┐   ┌─────────▼──────────┐  ┌────────▼────────┐
      │  Django/Gunicorn │   │  React (built SPA)  │  │  Tracking Views │
      │  (API + Web UI)  │   │  served as /static  │  │  /track/open,   │
      │  :8000           │   │                     │  │  /track/click   │
      └────────┬────────┘   └─────────────────────┘  └────────┬────────┘
               │                                               │
       ┌───────┼───────────────────────────────────────────────┘
       │       │
  ┌────▼────┐  ┌────────────┐    ┌──────────────┐
  │PostgreSQL│  │   Redis    │    │  Celery      │
  │(prod)    │  │broker+cache│───▶│  Workers     │
  │SQLite   │  └────────────┘    │  (async tasks)│
  │(dev)    │                    └──────┬────────┘
  └─────────┘                          │
                               ┌───────▼────────┐
                               │  AWS SES / SMTP │
                               │  (email relay)  │
                               └────────────────┘
```

---

## 2. Project Structure

```
web_mail/
├── config/                   # Django project config
│   ├── settings/
│   │   ├── base.py           # Shared settings
│   │   ├── dev.py            # SQLite, DEBUG=True
│   │   └── prod.py           # PostgreSQL, Redis, HTTPS
│   ├── urls.py               # Root URL routing
│   └── celery.py             # Celery app init
│
├── apps/
│   ├── authentication/       # User, EmailVerification, 2FA, TeamMember
│   ├── accounts/             # APIKey (hashed), Quota
│   ├── domains/              # Domain + DNS verification
│   ├── streams/              # Message streams (transactional/promotional)
│   ├── templates/            # Email template storage
│   ├── email_messages/       # Message records
│   ├── events/               # Open, click, bounce, complaint events
│   ├── analytics/            # DailyStats, HourlyStats (denormalised)
│   ├── webhooks/             # User webhook config + dispatch log
│   └── suppressions/         # Bounce/complaint/unsubscribe lists
│
├── api/v1/                   # DRF versioned API
├── web/                      # Marketing site + dashboard Django views
├── tracking/                 # Lightweight open/click endpoints
├── services/                 # Business logic layer
├── workers/tasks/            # Celery async tasks
├── integrations/             # AWS SES, SMTP, S3 adapters
├── core/                     # Shared utils, middleware, permissions
├── templates/                # Django HTML templates
├── frontend/                 # React application
└── tests/                    # unit / integration / e2e
```

---

## 3. Database Models

### 3.1 Core Models

```python
# apps/authentication/models.py
class User(AbstractBaseUser):
    email           = EmailField(unique=True)
    is_verified     = BooleanField(default=False)
    is_active       = BooleanField(default=True)
    created_at      = DateTimeField(auto_now_add=True)

# apps/accounts/models.py
class APIKey(models.Model):
    id              = UUIDField(primary_key=True)
    user            = ForeignKey(User)
    name            = CharField(max_length=100)
    key_hash        = CharField(max_length=64)   # SHA-256 of raw key
    last_used_at    = DateTimeField(null=True)
    is_active       = BooleanField(default=True)

# apps/domains/models.py
class Domain(models.Model):
    user                = ForeignKey(User)
    name                = CharField(max_length=253)
    verification_status = CharField(choices=['pending','verified','failed'])
    dkim_private_key    = TextField()
    dkim_public_key     = TextField()
    created_at          = DateTimeField(auto_now_add=True)

# apps/email_messages/models.py
class Message(models.Model):
    id              = UUIDField(primary_key=True)
    user            = ForeignKey(User, db_index=True)
    stream          = ForeignKey('streams.Stream')
    domain          = ForeignKey('domains.Domain')
    to_address      = EmailField()
    from_address    = EmailField()
    subject         = CharField(max_length=998)
    html_body       = TextField()
    text_body       = TextField()
    status          = CharField(choices=['queued','sent','delivered',
                                         'failed','suppressed'])
    attempts        = IntegerField(default=0)
    created_at      = DateTimeField(auto_now_add=True, db_index=True)

# apps/events/models.py
class Event(models.Model):
    message         = ForeignKey(Message)
    type            = CharField(choices=['delivered','open','click',
                                          'bounce','complaint','unsubscribe'])
    timestamp       = DateTimeField(auto_now_add=True, db_index=True)
    metadata        = JSONField(default=dict)   # IP, user agent, URL clicked, etc.

# apps/suppressions/models.py
class Suppression(models.Model):
    user            = ForeignKey(User)
    email           = EmailField(db_index=True)
    reason          = CharField(choices=['bounce','complaint','unsubscribe','manual'])
    created_at      = DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'email')

# apps/authentication/models.py  (addition)
class TeamMember(models.Model):
    account_owner   = ForeignKey(User, related_name='team_members')
    member          = ForeignKey(User, related_name='team_memberships', null=True)
    email           = EmailField()               # pre-accept invitation target
    role            = CharField(choices=['admin','viewer'], default='viewer')
    invited_at      = DateTimeField(auto_now_add=True)
    accepted_at     = DateTimeField(null=True)
    invite_token    = CharField(max_length=64, unique=True)  # HMAC-signed, 48h TTL
    class Meta:
        unique_together = ('account_owner', 'email')
```

---

## 4. API Design

### Base URL: `/api/v1/`
### Authentication: `Authorization: Bearer <api_key>`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/send` | Send single email |
| POST | `/send/batch` | Send up to 500 emails |
| GET | `/messages` | List messages (filterable) |
| GET | `/messages/{id}` | Message detail + event timeline |
| GET/POST | `/templates` | List / create templates |
| GET/PUT/DELETE | `/templates/{id}` | Template detail |
| GET/POST | `/domains` | List / add domain |
| POST | `/domains/{id}/verify` | Trigger DNS verification |
| GET | `/stats` | Aggregated stats (date range) |
| GET/POST | `/webhooks` | List / create webhooks |
| DELETE | `/webhooks/{id}` | Remove webhook |
| GET/DELETE | `/suppressions` | List / remove suppressions |
| POST | `/suppressions` | Manually add a suppression |
| GET | `/streams` | List message streams |
| POST | `/streams` | Create a stream |
| DELETE | `/streams/{id}` | Archive / delete stream |
| GET | `/webhooks/{id}/logs` | Dispatch log for a webhook (last 20) |
| POST | `/webhooks/{id}/retry` | Re-enqueue latest failed dispatch |
| GET | `/team` | List team members + pending invitations |
| POST | `/team/invite` | Send invitation email to new member |
| PATCH | `/team/{id}` | Change member role |
| DELETE | `/team/{id}` | Remove member / cancel invitation |
| GET | `/stats` | Aggregated stats (date range, optional stream filter) |

### Send Payload
```json
{
  "to": "recipient@example.com",
  "from": "sender@verified-domain.com",
  "subject": "Welcome",
  "html_body": "<h1>Hello</h1>",
  "text_body": "Hello",
  "stream": "transactional",
  "template_id": "optional-uuid",
  "template_data": { "name": "Alice" },
  "track_opens": true,
  "track_clicks": true
}
```

### Send Response (202 Accepted)
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "submitted_at": "2025-01-15T10:30:00Z"
}
```

---

## 5. Async Sending Pipeline

```
POST /api/v1/send
       │
       ▼
DRF View (send.py)
  1. Validate API key → get User
  2. Check suppression list
  3. Validate from_address domain ownership
  4. Save Message(status='queued')
  5. Enqueue send_email_task.delay(message_id)
  6. Return 202 + message_id
       │
       ▼ (async, Celery worker)
send_email_task
  1. Load Message from DB
  2. Render template if template_id set
  3. Inject tracking pixel + rewrite links
  4. Add List-Unsubscribe header
  5. Call SES/SMTP relay client
  6. Update Message.status → 'sent'
  7. Enqueue dispatch_webhook_task for 'delivered'
       │
       ▼ (ESP webhook callback)
/api/v1/webhooks/aws-ses/  (internal receiver)
  Create Event(type='delivered' | 'bounce' | 'complaint')
  If bounce/complaint → create Suppression record
  Enqueue dispatch_webhook_task
```

### Retry Strategy
- Retry 1: 30s · Retry 2: 2m · Retry 3: 10m · Retry 4: 1h · Retry 5: 6h
- After 5 failures → `status='permanently_failed'`, webhook fired

---

## 6. Open & Click Tracking

```
# tracking/urls.py
/track/open/<token>/   → OpenTrackingView
/track/click/<token>/  → ClickTrackingView

# Flow — Open
1. Token = HMAC-signed {message_id, recipient_hash}
2. Log Event(type='open', metadata={ip, user_agent})
3. Return 1×1 transparent GIF (no redirects)

# Flow — Click
1. Token carries encrypted original_url + message_id
2. Log Event(type='click', metadata={url, ip})
3. HTTP 302 redirect to original URL (target < 300ms p99)
```

---

## 7. Webhook Dispatch

```python
# workers/tasks/webhook_dispatch.py
@app.task(bind=True, max_retries=10)
def dispatch_webhook_task(self, webhook_id, event_payload):
    webhook = Webhook.objects.get(id=webhook_id)
    signature = hmac.new(webhook.secret, payload, sha256).hexdigest()
    response = requests.post(
        webhook.url,
        json=event_payload,
        headers={"X-WebMail-Signature": signature},
        timeout=10,
    )
    if response.status_code not in (200, 201, 202):
        raise self.retry(countdown=exponential_backoff(self.request.retries))
```

---

## 8. DNS Verification Utility

```python
# core/utils/dns_utils.py
import dns.resolver

def verify_domain(domain_name: str, dkim_selector: str) -> dict:
    results = {'spf': False, 'dkim': False, 'dmarc': False}
    try:
        spf = dns.resolver.resolve(domain_name, 'TXT')
        results['spf'] = any('v=spf1' in str(r) for r in spf)
    except dns.exception.DNSException:
        pass
    # Similar for DKIM (selector._domainkey.domain) and DMARC (_dmarc.domain)
    return results
```

---

## 9. Frontend Architecture (React)

```
frontend/src/
├── api/          # Axios client, per-resource service modules
├── pages/        # Dashboard, Domains, Templates, Messages,
│                 # MessageDetail, Analytics, Webhooks,
│                 # Suppressions, Streams, Billing,
│                 # Settings (2FA, Password, Team / Users)
├── components/
│   ├── common/   # Header, Sidebar, DataTable, Chart
│   ├── auth/     # LoginForm, SignupForm, TwoFactorSetup
│   ├── domains/  # DomainList, AddDomainForm, DnsRecordDisplay
│   ├── templates/# TemplateList, TemplateEditor (CodeMirror)
│   └── webhooks/ # WebhookForm
├── hooks/        # useAuth, useApi (Axios interceptors)
└── utils/        # formatters.js (dates, numbers, status badges)
```

**State management:** React Context for auth; React Query (`@tanstack/query`) for server state caching.  
**Charts:** Recharts (already in React ecosystem, no extra bundle).  
**Routing:** React Router v6 with protected routes.

### Dashboard page composition (Postmark parity)

| Page / Component | Route | Notes |
|---|---|---|
| `Dashboard.js` | `/` | 6 metric cards + **Sending Health card** (bounce %, complaint % with colour coding) + recent messages table + stream filter dropdown |
| `Messages.js` | `/messages` | Filterable list |
| `MessageDetail.js` | `/messages/:id` | Full headers, iframe body preview, event timeline, Resend button |
| `Streams.js` | `/streams` | Per-stream send counts, colour-coded bounce/complaint badges, create/archive |
| `Suppressions.js` | `/suppressions` | Filter by reason, search, remove, manual add; count badge on sidebar |
| `Webhooks.js` | `/webhooks` | Active/inactive badge, last attempt time, dead-letter count, expandable dispatch log, Retry/Disable controls |
| `Settings/Team.js` | `/settings/team` | Invite by email, role badge, pending invitations, remove member |
| `Analytics.js` | `/analytics` | Date range + stream filter; all charts respond to both |

---

## 10. Settings & Environment Split

| Setting | dev.py | prod.py |
|---------|--------|---------|
| `DEBUG` | `True` | `False` |
| `DATABASES` | SQLite (`db.sqlite3`) | PostgreSQL (env var) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis (env var) |
| `ALLOWED_HOSTS` | `['localhost', '127.0.0.1']` | Domain from env |
| `EMAIL_BACKEND` | `console` or `locmem` | AWS SES via boto3 |
| `STATIC_ROOT` | N/A | `/app/staticfiles/` |
| `SECURE_HSTS_*` | Off | On |

---

## 11. Deployment Stack (Docker Compose)

```yaml
services:
  web:      # Django + Gunicorn
  worker:   # Celery worker (same image as web)
  beat:     # Celery Beat (scheduled tasks)
  redis:    # Celery broker + Django cache
  db:       # PostgreSQL (prod) / omitted in dev (SQLite)
  nginx:    # Reverse proxy + static file server
  frontend: # React build stage → static files copied to Nginx
```

---

## 12. Monitoring

| Tool | Purpose |
|------|---------|
| Sentry | Error tracking (Django + React) |
| Celery Flower | Task monitoring UI |
| Prometheus + Grafana | Metrics (request rates, queue depth) |
| Structured JSON logs | ELK / Loki ingestion |
| `/health/` endpoint | Container liveness/readiness probe |

---

## 13. Security Checklist

- API keys stored as SHA-256 hash only; raw key shown once
- HMAC-SHA256 signature on every outbound webhook
- Tracking tokens are HMAC-signed (tamper-proof)
- `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` in prod
- `django-cors-headers` restricts cross-origin requests to known frontend origin
- `django-ratelimit` on auth endpoints (brute-force protection)
- GDPR: data export + account delete views in `web/views/account.py`
- CAN-SPAM: `List-Unsubscribe` header + physical address in every email footer
- Cookie consent via `django-cookie-consent`

---

## 14. SMTP Relay Architecture

WebMail must accept SMTP connections so legacy applications can send through it without code changes.

```
Client App (SMTP)
       │  port 587 (STARTTLS)
       ▼
┌──────────────────┐
│  smtpd gateway   │  aiosmtpd or Postfix relay
│  apps/smtp/      │  auth: API key as SMTP password
└────────┬─────────┘
         │  validates API key → domain → suppression
         ▼
services/email_service.py  (same send pipeline as REST API)
         │
         ▼
send_email_task  →  SES / SMTP relay
```

**Key design decisions:**
- SMTP AUTH LOGIN — API key used as the password; username ignored
- STARTTLS required; plain-text SMTP blocked
- Same pre-send checks (suppression, domain ownership) as the REST path
- Message stored in `email_messages.Message` identically to API sends
- `stream` defaults to `transactional`; override via `X-WebMail-Stream` header

**New files:**
- `apps/smtp/server.py` — `aiosmtpd`-based SMTP server, runs as a separate process/container
- `apps/smtp/handler.py` — `SMTPHandler` class: validates auth, calls `email_service.queue_email()`
- `docker-compose.yml` — new `smtp` service exposing port 587

---

## 15. Scheduled Send System

```python
# apps/email_messages/models.py — extension
class Message(models.Model):
    ...
    scheduled_at    = DateTimeField(null=True, db_index=True)   # None = send immediately

# workers/tasks/scheduled_send.py
@app.task
def dispatch_scheduled_messages():
    """Runs every minute via Celery Beat."""
    due = Message.objects.filter(
        status='scheduled',
        scheduled_at__lte=timezone.now()
    ).select_related('user', 'domain', 'stream')
    for msg in due:
        send_email_task.delay(str(msg.id))
```

**API change** — `POST /api/v1/send` accepts optional `send_at` (ISO-8601):
```json
{ "to": "...", "send_at": "2026-07-01T09:00:00Z" }
```
Response: `202 Accepted` with `"status": "scheduled"`.

**Cancel endpoint:** `DELETE /api/v1/messages/{id}/schedule/` — only allowed while `status='scheduled'`.

---

## 16. Real-time WebSocket Architecture

```
React Dashboard
      │  ws://api/ws/stats/
      ▼
Django Channels (ASGI)
      │
      ▼  channel layer
    Redis pub/sub
      ▲
      │  publish on every Event creation
workers/tasks/send_email.py
workers/tasks/webhook_dispatch.py
```

**Implementation:**
- `django-channels` replaces Gunicorn with Daphne (ASGI) or adds `uvicorn` workers
- `channels_redis` as channel layer backend
- `StatsConsumer` in `web/consumers.py` — joins room scoped to `user_id`, pushes delta stats every 5 s or on event
- React: `useWebSocket` hook wraps `WebSocket`; updates Recharts data without full re-fetch
- Auth: JWT token passed as query param `?token=` on WebSocket handshake, validated in `StatsConsumer.connect()`

**docker-compose.yml** — replace Gunicorn with Daphne:
```yaml
web:
  command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## 17. Advanced Analytics Pipeline

### 17.1 Link Tagging (UTM Parameters)

`services/tracking_service.py` — extend `inject_tracking()`:
1. Parse every `<a href>` in HTML body
2. Append `utm_source=webmail&utm_medium=email&utm_campaign=<stream>&utm_content=<message_id>` unless the URL already contains `utm_source`
3. Store original URL in `ClickToken`; rewrite href to click-tracking URL

### 17.2 Engagement Scoring

```python
# apps/analytics/models.py
class ContactEngagement(models.Model):
    user        = ForeignKey(User, db_index=True)
    email       = EmailField(db_index=True)
    score       = IntegerField(default=0)   # recalculated nightly
    last_open   = DateTimeField(null=True)
    last_click  = DateTimeField(null=True)
    open_count  = IntegerField(default=0)
    click_count = IntegerField(default=0)
    class Meta:
        unique_together = ('user', 'email')
```

Scoring weights (configurable via settings):
- Open: +2 · Click: +5 · Bounce: −10 · Complaint: −50
- Score decays 10% per month (Celery Beat monthly task)

### 17.3 Geolocation & Device Tracking

`tracking/views.py` — extend `OpenTrackingView` and `ClickTrackingView`:
```python
import geoip2.database

reader = geoip2.database.Reader('GeoLite2-City.mmdb')

def get_geo(ip):
    try:
        r = reader.city(ip)
        return {'country': r.country.iso_code, 'city': r.city.name}
    except Exception:
        return {}
```
- `Event.metadata` gains: `country`, `city`, `device_type` (`desktop`/`mobile`/`tablet`), `browser`, `os`
- `user-agents` library parses `User-Agent` header
- MaxMind GeoLite2-City.mmdb downloaded at container build time

---

## 18. A/B Testing Framework

```python
# apps/templates/models.py — extension
class ABTest(models.Model):
    user        = ForeignKey(User)
    name        = CharField(max_length=100)
    stream      = ForeignKey('streams.Stream')
    status      = CharField(choices=['draft','running','complete'])
    winner      = ForeignKey('ABTestVariant', null=True)
    sample_pct  = IntegerField(default=50)   # % of audience to test; remainder get winner
    metric      = CharField(choices=['open_rate','click_rate'])
    created_at  = DateTimeField(auto_now_add=True)

class ABTestVariant(models.Model):
    test        = ForeignKey(ABTest)
    label       = CharField(max_length=50)   # 'A', 'B', 'C'
    template    = ForeignKey('templates.Template')
    subject     = CharField(max_length=998, blank=True)
    sent        = IntegerField(default=0)
    opens       = IntegerField(default=0)
    clicks      = IntegerField(default=0)

    @property
    def open_rate(self):
        return self.opens / self.sent if self.sent else 0
```

**Send flow:** `POST /api/v1/send` with `ab_test_id` — worker picks variant by round-robin, records `variant_id` on `Message`.

**Winner selection:** Celery Beat task checks statistical significance (chi-squared p < 0.05) and sets `ABTest.winner`; subsequent sends use winner template only.

---

## 19. Dedicated IP Management

```python
# apps/accounts/models.py — extension
class IPPool(models.Model):
    user        = ForeignKey(User)
    name        = CharField(max_length=100)
    ips         = ArrayField(GenericIPAddressField())  # PostgreSQL ArrayField
    stream      = OneToOneField('streams.Stream', null=True)
    warming     = BooleanField(default=True)
    created_at  = DateTimeField(auto_now_add=True)

class WarmingSchedule(models.Model):
    pool        = ForeignKey(IPPool)
    day         = IntegerField()    # day number since pool created
    max_volume  = IntegerField()    # daily send cap for this day
```

**Integration:** `send_email_task` selects outbound IP from the pool assigned to the message's stream. SES `ConfigurationSet` or SMTP `MAIL FROM` used to bind the IP.

**Warming plan** (ISP-safe defaults):
| Day | Max Daily Volume |
|-----|-----------------|
| 1–5 | 200 |
| 6–10 | 1 000 |
| 11–20 | 10 000 |
| 21–30 | 50 000 |
| 31+ | Unlimited |

---

## 20. Enterprise Security

### 20.1 SSO / SAML 2.0

- `django-allauth` SAML provider (added in allauth 0.63+)
- `SAML_PROVIDERS` dict in `prod.py` — entity ID, SSO URL, x509 cert
- `GET /sso/saml/login/` → IdP redirect → `POST /sso/saml/acs/` → create/link User
- `TeamMember.sso_only = BooleanField` — forces SSO; password login rejected

### 20.2 Audit Trail

```python
# apps/accounts/models.py
class AuditLog(models.Model):
    user        = ForeignKey(User, db_index=True)
    actor       = ForeignKey(User, related_name='actor_logs')
    action      = CharField(max_length=100)   # 'api_key.created', 'domain.deleted', etc.
    resource_id = CharField(max_length=64, blank=True)
    ip_address  = GenericIPAddressField(null=True)
    user_agent  = CharField(max_length=300, blank=True)
    metadata    = JSONField(default=dict)
    created_at  = DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        indexes = [models.Index(fields=['user', 'created_at'])]
```

`core/middleware/audit.py` — `AuditMiddleware` wraps mutating API views and writes `AuditLog` records post-response.

### 20.3 IP Whitelisting

```python
# core/middleware/ip_whitelist.py
class IPWhitelistMiddleware:
    def __call__(self, request):
        if request.path.startswith('/api/'):
            whitelist = cache.get(f'ip_whitelist:{request.user.id}')
            if whitelist and get_client_ip(request) not in whitelist:
                return JsonResponse({'error': 'IP not whitelisted'}, status=403)
        return self.get_response(request)
```

`IPWhitelist` model: `user FK`, `cidr CharField` (supports ranges), `label`, `created_at`.

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

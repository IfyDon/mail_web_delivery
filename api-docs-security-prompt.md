# WebMail — Secure API Documentation Access
> Paste into Claude Code to implement API docs access control.

---

## Project Context

**WebMail** is a Postmark-like transactional email platform.

**Stack:** Django + DRF, `drf-spectacular` for OpenAPI docs, Nginx reverse proxy.

**Relevant files:**
```
config/
├── settings/
│   ├── base.py
│   ├── dev.py
│   └── prod.py
├── urls.py
nginx/
└── nginx.conf
```

**Current problem:** `drf-spectacular` Swagger UI (`/api/docs/`) and ReDoc (`/api/redoc/`) are mounted as unauthenticated Django views. Anyone who finds the URL gets the full API schema — every endpoint, every request/response shape, every parameter — with no login required. This is a security issue in production.

---

## Task

Implement a **three-layer** API docs access control strategy. Work through each step in order.

---

### Step 1 — Read current URL config

Read `config/urls.py` and locate the existing `drf-spectacular` URL patterns. They will look similar to:

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

---

### Step 2 — Restrict docs to `DEBUG=True` only

Wrap the docs URL patterns in a `settings.DEBUG` guard so they are completely absent in production:

```python
# config/urls.py
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
```

This means:
- `dev.py` (DEBUG=True) → docs are accessible at `/api/docs/`
- `prod.py` (DEBUG=False) → those URL patterns don't exist; Django returns 404

Confirm `dev.py` has `DEBUG = True` and `prod.py` has `DEBUG = False`. If either is missing, add it.

---

### Step 3 — Add staff-only fallback for production access

There will be times internal team members need to view docs in a production-like environment (staging). Add a second, staff-gated URL mount that is always present but protected:

```python
# config/urls.py
from django.contrib.admin.views.decorators import staff_member_required
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Always mounted — staff only
urlpatterns += [
    path(
        'api/schema/internal/',
        staff_member_required(SpectacularAPIView.as_view()),
        name='schema-internal',
    ),
    path(
        'api/docs/internal/',
        staff_member_required(
            SpectacularSwaggerView.as_view(url_name='schema-internal')
        ),
        name='swagger-ui-internal',
    ),
]

# Dev only — open access for local development convenience
if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
```

`staff_member_required` redirects unauthenticated or non-staff users to the Django admin login page. Non-staff authenticated users (regular API users) cannot access it.

---

### Step 4 — Block docs URLs at Nginx level

Read `nginx/nginx.conf`. Add explicit `deny all` directives for the public docs paths so they never reach Django in production, regardless of Django config:

```nginx
# Block public API docs in production
location /api/docs/ {
    return 404;
}

location /api/redoc/ {
    return 404;
}

location /api/schema/ {
    return 404;
}

# Internal docs — allow only from private/internal IP ranges
location /api/docs/internal/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;
    proxy_pass http://web:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

location /api/schema/internal/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;
    proxy_pass http://web:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Place these `location` blocks **before** the general `/api/` proxy block so Nginx matches them first. If the general block already exists, confirm the new specific blocks appear above it in the file.

---

### Step 5 — Exclude internal-only endpoints from the public schema

When WebMail eventually publishes public-facing API docs (for developer onboarding), endpoints like `/api/v1/team/`, `/api/v1/billing/`, `/api/v1/suppressions/` (management), and `/api/v1/webhooks/ses/` (internal SES receiver) should not appear in the public schema.

In each of those DRF views, add the `@extend_schema` decorator to mark them as internal:

```python
# Example — apply to every view that should be hidden from public schema
from drf_spectacular.utils import extend_schema

@extend_schema(exclude=True)
class SESInboundWebhookView(APIView):
    ...

@extend_schema(exclude=True)
class TeamMemberView(ModelViewSet):
    ...

@extend_schema(exclude=True)
class BillingView(APIView):
    ...
```

Find all views in these files and add `@extend_schema(exclude=True)`:
- `api/v1/views/ses_inbound.py`
- `api/v1/views/team.py` (if it exists)
- `api/v1/views/billing.py` (if it exists)
- Any view whose URL path contains `internal`, `admin`, `ses`, or `sns`

---

### Step 6 — Verify the smoke test in `tasks.md`

The existing task in Phase 7.4 reads:

```
Smoke test: curl http://localhost/health/ returns 200
           · curl http://localhost/api/docs/ loads Swagger UI
```

The second check is now only valid in dev. Update that smoke test line in `tasks.md` to:

```markdown
- [ ] Smoke test:
  - `curl http://localhost/health/` → 200
  - `curl http://localhost/api/docs/` → 404 (confirm docs are blocked in prod)
  - `curl http://localhost/api/docs/internal/` from internal IP → 200 after staff login
```

---

### Step 7 — Confirm no hardcoded docs URL elsewhere

Search the codebase for any hardcoded references to `/api/docs/` or `/api/redoc/` in:
- Frontend React files (`frontend/src/`)
- Landing page templates (`web/templates/`)
- README or any markdown docs

If found in the landing page (e.g. a "Read the docs" CTA link), update to point to a future public docs URL placeholder (`/docs/` or `#`) rather than the internal Swagger route.

Run:
```bash
grep -r "/api/docs" . --include="*.js" --include="*.html" --include="*.md" --include="*.py"
```

Report what is found and update each occurrence appropriately.

---

## Expected End State

| URL | Dev (DEBUG=True) | Prod (DEBUG=False) |
|---|---|---|
| `/api/docs/` | ✅ Open (local dev convenience) | ❌ 404 at Nginx |
| `/api/redoc/` | ✅ Open | ❌ 404 at Nginx |
| `/api/schema/` | ✅ Open | ❌ 404 at Nginx |
| `/api/docs/internal/` | ✅ Staff only | ✅ Staff only, internal IP only |
| `/api/schema/internal/` | ✅ Staff only | ✅ Staff only, internal IP only |

No configuration change should break local development. Running `python manage.py runserver` with `DEBUG=True` must still serve docs at `/api/docs/` for developer convenience.

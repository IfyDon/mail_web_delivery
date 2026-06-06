# Requirements — WebMail Platform
> Postmark-like transactional email service  
> Stack: Django + DRF · React · Celery + Redis · PostgreSQL (SQLite in dev)

---

## 1. Authentication & Account Management

### US-01 · User Registration
**As a** visitor, **I want to** sign up with my email and password **so that** I can access the platform.

**Acceptance Criteria**
- [ ] Registration form collects: email, password, confirm password
- [ ] Email must be unique; duplicate triggers a clear error
- [ ] Verification email is sent on signup
- [ ] Account is inactive until email is verified
- [ ] Password enforces minimum 8 characters with complexity rules

---

### US-02 · Login & Session
**As a** registered user, **I want to** log in **so that** I can access my dashboard.

**Acceptance Criteria**
- [ ] Login accepts email + password
- [ ] Invalid credentials return a generic error (no enumeration)
- [ ] Session token / JWT issued on success
- [ ] "Remember me" extends session duration
- [ ] Locked out after 5 failed attempts for 15 minutes

---

### US-03 · Two-Factor Authentication (2FA)
**As a** user, **I want to** enable 2FA on my account **so that** it is more secure.

**Acceptance Criteria**
- [ ] TOTP setup page shows QR code (via `django-otp`)
- [ ] Backup codes generated and downloadable at setup
- [ ] 2FA prompt appears on every login after enabling
- [ ] User can disable 2FA from account settings

---

### US-04 · API Key Management
**As a** developer, **I want to** generate and revoke API keys **so that** I can authenticate my application's email requests.

**Acceptance Criteria**
- [ ] User can generate multiple named API keys
- [ ] Key value shown once on creation; stored hashed in DB
- [ ] Keys can be revoked (soft-deleted) individually
- [ ] Each key shows last-used timestamp and request count
- [ ] Rate limit: 100 req/min and 10 000 emails/hour per key

---

### US-05 · Password Reset
**As a** user, **I want to** reset my password via email **so that** I can regain access if I forget it.

**Acceptance Criteria**
- [ ] "Forgot password" sends a time-limited reset link (1 hour TTL)
- [ ] Link is single-use; second visit returns an error
- [ ] New password must pass the same complexity rules as registration

---

## 2. Domain Management

### US-06 · Add Sending Domain
**As a** user, **I want to** add a custom sending domain **so that** emails are sent from my own address.

**Acceptance Criteria**
- [ ] User enters a domain name; system saves it with `status=pending`
- [ ] System generates DKIM private/public key pair for the domain
- [ ] UI displays the DNS records to publish: DKIM TXT, SPF TXT, DMARC TXT

---

### US-07 · DNS Verification
**As a** user, **I want to** verify my domain's DNS records **so that** the platform confirms I own it.

**Acceptance Criteria**
- [ ] "Verify" button triggers a DNS lookup via `dnspython`
- [ ] System checks SPF, DKIM, and DMARC TXT records
- [ ] Status updates to `verified` when all records resolve correctly
- [ ] Partial pass shows which records are missing
- [ ] Verification can be re-triggered at any time

---

## 3. Email Templates

### US-08 · Create / Edit Email Template
**As a** user, **I want to** create and edit HTML/plain-text email templates **so that** I can reuse them across campaigns.

**Acceptance Criteria**
- [ ] Template fields: name, subject, HTML body, plain-text body
- [ ] HTML editor uses CodeMirror (or equivalent) with syntax highlighting
- [ ] Supports `{{ variable }}` context substitution
- [ ] Optional MJML source field that compiles to HTML on save
- [ ] Version history kept; user can revert to previous version

---

### US-09 · Test Template
**As a** user, **I want to** send a test email using a template **so that** I can preview how it renders in an inbox.

**Acceptance Criteria**
- [ ] "Send test" button prompts for a recipient address
- [ ] Test email sent immediately (bypasses queue priority) with sample context data
- [ ] Confirmation shown on success; error shown if sending fails

---

## 4. Email Sending (API & Core Engine)

### US-10 · Send a Single Email via API
**As a** developer, **I want to** POST to `/api/v1/send` **so that** my application can send transactional emails.

**Acceptance Criteria**
- [ ] Endpoint accepts: `to`, `from`, `subject`, `html_body` / `text_body` or `template_id` + `template_data`
- [ ] Request validated against sender domain (must be verified)
- [ ] Recipient checked against suppression list before queuing
- [ ] On success: HTTP `202 Accepted` with `message_id` returned immediately
- [ ] Message saved with `status=queued`; Celery task enqueued

---

### US-11 · Async Email Dispatch
**As the** system, **I need to** process queued emails asynchronously **so that** the API remains fast under load.

**Acceptance Criteria**
- [ ] Celery worker picks up `send_email_task` and calls AWS SES (or SMTP)
- [ ] Message status updated to `sent` or `failed` after relay response
- [ ] Exponential backoff retry up to 5 attempts on transient failure
- [ ] After 5 failures, message status set to `permanently_failed`; user notified via webhook

---

### US-12 · Separate Message Streams
**As a** user, **I want to** assign emails to a stream (transactional or promotional) **so that** my deliverability is protected.

**Acceptance Criteria**
- [ ] Streams configurable per account: `transactional`, `promotional`
- [ ] Each stream can use a different relay/IP pool configuration
- [ ] Sending to wrong stream type flagged in dashboard

---

## 5. Event Tracking

### US-13 · Open Tracking
**As a** user, **I want to** know when recipients open my emails **so that** I can measure engagement.

**Acceptance Criteria**
- [ ] Tracking pixel (`/track/open/<token>`) embedded in HTML emails
- [ ] Endpoint returns a 1×1 transparent GIF and logs an `OpenEvent`
- [ ] Subsequent opens from the same recipient within 24 hours de-duplicated

---

### US-14 · Click Tracking
**As a** user, **I want to** know which links recipients click **so that** I can understand content performance.

**Acceptance Criteria**
- [ ] All links in HTML rewritten to `/track/click/<token>`
- [ ] Endpoint logs a `ClickEvent` then redirects to the original URL
- [ ] Original URL stored securely (not exposed in token)
- [ ] Redirect must be ≤ 300 ms p99

---

## 6. Suppression List & Compliance

### US-15 · Automatic Suppression
**As the** system, **I need to** suppress bounced and complained addresses **so that** we maintain sender reputation.

**Acceptance Criteria**
- [ ] Hard bounces automatically added to suppression list
- [ ] Spam complaints from ESP webhook automatically suppressed
- [ ] Suppression check runs before every email is queued
- [ ] Suppressed sends return `suppressed` status (not `failed`)

---

### US-16 · Unsubscribe Flow
**As a** recipient, **I want to** unsubscribe from emails **so that** I stop receiving them.

**Acceptance Criteria**
- [ ] `List-Unsubscribe` header added to every outgoing email
- [ ] Unsubscribe landing page at `/unsubscribe/<token>`
- [ ] One-click unsubscribe adds address to suppression list instantly
- [ ] User (sender) can view and manually remove addresses from suppression list

---

## 7. Message History & Analytics

### US-17 · Message History
**As a** user, **I want to** see a history of all sent messages **so that** I can troubleshoot delivery issues.

**Acceptance Criteria**
- [ ] Filterable list: date range, status, domain, stream
- [ ] Each row shows: recipient, subject, status, sent time
- [ ] Detail view shows full headers, body preview, and event timeline
- [ ] Pagination: 50 items per page

---

### US-18 · Analytics Dashboard
**As a** user, **I want to** see aggregated stats (sent, delivered, opened, clicked, bounced, complained) **so that** I can monitor my account's health.

**Acceptance Criteria**
- [ ] Overview page shows stats for last 7 / 30 / 90 days (selectable)
- [ ] Area/bar charts rendered via Chart.js or Recharts
- [ ] Stats updated within 60 seconds of an event occurring
- [ ] CSV export available for any date range

---

## 8. Webhooks

### US-19 · Configure Outbound Webhooks
**As a** developer, **I want to** register webhook URLs **so that** my system is notified of email events in real time.

**Acceptance Criteria**
- [ ] User adds URL + selects event types (delivered, opened, clicked, bounced, complained)
- [ ] Webhook secret generated; HMAC signature attached to every POST
- [ ] "Send test" button fires a sample payload to verify the endpoint
- [ ] Failed deliveries retried with exponential backoff (max 10 attempts)
- [ ] Dead-letter log shows failed dispatches

---

## 9. Dashboard — Postmark-Parity UI Features

### US-22 · Suppression List Dashboard Page
**As a** user, **I want to** view and manage my suppression list in the dashboard **so that** I can see who is blocked and why.

**Acceptance Criteria**
- [ ] Dedicated `/suppressions` page in the React dashboard with sidebar link
- [ ] Table columns: email address, reason (`bounce` / `complaint` / `unsubscribe`), suppressed date
- [ ] Filter by reason type; search by email address
- [ ] Clicking a suppressed address shows the originating message that caused it (if within retention window)
- [ ] "Remove" button per row calls `DELETE /api/v1/suppressions/` and removes the record (re-enables delivery)
- [ ] "Add manually" button allows entering an address to suppress with reason `manual`
- [ ] Count badge on sidebar link showing total suppressed addresses

---

### US-23 · Message Streams Dashboard Page
**As a** user, **I want to** view and manage my message streams in the dashboard **so that** I can monitor deliverability per stream.

**Acceptance Criteria**
- [ ] Dedicated `/streams` page with sidebar link
- [ ] List shows each stream: name, type (`transactional` / `promotional`), emails sent this month, bounce rate, complaint rate
- [ ] Bounce rate and complaint rate shown as colour-coded badges: green < 5% / < 0.05%, amber ≤ 10% / ≤ 0.1%, red > 10% / > 0.1%
- [ ] Create stream form: name, type, optional relay/IP pool selection
- [ ] Archive/delete stream with confirmation dialog
- [ ] Per-stream settings panel: open tracking toggle, click tracking toggle, webhook URL override

---

### US-24 · Message Detail & Event Timeline
**As a** user, **I want to** click any message in the history list and see its full detail **so that** I can debug delivery issues.

**Acceptance Criteria**
- [ ] Navigates to `/messages/:id` detail page
- [ ] Shows: `to_address`, `from_address`, `subject`, stream, domain, sent time, final status
- [ ] Full HTML body preview in sandboxed `<iframe>`; plain-text tab toggle
- [ ] Raw headers panel (collapsible)
- [ ] Ordered event timeline: each event shows icon, type label, timestamp, and metadata (IP address, user agent, URL clicked, bounce code + description)
- [ ] "Resend" button for `permanently_failed` messages only

---

### US-25 · Webhook Dispatch Log & Dead-Letter UI
**As a** developer, **I want to** see the delivery history and failure log for each webhook **so that** I can diagnose integration issues.

**Acceptance Criteria**
- [ ] Webhooks list page shows `is_active` status badge and `last_attempted_at` per webhook
- [ ] Each webhook has an expandable "Dispatch log" panel showing the last 20 `WebhookDispatchLog` entries: timestamp, HTTP status code, response body (truncated), attempt number
- [ ] Failed dispatches (non-2xx after all retries) highlighted in red; dead-letter count shown as badge
- [ ] "Retry now" button re-enqueues the dispatch task for the most recent failed payload
- [ ] "Disable" toggle deactivates the webhook without deleting it

---

### US-26 · Bounce & Complaint Rate Health Indicators
**As a** user, **I want to** see at-a-glance health indicators for bounce and complaint rates **so that** I am warned before my sending is at risk.

**Acceptance Criteria**
- [ ] Dashboard overview page includes a "Sending health" card alongside the existing 6 metric cards
- [ ] Card shows current bounce rate % and complaint rate % for the selected date range, per stream
- [ ] Colour coding: green (healthy), amber (warning), red (danger — matches Postmark's 10% / 0.1% thresholds)
- [ ] Red state shows an inline alert banner: "Your bounce rate is above the safe threshold. Review your suppression list."
- [ ] Rates computed from `DailyStats` (or raw `Event` table before 6.5C lands)

---

### US-27 · Team / Users Management Page
**As an** account owner, **I want to** invite team members and assign them roles **so that** colleagues can access the dashboard without sharing my credentials.

**Acceptance Criteria**
- [ ] `/settings/team` page accessible from Settings sidebar section
- [ ] Roles: `owner` (one per account), `admin` (full access except delete account / transfer ownership), `viewer` (read-only: stats, activity, suppression list)
- [ ] Owner can invite by email; invitation email sent with accept link (time-limited, 48 h TTL)
- [ ] Pending invitations shown with "Resend" and "Cancel" options
- [ ] Owner and admins can remove team members (cannot remove owner)
- [ ] Role displayed as badge on each row; owner can change a member's role
- [ ] `TeamMember` model: `ForeignKey(User)` account owner, `ForeignKey(User)` member, `role` CharField, `invited_at`, `accepted_at`

---

### US-28 · Per-Stream Analytics Breakdown
**As a** user, **I want to** filter analytics by stream **so that** I can compare transactional vs promotional performance independently.

**Acceptance Criteria**
- [ ] Analytics / Dashboard page gains a "Stream" filter dropdown alongside the existing date range selector
- [ ] All charts and metric cards respond to the stream filter
- [ ] "All streams" is the default option; selecting a specific stream re-fetches data scoped to that stream
- [ ] `GET /api/v1/stats/?stream=transactional&days=30` supported on the backend

---

## 10. Public Marketing Website

### US-20 · Landing Page
**As a** visitor, **I want to** understand the product quickly **so that** I decide to sign up.

**Acceptance Criteria**
- [ ] Hero section with headline and CTA buttons ("Start free trial", "API docs")
- [ ] Feature highlights: deliverability, separated streams, great support
- [ ] Customer testimonials carousel
- [ ] Company logos (social proof)
- [ ] Tabbed code examples: curl, Python, Node.js, Ruby, .NET, PHP
- [ ] Cookie consent banner (Performance, Functional, Targeting categories)

---

## 11. Billing & Plans

### US-21 · Plan & Usage Display
**As a** user, **I want to** see my current plan and usage **so that** I know when to upgrade.

**Acceptance Criteria**
- [ ] Billing page shows current plan, emails sent this month, limit
- [ ] Usage bar turns warning colour at 80% of limit
- [ ] Upgrade/downgrade links to payment provider (Stripe/Paddle)
- [ ] Invoice history accessible

---

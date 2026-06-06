# WebMail UI Improvement — Claude Code Prompt
> Paste this entire file into Claude Code to implement landing page and dashboard improvements.

---

## Project Context

You are working on **WebMail**, a Postmark-like transactional email delivery platform.

**Stack:**
- Backend: Django + Django REST Framework, Celery + Redis, PostgreSQL (SQLite in dev)
- Frontend: React (with React Router v6, React Query / `@tanstack/react-query`, Recharts, Tailwind CSS)
- API base: `/api/v1/` — Bearer token auth via API key
- Frontend root: `frontend/src/`

**Current frontend structure:**
```
frontend/src/
├── api/            # Axios client + per-resource modules (auth, domains, messages, stats, webhooks, suppressions)
├── pages/          # Dashboard.js, Messages.js, Domains.js, Templates.js, Analytics.js,
│                   # Webhooks.js, Suppressions.js, Billing.js, Settings.js, ApiKeys.js
├── components/
│   ├── common/     # Header, Sidebar, DataTable, Chart
│   ├── auth/       # LoginForm, SignupForm, TwoFactorSetup
│   ├── domains/    # DomainList, AddDomainForm, DnsRecordDisplay
│   ├── templates/  # TemplateList, TemplateEditor
│   └── webhooks/   # WebhookForm
├── hooks/          # useAuth, useApi
└── utils/          # formatters.js
```

**What is already complete:** Auth UI, Dashboard overview (6 metric cards + area chart + recent messages table), Domains page with DNS record display, Template editor with live preview, API Keys page.

**Design system already in use:** Tailwind CSS utility classes. No component library. Recharts for charts.

---

## Task Overview

Implement the following UI improvements across two surfaces:
1. **Landing page** (`web/templates/` — Django HTML + Tailwind, Alpine.js already in use)
2. **React dashboard** (`frontend/src/`)

Work through each section below in order. For each change, read the existing file first, then implement.

---

## Part 1 — Landing Page Improvements

### 1A. Hero Section Redesign
**File:** `web/templates/landing/index.html` (or equivalent landing template)

Redesign the hero section with a **split layout**:
- Left column (60% width): headline, subtext, two CTAs
- Right column (40% width): a dark-background code block showing the actual API send call

**Headline:** `"Your transactional emails, delivered."` (or read the existing one and improve it to follow this outcome-not-feature formula)

**Subtext:** One specific falsifiable trust signal — e.g. `"< 1s average delivery time. 99.9% uptime."` Keep it under 15 words.

**CTAs:**
- Primary (filled, high contrast): `"Start sending free"`
- Secondary (ghost/outline): `"Read the docs"`
- Never render two filled buttons side by side

**Code block (right column):**
```
Dark background (#0f1117 or similar), syntax-highlighted curl example:

curl -X POST https://api.webmail.io/v1/send \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "user@example.com",
    "from": "you@yourdomain.com",
    "subject": "Welcome",
    "html_body": "<h1>Hello!</h1>"
  }'

Followed by the response JSON:
{
  "message_id": "550e8400-e29b-41d4-a716",
  "status": "queued",
  "submitted_at": "2025-06-06T10:30:00Z"
}
```
Add a **Copy** button top-right of the code block. On click: copy content + change button label to "Copied!" for 2 seconds.

---

### 1B. Deliverability Stats Block
**File:** same landing template, after hero

Add a **social proof / stats bar** between the hero and the first feature section. Full-width, subtle background tint, containing three stats in a row:

| Stat | Label |
|---|---|
| 99.97% | Delivery rate |
| < 800ms | Avg. delivery time |
| 0.001% | Spam complaint rate |

Each stat: large bold number, small muted label below. These should be static (hardcoded). Separate each with a thin vertical divider. No animations needed.

---

### 1C. Feature Sections — Replace Icons with UI Screenshots
**File:** landing template feature sections

Current feature sections likely use abstract icons. Replace each icon placeholder with a **realistic UI mockup** of the relevant dashboard page, implemented as HTML/CSS (not images).

Implement mockups for these three features in priority order:

**Feature 1 — Separate Message Streams**
Mockup: a small diagram showing two lanes — "Transactional" and "Promotional" — each going to a separate IP badge. Use simple boxes and arrows in HTML/CSS. Label the transactional lane green, promotional lane blue.

**Feature 2 — Suppression & Compliance**
Mockup: a miniature table with 3 rows showing email addresses, a reason badge (HardBounce / Unsubscribe), and a date. Below it, a small `List-Unsubscribe` header snippet in monospace.

**Feature 3 — Real-time Event Tracking**
Mockup: a vertical timeline with 4 events — Queued → Sent → Delivered → Opened — each with a coloured dot, label, and timestamp. Green dots for positive events.

Each feature section layout: heading left, mockup right (alternate on every other section for visual rhythm).

---

### 1D. Code Integration Tabs — Improvements
**File:** landing template code tabs section (Alpine.js powered, already exists)

Make these improvements to the existing tabs:
1. Ensure the active tab has a distinct underline or filled indicator — not just a colour change
2. Add the **response JSON block** beneath each request example, separated by a thin divider labelled "Response"
3. Ensure each code block has a **Copy button** (top-right) with the same "Copied!" confirmation as 1A
4. If not already present, add **PHP** and **.NET** tabs

---

### 1E. Pricing Section — Usage Calculator
**File:** landing template pricing section

Add a **usage calculator** above or below the existing pricing tiers:

```
Interactive slider: "I send _____ emails per month"
Range: 1,000 – 500,000 (log scale recommended)

As slider moves, highlight the matching plan tier and show:
"You'd be on the [Startup] plan — $[X]/month"
```

Implement with Alpine.js (`x-data`, `x-model`, `x-text`). The calculation logic:
- 0–10,000 emails → Free plan ($0)
- 10,001–100,000 emails → Startup plan ($25)
- 100,001–500,000 emails → Growth plan ($75)
- 500,001+ emails → Enterprise (show "Contact us")

---

### 1F. Footer Additions
**File:** landing template footer

Ensure the footer contains these links (add any missing):
- API Docs (`/api/docs/`)
- Status Page (`/status/` — placeholder is fine)
- GitHub (placeholder `#` if not open source)
- Privacy Policy
- Terms of Service
- Data Processing Agreement (DPA) — even a placeholder page
- `© 2025 WebMail. Built for developers.`

---

## Part 2 — React Dashboard Improvements

### 2A. Sidebar — Live Count Badges
**File:** `frontend/src/components/common/Sidebar.js` (or equivalent)

Add live count badges to these two sidebar links:
- **Suppressions** — fetch count from `GET /api/v1/suppressions/?limit=1` and read the `count` field from the paginated response. Display as a grey pill badge (e.g. `847`).
- **Webhooks** — fetch `GET /api/v1/webhooks/` and count entries where `last_dispatch_failed === true` (or equivalent field). Display as a red pill badge only when count > 0.

Use React Query (`useQuery`) for both fetches. Refetch every 60 seconds (`refetchInterval: 60000`). If fetch fails, show no badge (fail silently).

Sidebar grouping — ensure items are in two visual groups separated by a thin `<hr>` divider:
- **Sending:** Dashboard, Messages, Streams, Templates
- **Config:** Domains, Webhooks, Suppressions, API Keys, Settings

---

### 2B. Dashboard Overview — Sending Health Card
**File:** `frontend/src/pages/Dashboard.js`

Add a **Sending Health card** as a 7th card in the metrics row (or as a wider card below the 6-card row if layout is 3×2).

Card content:
- Title: `"Sending Health"`
- Two metrics side by side: **Bounce Rate** `X.XX%` and **Complaint Rate** `X.XXX%`
- Colour coding via left border or background tint:
  - Green: bounce < 5% AND complaint < 0.05%
  - Amber: bounce ≤ 10% OR complaint ≤ 0.1%
  - Red: bounce > 10% OR complaint > 0.1%

When red: render an `AlertBanner` component directly below the metrics card row:
```jsx
<AlertBanner type="error">
  Your bounce rate exceeds the safe threshold (10%). 
  <a href="/suppressions">Review your suppression list →</a>
</AlertBanner>
```

Fetch data from `GET /api/v1/stats/?days=<selectedRange>`. Compute:
```js
bounceRate = (stats.bounced / stats.sent) * 100
complaintRate = (stats.complained / stats.sent) * 100
```

Make each metric card a `<Link>` to its relevant page:
- Sent → `/messages`
- Bounced → `/messages?status=bounced`
- Suppressions → `/suppressions`
- (other cards → appropriate filtered routes)

---

### 2C. Dashboard Chart — Multi-metric Tooltip
**File:** `frontend/src/pages/Dashboard.js` (Recharts AreaChart)

Replace the default Recharts tooltip with a custom tooltip component that shows **all four metrics at once** for a hovered date:

```jsx
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-medium text-gray-700 mb-2">{label}</p>
      {payload.map(entry => (
        <div key={entry.name} className="flex items-center gap-2 text-gray-600">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="capitalize">{entry.name}:</span>
          <span className="font-medium text-gray-900">{entry.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
};
```

Pass it to the chart: `<Tooltip content={<CustomTooltip />} />`

---

### 2D. Messages List — UX Improvements
**File:** `frontend/src/pages/Messages.js`

Make these changes:

**Status badges** — ensure every status uses colour + text + dot, never colour alone:
```jsx
const statusConfig = {
  delivered: { color: 'bg-green-100 text-green-800', dot: 'bg-green-500', label: 'Delivered' },
  bounced:   { color: 'bg-red-100 text-red-800',   dot: 'bg-red-500',   label: 'Bounced'   },
  queued:    { color: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500', label: 'Queued' },
  failed:    { color: 'bg-red-100 text-red-800',   dot: 'bg-red-500',   label: 'Failed'    },
  suppressed:{ color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400',  label: 'Suppressed'},
  sent:      { color: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500',  label: 'Sent'      },
};
```

**Row click target** — make the entire `<tr>` clickable to navigate to `/messages/:id`. Apply `cursor-pointer` and `hover:bg-gray-50` to each row.

**Filter persistence** — when a user applies a status filter, navigates to a message detail, and hits back, the filter should be restored. Implement by syncing filters to URL query params (`?status=bounced&domain=example.com`) using React Router's `useSearchParams`.

---

### 2E. Message Detail Page
**File:** create `frontend/src/pages/MessageDetail.js` + register route `/messages/:id` in `App.js`

Fetch from `GET /api/v1/messages/:id`.

**Layout:**
```
[Back to Messages]

┌─────────────────────────────────────────────────┐
│ Subject line                    [Status badge]   │
│ To: recipient@example.com                        │
│ From: sender@domain.com                          │
│ Stream: transactional · Domain: domain.com       │
│ Sent: June 6, 2025 at 10:30 AM                  │
└─────────────────────────────────────────────────┘

[HTML Preview] [Plain Text] [Raw Headers]   ← tab bar

┌─────────────────────────────────────────────────┐
│  <iframe srcDoc={htmlBody} sandbox="allow-same-origin" │
│   style={{ width: '100%', height: 400 }}         │
│  />                                              │
└─────────────────────────────────────────────────┘

Event Timeline
──────────────
● Queued       Jun 6, 10:30:00 AM
● Sent         Jun 6, 10:30:01 AM
● Delivered    Jun 6, 10:30:02 AM    via SES
● Opened       Jun 6, 10:35:14 AM    IP: 102.x.x.x · Chrome/Windows
● Clicked      Jun 6, 10:36:02 AM    https://example.com/welcome
                                      IP: 102.x.x.x

[Resend]  ← only visible when status === 'permanently_failed'
```

**Event timeline implementation:**
```jsx
const eventIcons = {
  delivered:   '✓',  // green
  open:        '👁',
  click:       '🔗',
  bounce:      '✕',  // red
  complaint:   '⚠',
  unsubscribe: '○',
};
```

For bounce events: show the raw SMTP code from `event.metadata.bounce_code` AND a plain-English explanation below it in muted text. E.g.: `550 5.1.1` → `"This address doesn't exist. It has been added to your suppression list automatically."`

Bounce code plain-English map (implement as a const lookup):
```js
const bounceExplanations = {
  '550': 'The recipient address was rejected by the server.',
  '551': 'The recipient is not local; the server cannot forward.',
  '552': 'The recipient\'s mailbox has exceeded its storage limit.',
  '553': 'The recipient address is not allowed by server policy.',
  '554': 'The message was rejected for policy reasons.',
};
```

---

### 2F. Suppressions Page
**File:** `frontend/src/pages/Suppressions.js`

The page likely exists but needs these improvements:

**Reason badges** — four distinct styles:
```jsx
const reasonBadge = {
  bounce:      'bg-red-100 text-red-700 border border-red-200',
  complaint:   'bg-orange-100 text-orange-700 border border-orange-200',
  unsubscribe: 'bg-gray-100 text-gray-600 border border-gray-200',
  manual:      'bg-blue-100 text-blue-700 border border-blue-200',
};
```

**Instant search** — add a search input that filters the displayed rows client-side (if list < 500 rows) or calls `GET /api/v1/suppressions/?email=<query>` debounced at 300ms (if paginated server-side).

**Remove confirmation** — inline, not a modal. When user clicks Remove, replace the row's action cell with:
```
"Re-enable delivery to this address?"  [Confirm]  [Cancel]
```
On Confirm: call `DELETE /api/v1/suppressions/` with `{ email }`, remove the row from the list optimistically.

**Manual add button** — top-right of page, opens a small inline form (not a modal):
```
Email: [________________]  Reason: [Manual ▾]  [Add]
```
On submit: call `POST /api/v1/suppressions/` with `{ email, reason: 'manual' }`.

**Empty state:**
```jsx
<EmptyState
  icon="✓"
  title="No suppressed addresses"
  description="Your sending reputation looks healthy. Addresses suppressed due to bounces or complaints will appear here."
/>
```

---

### 2G. Webhooks Page — Dispatch Log
**File:** `frontend/src/pages/Webhooks.js`

Add to each webhook row:
- `is_active` badge: green `Active` or grey `Inactive`
- `last_attempted_at` in relative time ("3 minutes ago") — use a `formatRelative(date)` utility
- Dead-letter count badge (red) when failed dispatch count > 0

Add an expandable **Dispatch Log panel** per webhook (toggle on row click or a "Show log" button):

```jsx
// Fetch from GET /api/v1/webhooks/:id/logs/
// Show last 20 WebhookDispatchLog entries

<div className="font-mono text-xs bg-gray-950 text-gray-300 rounded-lg p-4 space-y-2">
  {logs.map(log => (
    <div key={log.id} className="flex gap-4">
      <span className="text-gray-500 w-36 shrink-0">{formatRelative(log.attempted_at)}</span>
      <span className={log.status_code >= 200 && log.status_code < 300
        ? 'text-green-400' : 'text-red-400'}>
        {log.status_code}
      </span>
      <span className="text-gray-400 truncate">{log.response_body?.slice(0, 120)}</span>
      <span className="text-gray-600 shrink-0">attempt {log.attempt_number}</span>
    </div>
  ))}
</div>
```

Add **Retry** button (calls `POST /api/v1/webhooks/:id/retry/`) and **Disable** toggle (calls `PATCH /api/v1/webhooks/:id/` with `{ is_active: false }`).

---

### 2H. Analytics — Stream Filter
**Files:** `frontend/src/pages/Dashboard.js`, `frontend/src/pages/Analytics.js`

Add a **Stream** dropdown alongside the existing date range selector on both pages:

```jsx
<select value={selectedStream} onChange={e => setSelectedStream(e.target.value)}>
  <option value="">All streams</option>
  {streams.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
</select>
```

Fetch streams from `GET /api/v1/streams/`. When a stream is selected, append `&stream=<id>` to the stats fetch URL. All charts and metric cards must respond to both filters together.

---

### 2I. Empty States — All List Pages
**File:** create `frontend/src/components/common/EmptyState.js`, then apply to all list pages

```jsx
// EmptyState.js
export default function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <span className="text-4xl mb-4">{icon}</span>
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-500 max-w-sm mb-6">{description}</p>
      {action}
    </div>
  );
}
```

Apply to each page with contextual content:

| Page | Icon | Title | Description | Action |
|---|---|---|---|---|
| Messages (no results) | `📭` | "No messages yet" | "Send your first email using the API and it will appear here." | Code snippet: curl example |
| Suppressions (empty) | `✓` | "No suppressed addresses" | "Your sending reputation looks healthy." | None |
| Webhooks (none) | `🔗` | "No webhooks configured" | "Add a webhook URL to receive real-time event notifications." | "Add webhook" button |
| Domains (none) | `🌐` | "No domains added" | "Add a sending domain to start delivering emails from your own address." | "Add domain" button |

---

### 2J. Typography & Colour Consistency
**File:** `frontend/src/index.css` or Tailwind config

Ensure these are applied globally:

**Font rule:** All email addresses, API keys, message IDs, status codes, and token values rendered in `font-mono`. Apply via a utility class or a CSS rule:
```css
.data-value {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.875em;
}
```

**Colour rule:** Red (`text-red-*`, `bg-red-*`) must only appear for: error states, bounce events, high complaint rates, failed webhook dispatches, destructive action confirmations. Audit all pages and remove red from any decorative use.

**Background:** Ensure page background is `bg-gray-50` (not pure white `#ffffff`) for the dashboard shell. Card backgrounds remain `bg-white` with `shadow-sm border border-gray-100`.

---

## Shared Utilities to Create/Update

### AlertBanner component
**File:** create `frontend/src/components/common/AlertBanner.js`
```jsx
export default function AlertBanner({ type = 'info', children }) {
  const styles = {
    info:    'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    error:   'bg-red-50 border-red-200 text-red-800',
  };
  return (
    <div className={`border rounded-lg px-4 py-3 text-sm ${styles[type]}`}>
      {children}
    </div>
  );
}
```

### formatRelative utility
**File:** `frontend/src/utils/formatters.js` — add:
```js
export function formatRelative(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days > 1 ? 's' : ''} ago`;
}
```

---

## Implementation Order

Work through tasks in this sequence to avoid blocking dependencies:

1. **2J** — typography/colour baseline (affects everything)
2. **2I** — EmptyState component (needed by list pages)
3. **AlertBanner** + **formatRelative** utilities
4. **2A** — Sidebar badges
5. **2B** — Dashboard health card + AlertBanner wiring
6. **2C** — Chart tooltip
7. **2D** — Messages list improvements
8. **2E** — MessageDetail page (new)
9. **2F** — Suppressions page improvements
10. **2G** — Webhooks dispatch log
11. **2H** — Stream filter on analytics
12. **1A** → **1F** — Landing page (independent of React work)

After each file change, confirm there are no console errors and the page renders correctly before moving to the next.

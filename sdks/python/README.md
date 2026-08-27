# webmail-sdk

Official Python client for the [WebMail](https://webmailapi.com) transactional email API.

## Install

```bash
pip install webmail-sdk
```

## Quickstart

```python
from webmail_sdk import WebMail

client = WebMail(api_key="sk_live_...")  # or set WEBMAIL_API_KEY

client.emails.send(
    to="user@example.com",
    from_address="noreply@yourdomain.com",
    subject="Welcome!",
    html_body="<p>Hi there</p>",
)
```

## Idempotent sends

Pass `idempotency_key=` to safely retry a send without risking a duplicate email.
Replaying the same key within 24h returns the original response; reusing it with
a different request body raises `ConflictError`.

```python
client.emails.send(
    to="user@example.com",
    from_address="noreply@yourdomain.com",
    subject="Your receipt",
    html_body="<p>Thanks for your order</p>",
    idempotency_key="order-4471-receipt",
)
```

## Attachments

```python
from webmail_sdk import Attachment

client.emails.send(
    to="user@example.com",
    from_address="noreply@yourdomain.com",
    subject="Your invoice",
    html_body="<p>Attached.</p>",
    attachments=[Attachment.from_file("invoice.pdf")],
)
```

## Batch sending

```python
client.emails.send_batch([
    {"to": "a@example.com", "from_address": "noreply@yourdomain.com", "subject": "Hi", "html_body": "<p>1</p>"},
    {"to": "b@example.com", "from_address": "noreply@yourdomain.com", "subject": "Hi", "html_body": "<p>2</p>"},
])
```

## Pagination

`domains.list()`, `messages.list()`, `templates.list()`, and `streams.list()` are
server-paginated (50 per page). Pass `page=2` etc. to fetch further pages; each
call returns that page's items as a plain list.

## Resources

| Namespace              | Covers                                                   |
|-------------------------|-----------------------------------------------------------|
| `client.emails`         | `send`, `send_batch`                                       |
| `client.messages`       | `list`, `get`, `resend`, `cancel_schedule`                 |
| `client.domains`        | `list`, `create`, `get`, `delete`, `verify`, `generate_dkim`, `verified` |
| `client.templates`      | `list`, `create`, `get`, `update`, `delete`, `versions`, `create_version`, `render_preview` |
| `client.webhooks`       | `list`, `create`, `get`, `update`, `delete`, `test`, `logs`, `retry` |
| `client.suppressions`   | `list`, `add`, `remove`, `remove_bulk`, `export_csv`        |
| `client.streams`        | `list`, `create`, `get`, `update`, `delete`                |
| `client.stats`          | `get`, `export_csv`                                        |

## Errors

Every non-2xx response raises a subclass of `WebMailError`:

```python
from webmail_sdk import WebMail, ValidationError, RateLimitError, PaymentRequiredError

try:
    client.emails.send(...)
except ValidationError as e:
    print(e.message, e.body)
except PaymentRequiredError:
    print("monthly quota exceeded")
except RateLimitError as e:
    print("retry after", e.retry_after, "seconds")
```

| Status | Exception               |
|--------|--------------------------|
| 400/422| `ValidationError`        |
| 401    | `AuthenticationError`    |
| 402    | `PaymentRequiredError`   |
| 403    | `ForbiddenError`         |
| 404    | `NotFoundError`          |
| 409    | `ConflictError`          |
| 429    | `RateLimitError`         |
| 5xx    | `APIError`               |

## Development

```bash
cd sdks/python
pip install -e ".[dev]"
pytest
```

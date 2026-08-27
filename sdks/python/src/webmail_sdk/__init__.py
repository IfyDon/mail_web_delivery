"""Official Python client for the WebMail transactional email API."""
from .attachments import Attachment
from .client import WebMail
from .exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PaymentRequiredError,
    RateLimitError,
    ValidationError,
    WebMailError,
)

__version__ = "0.1.0"

__all__ = [
    "WebMail",
    "Attachment",
    "WebMailError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "PaymentRequiredError",
    "ConflictError",
    "RateLimitError",
    "APIError",
]

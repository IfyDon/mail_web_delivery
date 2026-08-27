"""Shared base class for resource namespaces (client.emails, client.domains, ...)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import WebMail


class Resource:
    def __init__(self, client: "WebMail"):
        self._client = client

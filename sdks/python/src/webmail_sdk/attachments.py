"""Helpers for building the base64 attachment payloads /send expects."""
from __future__ import annotations

import base64
import mimetypes
import os
from dataclasses import dataclass


@dataclass
class Attachment:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"

    @classmethod
    def from_file(cls, path: str, *, filename: str | None = None, content_type: str | None = None) -> "Attachment":
        """Read a local file and wrap it as an Attachment."""
        with open(path, "rb") as f:
            data = f.read()
        return cls(
            filename=filename or os.path.basename(path),
            content=data,
            content_type=content_type or mimetypes.guess_type(path)[0] or "application/octet-stream",
        )

    @classmethod
    def from_bytes(cls, data: bytes, filename: str, content_type: str = "application/octet-stream") -> "Attachment":
        return cls(filename=filename, content=data, content_type=content_type)

    def to_payload(self) -> dict:
        """Serialize to the {filename, content_type, content} shape the API expects."""
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "content": base64.b64encode(self.content).decode("ascii"),
        }

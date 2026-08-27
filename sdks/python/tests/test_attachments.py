import base64
import os

from webmail_sdk import Attachment


def test_from_bytes_to_payload():
    att = Attachment.from_bytes(b"data", "f.txt", "text/plain")
    payload = att.to_payload()
    assert payload["filename"] == "f.txt"
    assert payload["content_type"] == "text/plain"
    assert base64.b64decode(payload["content"]) == b"data"


def test_from_file_guesses_content_type(tmp_path):
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    att = Attachment.from_file(str(p))
    assert att.filename == "report.pdf"
    assert att.content_type == "application/pdf"
    assert att.content == b"%PDF-1.4 fake"


def test_from_file_filename_override(tmp_path):
    p = tmp_path / "raw.bin"
    p.write_bytes(b"x")
    att = Attachment.from_file(str(p), filename="custom.bin", content_type="application/custom")
    assert att.filename == "custom.bin"
    assert att.content_type == "application/custom"

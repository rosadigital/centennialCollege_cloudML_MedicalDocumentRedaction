import base64

from app.main import app
from fastapi.testclient import TestClient


def test_health() -> None:
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_sync_process_text() -> None:
    with TestClient(app) as client:
        files = {"file": ("note.txt", b"Patient email: x@y.com", "text/plain")}
        data = {"document_type": "text"}
        r = client.post(
            "/api/v1/process/sync",
            files=files,
            data=data,
        )
        assert r.status_code == 200
        payload = r.json()
        assert "result" in payload
        redacted = base64.standard_b64decode(payload["redacted_base64"]).decode("utf-8")
        assert "x@y.com" not in redacted
        assert "[REDACTED]" in redacted

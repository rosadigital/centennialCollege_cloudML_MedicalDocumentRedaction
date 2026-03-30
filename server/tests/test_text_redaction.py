from app.models.job import EntityRecord
from app.services.redaction.text import redact_text


def test_redact_text_replaces_spans() -> None:
    text = "Email test@example.com and phone 416-555-0100"
    email = "test@example.com"
    phone = "416-555-0100"
    es, ee = text.index(email), text.index(email) + len(email)
    ps, pe = text.index(phone), text.index(phone) + len(phone)
    entities = [
        EntityRecord(
            type="EMAIL",
            confidence=0.99,
            start=es,
            end=ee,
            page=None,
            source="x",
        ),
        EntityRecord(
            type="PHONE",
            confidence=0.95,
            start=ps,
            end=pe,
            page=None,
            source="x",
        ),
    ]
    out = redact_text(text, entities, "[REDACTED]")
    assert "example.com" not in out
    assert "416-555-0100" not in out
    assert out.count("[REDACTED]") == 2

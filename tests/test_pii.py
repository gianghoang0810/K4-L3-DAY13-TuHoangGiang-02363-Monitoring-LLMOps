from app.pii import scrub_text
import pytest


@pytest.mark.parametrize("raw,kind", [
    ("student+lab@example.com", "EMAIL"),
    ("001092001234", "CCCD"),
    ("0123456789012345", "CREDIT_CARD"),
    ("0123 4567 8901 2345", "CREDIT_CARD"),
    ("0123-4567-8901-2345", "CREDIT_CARD"),
])
def test_complete_redaction(raw, kind):
    assert scrub_text(f"Value: {raw}!") == f"Value: [REDACTED_{kind}]!"


def test_scrubbing_preserves_non_pii():
    text = "req-abc123ef latency_ms=125 model=claude-sonnet-4-5"
    assert scrub_text(text) == text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out

import json

import structlog

from app import logging_config
from app.logging_config import JsonlFileProcessor, scrub_event
from app.pii import scrub_text


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


def test_scrub_cccd() -> None:
    out = scrub_text("CCCD 001234567890 cua toi")
    assert "001234567890" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card_grouped_and_contiguous() -> None:
    for card in ("4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111"):
        out = scrub_text(f"Thanh toan bang the {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport_vn() -> None:
    out = scrub_text("Ho chieu B1234567 con han")
    assert "B1234567" not in out
    assert "REDACTED_PASSPORT_VN" in out


def test_scrub_cmnd_nine_digits() -> None:
    out = scrub_text("CMND 123456789 cap tai Ha Noi")
    assert "123456789" not in out
    assert "REDACTED_CMND" in out


def test_scrub_date_of_birth() -> None:
    for dob in ("15/03/1999", "15-03-1999"):
        out = scrub_text(f"Ngay sinh {dob}")
        assert dob not in out
        assert "REDACTED_DOB" in out


def test_scrub_vietnamese_address_keywords() -> None:
    addresses = (
        "đường Láng số 12",
        "số nhà 25 phố Huế",
        "quận Ba Đình",
    )

    for address in addresses:
        out = scrub_text(f"Dia chi: {address}")
        assert address not in out
        assert "REDACTED_ADDRESS_VN" in out


def test_email_is_scrubbed_before_number_patterns() -> None:
    """Thứ tự pattern: nếu phone_vn chạy trước email thì tên miền vẫn lộ."""
    out = scrub_text("mail user0901234567@example.com")
    assert "example.com" not in out
    assert out == "mail [REDACTED_EMAIL]"


def test_scrub_keeps_non_pii_log_fields_intact() -> None:
    """Các field kỹ thuật không được dính false positive, nếu không log mất giá trị debug."""
    safe_values = (
        "2026-08-11T09:54:19.123456Z",
        "req-1a2b3c4d",
        "claude-sonnet-4-5",
        "response_sent",
        "session-01",
        "abc123def456",
        "1470.6ms",
        "0.000123",
    )

    for value in safe_values:
        assert scrub_text(value) == value


def test_scrub_event_covers_every_field_not_only_payload() -> None:
    """validate_logs.py quét cả record sau json.dumps nên mọi field đều phải sạch."""
    event = {
        "event": "request_failed",
        "error_detail": "khong tim thay student@vinuni.edu.vn",
        "payload": {
            "nested": {"note": "goi 0987654321"},
            "items": ["the 4111111111111111"],
        },
    }

    raw = json.dumps(scrub_event(None, "error", event), ensure_ascii=False)

    assert "student@vinuni.edu.vn" not in raw
    assert "0987654321" not in raw
    assert "4111111111111111" not in raw


def test_scrub_event_runs_before_the_file_writer() -> None:
    """Bug gốc của lab: scrub_event không được đăng ký nên log ghi ra nguyên văn PII."""
    logging_config.configure_logging()
    processors = structlog.get_config()["processors"]

    assert scrub_event in processors
    writer_index = next(
        index
        for index, processor in enumerate(processors)
        if isinstance(processor, JsonlFileProcessor)
    )
    assert processors.index(scrub_event) < writer_index

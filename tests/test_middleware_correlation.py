"""Tests cho phần Thành viên A: correlation ID middleware + exception handler."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import logging_config, main
from app.main import app
from app.middleware import REQUEST_ID_HEADER, RESPONSE_TIME_HEADER, resolve_correlation_id

CORRELATION_ID_FORMAT = re.compile(r"^req-[0-9a-f]{8}$")


def read_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture
def log_path(monkeypatch, tmp_path: Path) -> Path:
    path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", path)
    return path


def chat_payload(**overrides) -> dict:
    payload = {
        "user_id": "student-01",
        "session_id": "session-01",
        "feature": "qa",
        "message": "Explain observability",
    }
    payload.update(overrides)
    return payload


def test_generated_correlation_id_uses_req_hex8_format(log_path: Path) -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json=chat_payload())

    assert response.status_code == 200
    correlation_id = response.json()["correlation_id"]
    assert CORRELATION_ID_FORMAT.match(correlation_id), correlation_id
    assert response.headers[REQUEST_ID_HEADER] == correlation_id
    assert int(response.headers[RESPONSE_TIME_HEADER]) >= 0


def test_incoming_request_id_is_reused(log_path: Path) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat", json=chat_payload(), headers={REQUEST_ID_HEADER: "upstream-abc123"}
        )

    assert response.json()["correlation_id"] == "upstream-abc123"
    assert response.headers[REQUEST_ID_HEADER] == "upstream-abc123"


@pytest.mark.parametrize(
    "unsafe",
    ["", " ", 'x" injected="1', "a" * 65, "id with space", "line\nbreak"],
)
def test_unsafe_incoming_request_id_is_rejected(unsafe: str) -> None:
    assert CORRELATION_ID_FORMAT.match(resolve_correlation_id(unsafe))


def test_correlation_id_is_unique_per_request_and_context_does_not_leak(
    log_path: Path,
) -> None:
    with TestClient(app) as client:
        first = client.post("/chat", json=chat_payload(session_id="s-1")).json()
        second = client.post("/chat", json=chat_payload(session_id="s-2")).json()

    assert first["correlation_id"] != second["correlation_id"]

    events = read_events(log_path)
    api_events = [event for event in events if event.get("service") == "api"]
    assert api_events, "no api events written"
    for event in api_events:
        assert event["correlation_id"] in {first["correlation_id"], second["correlation_id"]}
        assert event["session_id"] in {"s-1", "s-2"}

    # Access log của middleware phải mang đúng correlation ID của request đó.
    http_events = [event for event in events if event.get("service") == "http"]
    assert len(http_events) == 2
    assert {event["correlation_id"] for event in http_events} == {
        first["correlation_id"],
        second["correlation_id"],
    }


def test_api_logs_carry_enrichment_fields(log_path: Path) -> None:
    with TestClient(app) as client:
        client.post("/chat", json=chat_payload())

    api_events = [event for event in read_events(log_path) if event.get("service") == "api"]
    required = {"correlation_id", "user_id_hash", "session_id", "feature", "model", "env"}
    for event in api_events:
        assert required.issubset(event.keys()), sorted(required - set(event.keys()))
        assert event["user_id_hash"] != "student-01"


def test_access_log_is_not_service_api(log_path: Path) -> None:
    """Log tầng HTTP không được mang service=api, nếu không validator sẽ báo
    thiếu enrichment cho các request không có user context (/health, 422)."""
    with TestClient(app) as client:
        client.get("/health")

    events = read_events(log_path)
    completed = [event for event in events if event["event"] == "http_request_completed"]
    assert completed and all(event["service"] == "http" for event in completed)
    assert completed[-1]["payload"]["status_code"] == 200
    assert completed[-1]["payload"]["path"] == "/health"


def test_service_api_events_always_have_enrichment(log_path: Path) -> None:
    """Điều kiện validate_logs.py chấm: mọi record service=api phải đủ enrichment."""
    required = {"user_id_hash", "session_id", "feature", "model"}
    with TestClient(app) as client:
        client.get("/health")
        client.post("/chat", json=chat_payload())
        client.post("/chat", json={"user_id": "u1"})  # 422
        client.post("/incidents/khong-ton-tai/enable")  # 404

    for event in read_events(log_path):
        if event.get("service") == "api":
            assert required.issubset(event.keys()), event["event"]
            assert event.get("correlation_id") not in (None, "MISSING")


def test_agent_failure_returns_500_with_correlation_id(monkeypatch, log_path: Path) -> None:
    def boom(**_: object) -> None:
        raise RuntimeError("Vector store timeout")

    monkeypatch.setattr(main.agent, "run", boom)

    with TestClient(app) as client:
        response = client.post("/chat", json=chat_payload())

    assert response.status_code == 500
    assert response.json()["detail"] == "RuntimeError"
    assert CORRELATION_ID_FORMAT.match(response.headers[REQUEST_ID_HEADER])

    events = read_events(log_path)
    failed = next(event for event in events if event["event"] == "request_failed")
    assert failed["error_type"] == "RuntimeError"
    assert failed["correlation_id"] == response.headers[REQUEST_ID_HEADER]

    handled = next(event for event in events if event["event"] == "http_exception")
    assert handled["service"] == "http"
    assert handled["payload"]["status_code"] == 500

    completed = next(event for event in events if event["event"] == "http_request_completed")
    assert completed["payload"]["status_code"] == 500


def test_validation_error_is_logged_and_returns_422(log_path: Path) -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json={"user_id": "u1"})

    assert response.status_code == 422
    assert CORRELATION_ID_FORMAT.match(response.headers[REQUEST_ID_HEADER])

    events = read_events(log_path)
    validation = next(event for event in events if event["event"] == "request_validation_failed")
    assert validation["service"] == "http"
    assert validation["error_type"] == "ValidationError"
    assert validation["correlation_id"] == response.headers[REQUEST_ID_HEADER]
    assert {"body.session_id", "body.message"} <= {
        item["loc"] for item in validation["payload"]["detail"]
    }

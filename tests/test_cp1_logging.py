import asyncio
import json
import re

import httpx
from structlog.contextvars import bind_contextvars, clear_contextvars

from app import logging_config
from app.main import app, agent
from app.pii import hash_user_id


def test_request_context_isolation_and_headers(monkeypatch, tmp_path):
    log_path = tmp_path / "requests.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_requests():
        bind_contextvars(stale_context="must-not-leak")
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                async def send(index):
                    return await client.post(
                        "/chat",
                        headers={"x-request-id": "req-client"} if index == 0 else {},
                        json={"user_id": f"user-{index}", "session_id": f"session-{index}",
                              "feature": "qa", "message": "Explain logging"},
                    )
                return await asyncio.gather(send(0), send(1))
        finally:
            clear_contextvars()

    responses = asyncio.run(send_requests())
    ids = [response.json()["correlation_id"] for response in responses]
    assert ids[0] == "req-client"
    assert re.fullmatch(r"req-[0-9a-f]{8}", ids[1])
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    for index, response in enumerate(responses):
        assert response.status_code == 200
        assert response.headers["x-request-id"] == ids[index]
        assert float(response.headers["x-response-time-ms"]) >= 0
        request_events = [event for event in events if event.get("correlation_id") == ids[index]]
        assert {event["event"] for event in request_events} >= {"request_received", "response_sent"}
        for event in request_events:
            assert "stale_context" not in event
            assert event["user_id_hash"] == hash_user_id(f"user-{index}")
            assert event["session_id"] == f"session-{index}"
            assert event["feature"] == "qa"
            assert event["model"] == agent.model
            assert "env" in event


def test_scrubbing_precedes_file_and_console_output(monkeypatch, tmp_path, capsys):
    log_path = tmp_path / "scrubbed.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    try:
        raise ValueError("student@example.com")
    except ValueError:
        logging_config.get_logger().exception(
            "pii_probe", contact="student@example.com",
            payload={"nested": [{"phone": "090 123 4567", "cccd": "001092001234"}],
                     "card": "0123 4567 8901 2345", "count": 2},
        )
    captured = capsys.readouterr()
    for output in (log_path.read_text(encoding="utf-8"), captured.out + captured.err):
        for raw in ("student@example.com", "090 123 4567", "001092001234", "0123 4567 8901 2345"):
            assert raw not in output
        for kind in ("EMAIL", "PHONE_VN", "CCCD", "CREDIT_CARD"):
            assert f"[REDACTED_{kind}]" in output
    assert json.loads(log_path.read_text(encoding="utf-8"))["payload"]["count"] == 2

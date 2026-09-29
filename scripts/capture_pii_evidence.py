"""Capture four real /chat requests with synthetic PII, saving only scrubbed logs.

Run without .env/Cloud credentials. The synthetic input fixtures are defined here
so the input-to-output mapping is reproducible without raw PII in evidence.
"""
import asyncio
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
os.environ.pop("LANGFUSE_SECRET_KEY", None)

import httpx
from app import logging_config
from app.main import app

# Synthetic fixtures only; never use real contact, identity or payment data.
CASES = {
    "EMAIL": "student@example.com",
    "PHONE_VN": "0901234567",
    "CCCD": "001092001234",
    "CREDIT_CARD": "4532-1111-2222-3333",
}


async def capture():
    cases = []
    with TemporaryDirectory(prefix="day13-pii-") as temp:
        logging_config.LOG_PATH = Path(temp) / "runtime.jsonl"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://lab"
        ) as client:
            for kind, raw in CASES.items():
                message = f"{raw}. Explain monitoring."
                response = await client.post("/chat", json={
                    "user_id": "synthetic-pii-demo",
                    "session_id": "cp4-pii-" + kind.lower(),
                    "feature": "qa", "message": message,
                })
                response.raise_for_status()
                cid = response.json()["correlation_id"]
                records = [json.loads(line) for line in logging_config.LOG_PATH.read_text(
                    encoding="utf-8").splitlines()]
                events = [r for r in records if r.get("correlation_id") == cid]
                request = next(r for r in events if r["event"] == "request_received")
                assert any(r["event"] == "response_sent" for r in events)
                assert f"[REDACTED_{kind}]" in request["payload"]["message_preview"]
                assert not request["payload"]["message_preview"].endswith("...")
                assert all(value not in json.dumps(events) for value in CASES.values())
                cases.append({
                    "synthetic_input_fixture": f"scripts/capture_pii_evidence.py::CASES[{kind}]",
                    "input_template": "{synthetic fixture}. Explain monitoring.",
                    "pii_type": kind, "http_status": response.status_code,
                    "correlation_id": cid, "output_events": events,
                    "full_marker_present": True, "raw_fixture_absent": True,
                })
    return cases


def main():
    console = io.StringIO()
    with redirect_stdout(console):
        cases = asyncio.run(capture())
    assert all(raw not in console.getvalue() for raw in CASES.values())
    source_commit = subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT, text=True,
    ).strip()
    result = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_source_commit": source_commit,
        "command": "python scripts/capture_pii_evidence.py",
        "transport": "httpx ASGITransport -> real FastAPI /chat -> configured JSONL processor",
        "note": "Four synthetic fixtures, one per request to avoid preview truncation. No Cloud export; raw fixtures are in the linked script, not in evidence.",
        "cases": cases,
    }
    path = ROOT / "submission/evidence/05a-pii-runtime.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: 4/4 synthetic PII cases; complete markers; no raw fixture in file or console logs.")
    print(f"Evidence: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

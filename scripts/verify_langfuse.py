"""Run ten synthetic API requests and verify their traces on Langfuse Cloud."""
import asyncio
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SAFE_METADATA = {"correlation_id", "model", "feature", "simulated", "ttft_ms",
                 "prompt_source", "prompt_label", "prompt_name", "prompt_version",
                 "prompt_fetch_error", "doc_count", "tool_success", "query_preview"}
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.main import app
from app.tracing import get_langfuse_client


async def workload(session):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://lab") as client:
        health = (await client.get("/health")).json()
        assert health["ok"] and health["tracing_enabled"], health
        for index in range(10):
            response = await client.post("/chat", json={
                "user_id": "setup-demo", "session_id": session, "feature": "qa",
                "message": "Explain how metrics logs and traces help debug an API.",
            })
            response.raise_for_status()
            print(f"request {index + 1}: HTTP {response.status_code} {response.json()['correlation_id']}")


def main():
    client = get_langfuse_client()
    assert client.auth_check(), "Langfuse authentication failed"
    session = sys.argv[1] if len(sys.argv) > 1 else "setup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    if len(sys.argv) == 1:
        asyncio.run(workload(session))
    client.flush()
    traces = {}
    for attempt in range(12):
        rows = client.api.observations.get_many(
            session_id=session, limit=100, fields="core,basic,usage,metadata,model",
            from_start_time=datetime.now(timezone.utc) - timedelta(days=1),
            to_start_time=datetime.now(timezone.utc),
        ).data
        traces = {}
        for row in rows:
            item = row.dict(by_alias=True)
            traces.setdefault(item["traceId"], []).append(item)
        if len(traces) >= 10 and all(len(items) >= 3 for items in traces.values()):
            break
        print(f"Cloud ingestion: {len(traces)}/10 traces (attempt {attempt + 1})", flush=True)
        time.sleep(5)
    evidence = {"session_id": session, "trace_count": len(traces), "traces": []}
    for trace_id, observations in traces.items():
        evidence["traces"].append({
            "trace_id": trace_id,
            "url": client.get_trace_url(trace_id=trace_id),
            "observations": [{"name": item.get("name"), "type": item.get("type"),
                              "id": item.get("id"), "parent_id": item.get("parentObservationId"),
                              "model": item.get("model") or item.get("providedModelName") or (item.get("metadata") or {}).get("model"), "usage": item.get("usageDetails"),
                              "cost": item.get("costDetails"),
                              "metadata": {key: value for key, value in (item.get("metadata") or {}).items() if key in SAFE_METADATA}}
                             for item in observations],
        })
    path = ROOT / "submission/evidence/langfuse-setup.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    assert len(traces) >= 10, "Cloud has not returned all traces yet; inspect evidence and retry later"
    for trace in evidence["traces"]:
        names = {item["name"] for item in trace["observations"]}
        assert {"lab-agent-run", "retrieval", "llm-generation"} <= names, names
        root = next(item for item in trace["observations"] if item["name"] == "lab-agent-run")
        for item in trace["observations"]:
            if item["name"] != "lab-agent-run":
                assert item["parent_id"] == root["id"]
    print(f"VERIFIED: {len(traces)} Cloud traces with root, retrieval and generation. Evidence: {path}")


if __name__ == "__main__":
    main()

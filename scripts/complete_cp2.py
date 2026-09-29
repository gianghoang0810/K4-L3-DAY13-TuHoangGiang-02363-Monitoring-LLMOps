"""Create lab prompt versions, verify rollback, and run a labelled practice incident.

Uses synthetic data, never reads or creates config/challenge.json.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sys
import time

from dotenv import load_dotenv
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
os.environ["LANGFUSE_PROMPT_CACHE_TTL_SECONDS"] = "0"
os.environ.setdefault("LANGFUSE_TIMEOUT", "30")
from app.main import app
from app.tracing import get_langfuse_client
from app.incidents import enable, disable
from app.dashboard import aggregate, read_records, snapshot, render_dashboard
from verify_langfuse import SAFE_METADATA

NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
BASE = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
CANDIDATE = BASE + "\nAnswer in at most three concise sentences."
FOLDER = ROOT / "submission/evidence"


def save(name, data):
    FOLDER.mkdir(exist_ok=True)
    (FOLDER / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def ensure_prompt(client, version, template, labels):
    try:
        prompt = client.get_prompt(NAME, version=version, cache_ttl_seconds=0, max_retries=0)
    except Exception as exc:
        if getattr(exc, "status_code", None) != 404:
            raise
        prompt = client.create_prompt(name=NAME, type="text", prompt=template, labels=labels,
                                      commit_message=f"Day13 lab prompt v{version}")
    if prompt.version != version or prompt.prompt != template:
        raise RuntimeError("Existing prompt differs; refusing to overwrite user prompt")
    client.update_prompt(name=NAME, version=version, new_labels=labels)
    return prompt


async def send_stage(client, session, count, message="Explain monitoring metrics logs and traces."):
    results = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://lab") as http:
        for index in range(count):
            response = await http.post("/chat", json={
                "user_id": "cp2-demo", "session_id": session, "feature": "qa", "message": message,
            })
            response.raise_for_status()
            result = response.json()
            results.append({key: result[key] for key in ("correlation_id", "latency_ms", "ttft_ms", "cost_usd")})
    client.flush()
    return results


def fetch_cloud(client, sessions, started):
    all_rows = []
    for session, expected in sessions.items():
        for attempt in range(5):
            rows = client.api.observations.get_many(
                session_id=session, from_start_time=started - timedelta(seconds=5),
                to_start_time=datetime.now(timezone.utc), limit=100,
                fields="core,basic,usage,metadata,model,prompt",
            ).data
            if len(rows) >= expected * 3:
                break
            print(f"Waiting for Cloud session {session}: {len(rows)}/{expected * 3}", flush=True)
            time.sleep(3)
        if len(rows) < 3:
            raise RuntimeError(f"Cloud evidence incomplete for {session}")
        if len(rows) < expected * 3:
            print(f"Partial ingestion for {session}: {len(rows)} observations; report only confirmed traces", flush=True)
        for row in rows:
            item = row.dict(by_alias=True)
            meta = item.get("metadata") or {}
            all_rows.append({
                "session": session, "trace_id": item["traceId"], "id": item["id"],
                "parent_id": item.get("parentObservationId"), "name": item.get("name"),
                "type": item.get("type"), "start": item.get("startTime"), "end": item.get("endTime"),
                "model": item.get("model") or meta.get("model"),
                "usage": item.get("usageDetails"), "cost": item.get("costDetails"),
                "prompt_id": item.get("promptId"), "prompt_version": item.get("promptVersion"),
                "metadata": {key: value for key, value in meta.items() if key in SAFE_METADATA},
                "url": client.get_trace_url(trace_id=item["traceId"]),
            })
    return all_rows


def main():
    client = get_langfuse_client()
    assert client.auth_check()
    if "--resume" in sys.argv:
        stages = json.loads((FOLDER / "prompt-workflow.json").read_text(encoding="utf-8"))["stages"]
        sessions = {entry["session"]: len(entry["requests"]) for entry in stages}
        finalize(client, stages, sessions, datetime.now(timezone.utc) - timedelta(days=1))
        return
    started = datetime.now(timezone.utc)
    run = started.strftime("%Y%m%dT%H%M%S")
    previous = FOLDER / "prompt-workflow.json"
    if previous.exists():
        previous.rename(FOLDER / f"prompt-workflow-history-{run}.json")
    ensure_prompt(client, 1, BASE, ["baseline", "production"])
    ensure_prompt(client, 2, CANDIDATE, ["candidate"])
    stages = []
    sessions = {}

    def stage(name, label, version, count=3, message="Explain monitoring metrics logs and traces."):
        os.environ["LANGFUSE_PROMPT_LABEL"] = label
        current = client.get_prompt(NAME, label=label, cache_ttl_seconds=0)
        assert current.version == version
        session = f"cp2-{run}-{name}"
        output = asyncio.run(send_stage(client, session, count, message))
        entry = {"stage": name, "session": session, "label": label,
                 "version": current.version, "requests": output,
                 "verified_at": datetime.now(timezone.utc).isoformat()}
        stages.append(entry)
        sessions[session] = count
        save("prompt-workflow.json", {"prompt": NAME, "stages": stages})
        print(f"Stage {name}: {count} HTTP 200, prompt v{version} / {label}", flush=True)

    stage("baseline", "baseline", 1)
    stage("candidate", "candidate", 2)
    try:
        client.update_prompt(name=NAME, version=2, new_labels=["production"])
        stage("promoted", "production", 2)
    finally:
        client.update_prompt(name=NAME, version=1, new_labels=["production"])
    stage("rollback", "production", 1)

    # Runtime PII sample; save only redacted events, never raw input to evidence.
    stage("pii", "production", 1, count=1,
          message="Email student@example.com, phone 0901234567, CCCD 001092001234, card 4532-1111-2222-3333. Explain monitoring.")
    stage("practice-before", "production", 1, count=3)
    enable("rag_slow")
    try:
        stage("practice-slow", "production", 1, count=3)
    finally:
        disable("rag_slow")
    stage("practice-after", "production", 1, count=3)
    finalize(client, stages, sessions, started)


def finalize(client, stages, sessions, started):
    rows = fetch_cloud(client, sessions, started)
    save("cp2-cloud-observations.json", rows)
    for entry in stages:
        roots = [r for r in rows if r["session"] == entry["session"] and r["name"] == "lab-agent-run"]
        assert 1 <= len(roots) <= len(entry["requests"])
        for root in roots:
            assert root["metadata"]["prompt_source"] == "langfuse"
            assert str(root["metadata"]["prompt_version"]) == str(entry["version"])
            children = [r for r in rows if r["parent_id"] == root["id"]]
            assert {r["name"] for r in children} == {"retrieval", "llm-generation"}
        entry["trace_ids"] = [r["trace_id"] for r in roots]
        entry["confirmed_traces"] = len(roots)
        entry["sent_requests"] = len(entry["requests"])
    assert len({r["trace_id"] for r in rows}) >= 10
    save("prompt-workflow.json", {"prompt": NAME, "stages": stages,
                                "production_version_after_rollback": client.get_prompt(NAME, label="production", cache_ttl_seconds=0).version})
    records, _ = read_records()
    practice = {"kind": "practice_only_not_official_challenge", "scenario": "rag_slow", "stages": []}
    for entry in stages:
        selected = [r for r in records if r.get("session_id") == entry["session"]]
        if "practice" in entry["stage"]:
            practice["stages"].append({**entry, "metrics": aggregate(selected)})
        if entry["stage"] == "pii":
            save("05-pii-redaction.json", [{k: v for k, v in r.items() if k != "_time"} for r in selected])
    save("practice-investigation.json", practice)
    data = snapshot()
    save("dashboard-metrics.json", data)
    (FOLDER / "11-dashboard-overview.html").write_text(render_dashboard(data, live=False), encoding="utf-8")
    print(f"CP2 verified: {len(rows)} Cloud observations; production rolled back to v1.")


if __name__ == "__main__":
    main()

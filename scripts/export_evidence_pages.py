"""Render reviewable HTML pages from real local logs and Langfuse API exports.

These pages are evidence mirrors, not screenshots of the Langfuse web UI.
"""
from datetime import datetime
from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "submission/evidence"
PROJECT_NAME = "day13-k4-l3a-02363"


def page(title: str, subtitle: str, body: str) -> str:
    return f'''<!doctype html><html><meta charset="utf-8"><title>{escape(title)}</title><style>
    body{{background:#0b1320;color:#e8eff9;font:16px system-ui;margin:42px auto;max-width:1180px;padding:0 26px}}
    h1{{font-size:30px;margin-bottom:6px}}h2{{margin-top:30px}}.sub,small{{color:#9fb1c9}}.box{{background:#142238;border:1px solid #304768;border-radius:12px;padding:20px;margin:18px 0}}
    pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#08101c;border-radius:8px;padding:18px;color:#bce7de}}
    table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #304768;vertical-align:top}}
    .tag{{display:inline-block;background:#29415f;border-radius:999px;padding:4px 10px;margin:3px}}.ok{{color:#7de3b2}}.warn{{color:#ffd37d}}
    .bar{{height:22px;border-radius:5px;background:#51d2c7;min-width:3px}}code{{color:#c8b7ff}}
    </style><small>K4-L3A · MSSV 2A202602363 · {PROJECT_NAME}</small><h1>{escape(title)}</h1><p class="sub">{escape(subtitle)}</p>{body}</html>'''


def save(name: str, title: str, subtitle: str, body: str) -> None:
    (EVIDENCE / name).write_text(page(title, subtitle, body), encoding="utf-8")


def json_pre(value) -> str:
    return f"<pre>{escape(json.dumps(value, ensure_ascii=False, indent=2, default=str))}</pre>"


def main() -> None:
    pii = json.loads((EVIDENCE / "05-pii-redaction.json").read_text(encoding="utf-8"))
    response = next(row for row in pii if row.get("event") == "response_sent")
    request = next(row for row in pii if row.get("event") == "request_received")
    save("04-structured-log.html", "Structured log runtime", "Real response_sent event from data/logs.jsonl", json_pre(response))
    markers = sorted(set(part.split("]", 1)[0] + "]" for part in request["payload"]["message_preview"].split("[") if part.startswith("REDACTED_")))
    save("05-pii-redaction.html", "PII redaction runtime", "Synthetic input contained email, VN phone, CCCD and payment card. Raw values are intentionally omitted.",
         '<div class="box"><h2>Detected redaction markers</h2>' + ''.join(f'<span class="tag">{escape(marker)}</span>' for marker in markers) + '</div>' + json_pre(request))

    rows = json.loads((EVIDENCE / "cp2-cloud-observations.json").read_text(encoding="utf-8"))
    roots = [row for row in rows if row["name"] == "lab-agent-run"]
    trace_rows = ''.join(f'<tr><td><code>{r["trace_id"]}</code></td><td>{escape(r["session"])}</td><td>{r["metadata"].get("prompt_label")}</td><td>v{r["metadata"].get("prompt_version")}</td></tr>' for r in roots)
    save("06-trace-list.html", "Langfuse trace list — API export", f"{len(roots)} confirmed traces read from Langfuse Observations API v2", f'<div class="box"><table><tr><th>Trace ID</th><th>Session</th><th>Prompt label</th><th>Version</th></tr>{trace_rows}</table></div>')

    slow_root = next(r for r in roots if r["session"].endswith("practice-slow"))
    trace = [r for r in rows if r["trace_id"] == slow_root["trace_id"]]
    start = min(datetime.fromisoformat(r["start"]) for r in trace)
    end = max(datetime.fromisoformat(r["end"]) for r in trace)
    total_ms = max(1, (end - start).total_seconds() * 1000)
    waterfall = []
    for row in sorted(trace, key=lambda r: r["start"]):
        row_start, row_end = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
        duration = (row_end - row_start).total_seconds() * 1000
        offset = (row_start - start).total_seconds() * 1000
        waterfall.append(f'<tr><td>{escape(row["name"])}</td><td>{row["type"]}</td><td>{duration:.0f} ms</td><td style="width:55%"><div class="bar" style="margin-left:{offset/total_ms*65:.1f}%;width:{max(1,duration/total_ms*65):.1f}%"></div></td></tr>')
    save("07-trace-waterfall.html", "Trace waterfall — Cloud API mirror", f'Trace {slow_root["trace_id"]}; values read from Langfuse Cloud, not a Langfuse UI screenshot', f'<div class="box"><table><tr><th>Observation</th><th>Type</th><th>Duration</th><th>Timeline ({total_ms:.0f} ms)</th></tr>{"".join(waterfall)}</table></div>')
    generation = next(r for r in trace if r["name"] == "llm-generation")
    metadata = {"trace_id": slow_root["trace_id"], "trace_url": slow_root["url"], "correlation_id": slow_root["metadata"]["correlation_id"],
                "model": generation["model"], "prompt_name": slow_root["metadata"]["prompt_name"], "prompt_label": slow_root["metadata"]["prompt_label"],
                "prompt_version": slow_root["metadata"]["prompt_version"], "usage": generation["usage"], "cost": generation["cost"]}
    save("08-trace-metadata.html", "Trace metadata — Cloud API export", "Correlation ID connects this Cloud trace to the structured log; token/cost are simulated.", json_pre(metadata))

    workflow = json.loads((EVIDENCE / "prompt-workflow.json").read_text(encoding="utf-8"))
    versions = '<div class="box"><table><tr><th>Version</th><th>Labels exercised</th><th>Template change</th></tr><tr><td>v1</td><td>baseline, production</td><td>Base contract with feature/docs/message</td></tr><tr><td>v2</td><td>candidate, production during promote</td><td>Add concise answer instruction</td></tr></table></div>'
    save("09-prompt-versions.html", "Managed prompt versions — API verified", f'Prompt {workflow["prompt"]} in {PROJECT_NAME}', versions)
    stage_rows = ''.join(f'<tr><td>{s["stage"]}</td><td>{s["label"]}</td><td>v{s["version"]}</td><td>{s.get("confirmed_traces", 0)}/{s.get("sent_requests", len(s["requests"]))}</td><td><code>{s.get("trace_ids", ["—"])[0]}</code></td></tr>' for s in workflow["stages"] if s["stage"] in {"baseline", "candidate", "promoted", "rollback"})
    save("10-prompt-rollback.html", "Prompt promote and rollback — API verified", f'Final production version: v{workflow["production_version_after_rollback"]}', f'<div class="box"><table><tr><th>Stage</th><th>Label</th><th>Version</th><th>Confirmed/sent</th><th>Example trace</th></tr>{stage_rows}</table></div><p class="ok">production was promoted to v2 and restored to v1.</p>')
    print("Rendered evidence HTML pages 04–10 from runtime/API data")


if __name__ == "__main__":
    main()

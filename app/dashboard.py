"""Six-panel dashboard computed exclusively from structured JSONL logs."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
from pathlib import Path
from statistics import mean

import yaml

ROOT = Path(__file__).resolve().parents[1]


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)]


def read_records(path=None):
    path = Path(path or ROOT / "data/logs.jsonl")
    records = []
    skipped = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
                record["_time"] = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
                if record["_time"].tzinfo is None:
                    raise ValueError("Timestamp must have timezone")
                records.append(record)
            except (ValueError, KeyError, TypeError):
                skipped += 1
    return records, skipped


def aggregate(records):
    received = [r for r in records if r.get("event") == "request_received"]
    completed = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]
    tools = [r for r in records if r.get("tool_name") == "retrieval" and isinstance(r.get("tool_success"), bool)]
    numbers = lambda field: [r[field] for r in completed if isinstance(r.get(field), (float, int))]
    slo_total = len(received)
    slo_good = sum(r.get("latency_ms", float("inf")) <= 3000 for r in completed)
    return {
        "requests": len(received), "responses": len(completed), "failures": len(failed),
        "p50": percentile(numbers("latency_ms"), 50),
        "p95": percentile(numbers("latency_ms"), 95),
        "p99": percentile(numbers("latency_ms"), 99),
        "ttft_p95": percentile(numbers("ttft_ms"), 95),
        "error_rate_pct": len(failed) / len(received) * 100 if received else None,
        "retrieval_success_pct": sum(r["tool_success"] for r in tools) / len(tools) * 100 if tools else None,
        "error_breakdown": dict(Counter(r.get("error_type", "unknown") for r in failed)),
        "cost_usd": sum(numbers("cost_usd")), "tokens_in": sum(numbers("tokens_in")),
        "tokens_out": sum(numbers("tokens_out")),
        "quality": mean(numbers("quality_score")) if numbers("quality_score") else None,
        "slo_total": slo_total,
        "slo_good": slo_good,
        "slo_bad": max(0, slo_total - slo_good),
        "slo_attainment_pct": slo_good / slo_total * 100 if slo_total else None,
    }


def snapshot(path=None, end=None):
    contract = yaml.safe_load((ROOT / "config/dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(minutes=contract["time_range_minutes"])
    records, skipped = read_records(path)
    selected = [r for r in records if start <= r["_time"] <= end]
    minute = start.replace(second=0, microsecond=0)
    series = []
    while minute <= end:
        next_minute = minute + timedelta(minutes=1)
        series.append({"time": minute.isoformat(), **aggregate([r for r in selected if minute <= r["_time"] < next_minute])})
        minute = next_minute
    return {"start": start.isoformat(), "end": end.isoformat(), "source": "data/logs.jsonl",
            "skipped_records": skipped, "summary": aggregate(selected), "series": series,
            "contract": contract}


def chart(series, fields, threshold, threshold_label):
    colors = ["#56d8cc", "#f5bd69", "#b99aff", "#7bb7ff"]
    values = [r.get(field) for r in series for field in fields if r.get(field) is not None]
    ymax = max([threshold, 1, *values]) * 1.15
    result = ['<svg viewBox="0 0 540 150" role="img" aria-label="Time series with threshold">']
    y = lambda value: 120 - value / ymax * 105
    result.append(f'<path d="M38 {y(threshold):.1f}H530" stroke="#ff8282" stroke-dasharray="5 5"/>')
    result.append(f'<text x="40" y="{max(12, y(threshold)-5):.1f}" fill="#ffb7b7">{escape(threshold_label)}</text>')
    for index, field in enumerate(fields):
        points = []
        for n, row in enumerate(series):
            value = row.get(field)
            if value is None:
                if points:
                    result.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[index]}" stroke-width="2"/>')
                    points = []
                continue
            x = 40 + n / max(1, len(series)-1) * 485
            points.append(f"{x:.1f},{y(value):.1f}")
            result.append(f'<circle cx="{x:.1f}" cy="{y(value):.1f}" r="2.5" fill="{colors[index]}"/>')
        if points:
            result.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[index]}" stroke-width="2"/>')
    result.append(f'<text x="3" y="14">{ymax:.2g}</text><text x="15" y="122">0</text>')
    result.append(f'<text x="40" y="145">{series[0]["time"][11:16]} UTC</text><text x="470" y="145">{series[-1]["time"][11:16]}</text></svg>')
    result.append('<div class="legend">' + ' · '.join(f'<span style="color:{colors[i]}">{escape(field)}</span>' for i, field in enumerate(fields)) + '</div>')
    return ''.join(result)


def render_dashboard(data, live=True):
    s, contract = data["summary"], data["contract"]
    fmt = lambda value, decimals=2: "N/A" if value is None else f"{value:,.{decimals}f}"
    details = [
        (f'P50 {fmt(s["p50"])} · P95 {fmt(s["p95"])} · P99 {fmt(s["p99"])} ms', f'TTFT P95 {fmt(s["ttft_p95"])} ms', ["p50", "p95", "p99", "ttft_p95"]),
        (f'{s["requests"]} requests', f'{s["requests"]/contract["time_range_minutes"]:.2f} requests/min over full window', ["requests"]),
        (f'Errors {fmt(s["error_rate_pct"])}%', f'Retrieval success {fmt(s["retrieval_success_pct"])}% · breakdown {escape(str(s["error_breakdown"]))}', ["error_rate_pct", "retrieval_success_pct"]),
        (f'${s["cost_usd"]:.6f}', 'Simulated USD · chart: cost per minute', ["cost_usd"]),
        (f'Input {s["tokens_in"]:,} · Output {s["tokens_out"]:,}', 'tokens · per-minute sums', ["tokens_in", "tokens_out"]),
        (f'{fmt(s["quality"])} / 1', 'Heuristic quality proxy; not human evaluation', ["quality"]),
    ]
    cards = []
    for panel, (value, subtitle, fields) in zip(contract["panels"], details):
        t = panel["threshold"]
        threshold_label = f'{t["aggregation"]} {t["operator"]} {t["value"]} {panel["unit"]}'
        cards.append(f'<section><h2>{escape(panel["title"])}</h2><div class="value">{value}</div><p>{subtitle}</p>' + chart(data["series"], fields, t["value"], threshold_label) + f'<small>Threshold: {escape(threshold_label)}</small></section>')
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    {f'<meta http-equiv="refresh" content="{contract["refresh_seconds"]}">' if live else ''}
    <title>Day 13 · Monitoring dashboard</title><style>
    body{{background:#0c1422;color:#e7edf7;font:14px system-ui;margin:26px auto;max-width:1240px;padding:0 20px}}
    h1{{font-size:28px;margin:6px 0}} header p,small{{color:#9cb0ca}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
    section{{background:#142137;border:1px solid #2d405d;border-radius:12px;padding:18px}}h2{{font-size:17px;margin:0 0 12px}}
    .value{{font-size:22px;font-weight:650}}p{{margin:6px 0 10px}}svg{{width:100%;height:150px}}svg text{{font:10px system-ui;fill:#9cb0ca}}
    .legend{{font-size:11px;margin-bottom:6px}}footer{{margin-top:16px;color:#9cb0ca}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
    </style><header><small>K4-L3A · 02363 · LOG-BASED OBSERVABILITY</small><h1>Monitoring & LLMOps</h1>
    <p>{escape(data['start'])} → {escape(data['end'])} · {contract['time_range_minutes']} min · refresh {contract['refresh_seconds']}s</p>
    <p>Source: {data['source']} · malformed records skipped: {data['skipped_records']} · {'LIVE' if live else 'SAVED RUNTIME SNAPSHOT'}</p></header>
    <main class="grid">{''.join(cards)}</main><footer>SLO sample: {s['slo_good']}/{s['slo_total']} good ({fmt(s['slo_attainment_pct'])}%), {s['slo_bad']} bad. Percentiles: nearest rank. Empty data = N/A. Cost threshold applies to window total; token threshold to each field total. Time-series buckets at window edges may be partial.</footer></html>'''

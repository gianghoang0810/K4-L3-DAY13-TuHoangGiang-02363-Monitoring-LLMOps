from datetime import datetime, timezone, timedelta

from app.dashboard import aggregate, snapshot, render_dashboard


def test_dashboard_handles_failures_and_retrieval_denominator():
    rows = [{"event": "request_received"}] * 4 + [
        {"event": "response_sent", "latency_ms": 100, "ttft_ms": 30, "tokens_in": 10,
         "tokens_out": 20, "cost_usd": 0.01, "quality_score": 0.8,
         "tool_name": "retrieval", "tool_success": True},
        {"event": "request_failed", "error_type": "RuntimeError", "tool_name": "retrieval", "tool_success": False},
    ]
    result = aggregate(rows)
    assert result["error_rate_pct"] == 25
    assert result["retrieval_success_pct"] == 50
    assert result["error_breakdown"] == {"RuntimeError": 1}
    assert result["tokens_in"] == 10
    assert result["ttft_p95"] == 30
    assert result["slo_total"] == 4
    assert result["slo_good"] == 1
    assert result["slo_bad"] == 3
    assert result["slo_attainment_pct"] == 25
    assert aggregate([])["error_rate_pct"] is None


def test_dashboard_filters_time_and_displays_six_panels(tmp_path):
    import json
    end = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
    path = tmp_path / "log.jsonl"
    path.write_text('\n'.join(json.dumps({"ts": (end - timedelta(minutes=m)).isoformat(),
                                          "event": "request_received"}) for m in (1, 70)), encoding="utf-8")
    data = snapshot(path, end=end)
    assert data["summary"]["requests"] == 1
    assert sum(row["requests"] for row in data["series"]) == 1
    html = render_dashboard(data)
    assert html.count("<section>") == 6
    assert "refresh" in html and "3000" in html and "N/A" in html


def test_errors_panel_contract_includes_success_and_failure_events():
    import yaml
    from app.dashboard import ROOT
    contract = yaml.safe_load((ROOT / "config/dashboard.yaml").read_text(encoding="utf-8"))
    errors = next(panel for panel in contract["dashboard"]["panels"] if panel["id"] == "errors")
    assert {"request_received", "response_sent", "request_failed"} <= set(errors["events"])

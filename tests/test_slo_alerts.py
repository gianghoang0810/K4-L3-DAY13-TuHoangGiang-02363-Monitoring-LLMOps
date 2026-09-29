from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_slo_has_consistent_target_and_budget():
    slo = yaml.safe_load((ROOT / "config/slo.yaml").read_text(encoding="utf-8"))["primary_slo"]
    assert slo["target_percent"] + slo["error_budget_percent"] == 100
    assert slo["example_allowed_bad_requests"] == (
        slo["example_total_requests"] * slo["error_budget_percent"] / 100
    )
    assert "response_sent" in slo["sli"]["good_event"]
    assert "request_received" in slo["sli"]["total_event"]


def test_three_symptom_alerts_have_operational_fields_and_runbooks():
    config = yaml.safe_load((ROOT / "config/alert_rules.yaml").read_text(encoding="utf-8"))
    alerts = config["alerts"]
    assert len(alerts) == 3
    assert config["notification_status"] == "configured_only_no_slack_webhook"
    for alert in alerts:
        assert alert["type"] == "symptom-based"
        assert alert["severity"] in {"warning", "critical"}
        assert alert["duration"].endswith("m")
        assert alert["channel"] == "slack"
        assert alert["slack_channel"].startswith("#")
        assert alert["owner"] == "TuHoangGiang-02363"
        section = alert["runbook"].split("#", 1)[1]
        runbook = (ROOT / alert["runbook"].split("#", 1)[0]).read_text(encoding="utf-8-sig").lower()
        assert f"## {section.replace('-', ' ').title()}".lower() in runbook

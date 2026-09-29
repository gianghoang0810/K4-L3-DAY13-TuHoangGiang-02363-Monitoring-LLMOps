"""Save actual log-derived dashboard HTML and metrics; no generated sample data."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.dashboard import snapshot, render_dashboard

if __name__ == "__main__":
    data = snapshot()
    folder = ROOT / "submission/evidence"
    folder.mkdir(exist_ok=True)
    (folder / "11-dashboard-overview.html").write_text(render_dashboard(data, live=False), encoding="utf-8")
    (folder / "dashboard-metrics.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data["summary"], indent=2))

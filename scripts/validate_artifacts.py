"""Check evidence links and prevent committing the configured Langfuse keys."""
from pathlib import Path
import re
import subprocess

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = dotenv_values(ROOT / ".env")
    keys = [config.get(key) for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if config.get(key)]
    files = subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, text=True,
    ).splitlines()
    hits = []
    for name in files:
        path = ROOT / name
        if path.is_file() and any(key.encode() in path.read_bytes() for key in keys):
            hits.append(name)
    assert not hits, f"Configured credentials present in: {hits}"
    print(f"Configured credential scan: {len(keys)} keys checked; no matches in candidate repository files")
    missing = []
    for name in ("README.md", "submission/REPORT.md", "submission/evidence/README.md"):
        path = ROOT / name
        if not path.exists():
            continue
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8-sig"), flags=re.S)
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in link or link.startswith("#"):
                continue
            target = link.split("#")[0]
            if target and not (path.parent / target).exists():
                missing.append((name, target))
    assert not missing, missing
    print("Local Markdown links in project documents: OK (code examples excluded)")
    for name in ("cp2-cloud-observations.json", "05-pii-redaction.json", "05a-pii-runtime.json", "langfuse-setup.json"):
        text = (ROOT / "submission/evidence" / name).read_text(encoding="utf-8")
        for raw in ("student@example.com", "0901234567", "001092001234", "4532-1111-2222-3333"):
            assert raw not in text, name
    print("Runtime sample PII absent from exported evidence")
    print("This is a targeted scan, not a complete security audit or screenshot check.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""W1 p4d fixture predicates (invoked from w1_proof_gate.sh)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "incident_triage.py"),
            "--sentinel-json",
            str(ROOT / "tests/fixtures/restart-resolved-report.json"),
            "--alert",
            str(ROOT / "tests/fixtures/restart-alert.json"),
            "--output-format",
            "json",
        ],
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    if proc.returncode not in (0, 3):
        print(f"FAIL: cli exit {proc.returncode}: {proc.stderr}", file=sys.stderr)
        return 1
    d = json.loads(proc.stdout)
    corr = d.get("correlation") or {}
    alert_type = corr.get("alert_type") or d.get("alert_type")
    if alert_type != "crash_loop":
        print(f"FAIL: alert_type={alert_type}", file=sys.stderr)
        return 1
    conf = str(d.get("confidence") or d.get("confidence_level") or "").lower()
    if "low" not in conf:
        print(f"FAIL: confidence={conf!r}", file=sys.stderr)
        return 1
    rc = d.get("root_cause")
    msg = rc.get("message", "") if isinstance(rc, dict) else str(rc or "")
    if "billing" in msg.lower() and "job" in msg.lower():
        print(f"FAIL: bogus job root: {msg}", file=sys.stderr)
        return 1
    print("p4d-restart-classifier: ok")
    print("p4d-honest-resolved: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

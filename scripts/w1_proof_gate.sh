#!/usr/bin/env bash
# GreenerPlatform proof program W1 gate — run from repo root.
# Exit 0 when fixtures + correlation tests pass; exit 1 on failure.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== W1: unittest (correlation + fixtures) =="
python3 -m unittest tests.test_correlation -v

echo "== W1: CLI smoke (sample + p4d restart resolved) =="
for pair in "sample-report.json:sample-alert.json" "restart-resolved-report.json:restart-alert.json"; do
  report="${pair%%:*}"
  alert="${pair##*:}"
  set +e
  python3 incident_triage.py \
    --sentinel-json "tests/fixtures/$report" \
    --alert "tests/fixtures/$alert" \
    --output-format json 2>/dev/null | python3 -m json.tool >/dev/null
  rc=${PIPESTATUS[0]}
  set -e
  if [[ "$rc" != "0" && "$rc" != "3" ]]; then
    echo "FAIL: triage exit $rc for $report"
    exit 1
  fi
done

echo "== W1: p4d predicates =="
python3 scripts/check_p4d_predicates.py

echo "== W1: regression probe (unittest must fail on bad classifier) =="
python3 scripts/w1_regression_probe.py

echo "W1 proof gate: PASS"

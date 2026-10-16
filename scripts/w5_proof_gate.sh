#!/usr/bin/env bash
# GreenerPlatform proof program W5 gate — evidence integrity (triage).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== W5: unittest (evidence gaps) =="
python3 -m unittest tests.test_w5_evidence tests.test_graph_correlation -v

echo "== W5: W1 still green =="
bash scripts/w1_proof_gate.sh

echo "W5 proof gate (incident-triage): PASS"

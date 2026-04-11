# incident-triage

Deterministic Kubernetes incident triage CLI tool. Given a sentinel JSON snapshot and an alert descriptor (PagerDuty, ADO, or free text), it correlates the alert symptom to sentinel findings, builds a causation chain, and emits a structured triage JSON report — no Claude required.

Works standalone in CI and as the data source for the `/triage` Claude skill.

---

## Requirements

- Python 3.10+
- A sentinel JSON snapshot (from `kubectl-sentinel --json`)
- No external pip packages — stdlib only

## Installation

```bash
bash install.sh          # installs to ~/bin
bash install.sh /usr/local/bin  # custom path
```

## Usage

```bash
# Full triage from files
incident-triage --sentinel-json report.json --alert alert.json

# Free-text alert
incident-triage --sentinel-json report.json --alert "payments API 503 since 14:30"

# Snapshot mode (no cluster access needed)
incident-triage --sentinel-json snap.json --alert pd-alert.json

# Override namespace when not determinable from alert
incident-triage --sentinel-json report.json --alert "service down" --namespace payments
```

## Flags

| Flag | Description |
|------|-------------|
| `--sentinel-json <file>` | Path to sentinel JSON snapshot (schema v1.0) |
| `--alert <text or file>` | Alert: free text or path to alert descriptor JSON |
| `--namespace <ns>` | Override namespace when not determinable from alert |
| `--output-format json\|text` | Output format (default: json) |

## Exit codes

| Code | When |
|------|------|
| `0` | Triage complete — valid output |
| `1` | Namespace unknown — Claude must ask the user |
| `2` | Sentinel snapshot missing or invalid — Claude must collect cluster state |
| `3` | No sentinel findings match the alert — low-confidence output produced |

## Output schema

See [schema.md](schema.md) for the full triage output JSON schema.

## Test fixtures

`tests/fixtures/` contains:
- `sample-report.json` — minimal sentinel v1.0 snapshot (CRITICAL: CrashLoopBackOff in namespace payments)
- `sample-alert.json` — PagerDuty alert descriptor (payments SLO breach)

Smoke test:
```bash
python3 incident-triage \
  --sentinel-json tests/fixtures/sample-report.json \
  --alert tests/fixtures/sample-alert.json \
  | python3 -m json.tool
```

## Claude skill

`/triage` in Claude Code uses this tool as its primary data source. The skill falls back to inline correlation when incident-triage is not installed.

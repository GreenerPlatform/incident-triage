## Why Incident Triage Takes Too Long

When PagerDuty fires, you get the alert — not the cause. You open the dashboard,
then kubectl, then Slack history, then runbooks. By the time you have a picture,
20 minutes are gone.

> **Alert in. Causation chain out. P1 command, ready to run.**

```bash
incident-triage \
  --sentinel-json snap.json \
  --alert "payments API 503 since 14:30"
```

```json
{
  "confidence": "high",
  "causation_chain": [
    { "label": "root_cause",   "description": "Pod payments/api-gateway CrashLoopBackOff (restarts: 47)" },
    { "label": "intermediate", "description": "Deployment payments/api-gateway — 0/3 replicas available" },
    { "label": "symptom",      "description": "payments API 503 since 14:30" },
    { "label": "alert",        "description": "Alert triggered: payments API 503 since 14:30" }
  ],
  "fix_plan": {
    "p1": {
      "action": "Restart the crashing deployment",
      "command": "kubectl rollout restart deploy/api-gateway -n payments"
    },
    "p2": {
      "action": "Watch pods return to Running state",
      "command": "kubectl get pods -n payments -w"
    },
    "p3": { "action": "Investigate why CrashLoopBackOff is recurring" }
  }
}
```

---

## Install

```bash
bash install.sh          # installs to ~/bin
bash install.sh /usr/local/bin  # custom path
```

**Requirements:** Python 3.10+ · stdlib only · no pip packages

---

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

# HTML report
incident-triage --sentinel-json snap.json --alert alert.json --output-format html > report.html
```

## Flags

| Flag | Description |
|------|-------------|
| `--sentinel-json <file>` | Path to sentinel JSON snapshot (kubectl-sentinel --json output) |
| `--alert <text or file>` | Alert: free text or path to alert descriptor JSON |
| `--namespace <ns>` | Override namespace when not determinable from alert |
| `--output-format json\|html` | Output format (default: json) |

## Alert descriptor JSON

When `--alert` points to a JSON file, it is parsed as an alert descriptor:

```json
{
  "alert_source": "pagerduty",
  "alert_name": "payments SLO breach — availability < 99.5%",
  "service": "api-gateway",
  "namespace": "payments",
  "severity": "critical",
  "start_time": "2026-04-11T14:30:00Z"
}
```

Free text is also accepted — service name, namespace, and timestamps are extracted via regex.

## Exit codes

| Code | When |
|------|------|
| `0` | Triage complete — valid output |
| `1` | Namespace unknown |
| `2` | Sentinel snapshot missing or invalid |
| `3` | No sentinel findings match the alert — low-confidence output produced |

## How it works

1. **Classify** — alert text is matched to one of 12 alert types (SLO burn, CrashLoop, OOMKill, etc.)
2. **Prioritise** — sentinel sections are ranked by relevance to the alert type
3. **Score** — each finding is classified as `direct`, `contributing`, or `background`
4. **Chain** — the top direct finding becomes the root cause; contributing findings become intermediate steps
5. **Plan** — P1 command comes from the sentinel `recommendation` field (a complete kubectl command)

No LLM calls. No network access. Deterministic output for the same inputs.

## Smoke test

```bash
python3 incident-triage \
  --sentinel-json tests/fixtures/sample-report.json \
  --alert tests/fixtures/sample-alert.json \
  | python3 -m json.tool
```

`tests/fixtures/` contains a minimal sentinel snapshot (CRITICAL: CrashLoopBackOff in namespace
payments) and a matching PagerDuty alert descriptor.

## Output schema

See [schema.md](schema.md) for the full triage output JSON schema.

## The dual-layer pattern

incident-triage is the deterministic layer: alert → cluster state → causation chain in under
1 second. The `/triage` Claude Code skill is the reasoning layer: it runs sentinel, feeds the
output to this tool, then adds context from PagerDuty history, related incidents, and playbooks.

---

## Contributing

Issues and pull requests welcome.

Design principle: classify before you recommend. OOMKill does not always mean "raise the limit" —
the root cause (limit too low vs. memory leak vs. input spike) determines the correct fix.

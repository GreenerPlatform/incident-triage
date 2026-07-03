<div align="center">
  <img src="docs/banner.svg" alt="incident-triage" width="100%"/>
</div>

<div align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/GreenerPlatform/incident-triage/ci.yml?style=flat-square&label=CI" alt="CI"/>
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python"/>
  <img src="https://img.shields.io/badge/stdlib%20only-no%20pip-lightgrey?style=flat-square" alt="stdlib only"/>
  <img src="https://img.shields.io/badge/output-JSON%20%7C%20HTML-lightgrey?style=flat-square" alt="output formats"/>
  <img src="https://img.shields.io/badge/CI%20safe-exit%200--3-brightgreen?style=flat-square" alt="exit codes"/>
  <img src="https://img.shields.io/github/license/GreenerPlatform/incident-triage?style=flat-square" alt="license"/>
</div>

---

## Why Incident Triage Takes Too Long

When your on-call alert fires — PagerDuty, Alertmanager, Opsgenie, Grafana, or a
plain webhook — you get the symptom, not the cause. You open the dashboard, then
kubectl, then chat history, then runbooks. By the time you have a picture, 20
minutes are gone.

> **Alert in. Causation chain out. Fix command, ready to run.**

```bash
incident-triage \
  --sentinel-json snap.json \
  --alert "payments API 503 since 14:30"
```

```json
{
  "confidence": "high",
  "what_changed": {
    "detected": true,
    "summary": "Likely trigger: deploy/rollout change — a new build is crashing on startup; first seen 2 min before the alert (Pod payments/api-gateway).",
    "trigger": { "change_type": "deploy/rollout change", "reason": "BackOff", "seconds_before_alert": 135 }
  },
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
# pipx (recommended — isolated, on your PATH)
pipx install incident-triage

# or pip
pip install incident-triage

# or from source, no packaging
git clone https://github.com/GreenerPlatform/incident-triage
cd incident-triage && bash install.sh /usr/local/bin
```

**Requirements:** Python 3.10+ · standard library only · zero runtime dependencies

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
  "alert_source": "pagerduty | alertmanager | opsgenie | grafana | webhook | freetext",
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
5. **What changed** — event timestamps are correlated against the alert start time to surface the *likely trigger* ("a new build started crashing 2 min before the alert") and classify the change type — config, image, rollout, resource, scheduling, quota, or probe/health
6. **Plan** — the fix command comes from the sentinel `recommendation` field (a complete kubectl command)

No LLM calls. No network access. Deterministic output for the same inputs — including `what_changed`, which is pure temporal correlation over the snapshot.

## Smoke test

```bash
python3 incident_triage.py \
  --sentinel-json tests/fixtures/sample-report.json \
  --alert tests/fixtures/sample-alert.json \
  | python3 -m json.tool
```

`tests/fixtures/` contains a minimal sentinel snapshot (CRITICAL: CrashLoopBackOff in namespace
payments) and a matching alert descriptor.

## Output schema

See [schema.md](schema.md) for the full triage output JSON schema.

## Getting cluster state

`incident-triage` reads a sentinel JSON snapshot. Collect one with
[kubectl-sentinel](https://github.com/GreenerPlatform/kubectl-sentinel):

```bash
# Install kubectl-sentinel (requires kubectl + jq)
git clone https://github.com/GreenerPlatform/kubectl-sentinel
cd kubectl-sentinel && bash install.sh ~/bin && cd -

# Collect cluster state and triage in one pipeline
kubectl sentinel --json -n payments > snap.json
incident-triage --sentinel-json snap.json --alert "payments API 503 since 14:30"
```

kubectl-sentinel runs 15 health dimensions in under 10 seconds and emits structured JSON.
Its `recommendation` field is used directly as the fix command in the triage output.

## Using it from an AI agent (any runtime)

The tool is a plain CLI with JSON in/out, so any agent can drive it. Two paths:

**1. MCP server (recommended, vendor-neutral).** The [GreenerPlatform MCP server](https://github.com/GreenerPlatform)
exposes `sentinel` and `triage` as tools to any MCP-capable client — Cursor, Claude Desktop,
VS Code, Windsurf, or a custom agent. Install once; it works everywhere.

**2. Reference agent skill.** [`skills/SKILL.md`](skills/SKILL.md) is a reference reasoning-layer
integration (Claude Code command + an optional PagerDuty enrichment phase). Copy it into your
agent's command directory and adapt the alerting/notification provider to your stack:

```bash
cp skills/SKILL.md /path/to/your-project/.claude/commands/triage.md
```

```
/triage payments API returning 503 since 14:30
/triage --sentinel-json snap.json --alert "payments API 503"
```

## The dual-layer pattern

incident-triage is the deterministic layer: alert → cluster state → causation chain in under
1 second. An agent (via MCP or the reference skill) is the reasoning layer: it runs sentinel,
feeds the output to this tool, then adds context from your incident history and playbooks.
The agent is bounded by the evidence — it reasons over facts the CLI established, not guesses.

---

## Contributing

Issues and pull requests welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Design principle: classify before you recommend. OOMKill does not always mean "raise the limit" —
the root cause (limit too low vs. memory leak vs. input spike) determines the correct fix.

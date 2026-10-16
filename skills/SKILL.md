---
name: triage
description: >
  Incident triage — given a normalized alert or free text plus a sentinel JSON
  snapshot, ranks cluster evidence, records gaps, and proposes reviewable response
  steps. Use when an alert fires or a user reports a service is down.
compatibility: Requires kubectl and kubectl-sentinel. incident-triage on PATH is preferred.
allowed-tools: Bash(kubectl-sentinel:*) Bash(incident-triage:*) mcp__kubernetes__kubectl_context mcp__kubernetes__ping mcp__kubernetes__kubectl_get mcp__kubernetes__kubectl_describe mcp__kubernetes__kubectl_logs mcp__kubernetes__kubectl_generic mcp__kubernetes__kubectl_rollout mcp__kubernetes__kubectl_scale
---

**Arguments:** $ARGUMENTS

The rule-based core is vendor-neutral: `kubectl-sentinel` plus `incident-triage`, or the
[GreenerPlatform MCP server](https://github.com/GreenerPlatform/greenerplatform-mcp).
For PagerDuty incident IDs, add the steps in
[pagerduty-enrichment.md](pagerduty-enrichment.md).

## Argument parsing

- Empty → ask for alert description
- Free text → alert description (example: `payments API returning 503 since 14:30`)
- `--sentinel-json <path>` → skip live sentinel
- `-n <namespace>` → scope sentinel
- `--context <name>` → kubeconfig context for sentinel
- `--pd-incident <id>` → run [pagerduty-enrichment.md](pagerduty-enrichment.md) first

## Phase 0 — Pre-flight

Stop on the first failure.

1. `mcp__kubernetes__kubectl_context(operation="get")`. If no context, stop with an error.
2. `mcp__kubernetes__ping()`. If ping fails, stop with an error.
3. Run `kubectl get ns --request-timeout=5s`. If credentials fail, stop and show the first error line.
4. `command -v incident-triage`. If missing, use Phase 1b.

## Phase 1a — incident-triage on PATH

1. Parse service, namespace, alert type, and start time from the alert. If namespace is unknown, ask once.
2. If no `--sentinel-json`, run `kubectl-sentinel --json [-n <namespace>] [--context <name>] > /tmp/sentinel-snap.json`. Exit codes 0, 1, and 2 are valid.
3. Run:

```bash
incident-triage \
  --sentinel-json /tmp/sentinel-snap.json \
  --alert "<alert text or /tmp/pd-alert.json>" \
  [--namespace <ns>]
```

Exit codes: `0` direct match; `1` missing both inputs; `2` bad input; `3` no direct match (use confidence LOW). Do not show raw JSON to the user.

## Phase 1b — Fallback without incident-triage

Run sentinel, classify the alert with keyword tables from `incident_triage.py`, and rank
findings by section priority. State confidence explicitly. Match the Phase 2 report shape.

## Phase 2 — Render report

Render sentinel findings first (same layout as `/sentinel`), then analysis.

Include: alert header, confidence with one-sentence reason, causation chain as **candidate**
hypotheses, parallel findings, fix plan P1–P3, and evidence gaps from the JSON.

Rules:

- Do not paste raw JSON or full kubectl output.
- Treat `root_cause` and `causation_chain` as compatibility fields, not verified causation.
- Use real resource names from sentinel output in commands.
- If exit code is `3` or confidence is low, say root cause is unclear and list live checks.
- Mark cross-service links as INFERRED with a verify command unless logs or traces confirm them.
- Optional PagerDuty block: [pagerduty-enrichment.md](pagerduty-enrichment.md).

For the full report skeleton and classification tables, see
[triage-report-template.md](triage-report-template.md). Prefer the sentinel
`recommendation` field when present.

## Execute (writes)

One write per user confirmation. After P1, run rollout status and pod get. Read-only
kubectl calls do not need confirmation.

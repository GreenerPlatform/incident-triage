# Output Schema — incident-triage v1.1

This file defines the JSON interface between the `incident-triage` CLI tool and any
consuming layer (an AI agent via MCP, a CI pipeline, or custom tooling).

---

## Input: alert descriptor

Passed to `incident-triage` as `--alert <file.json>`, or parsed from free text.

```json
{
  "alert_source": "pagerduty | alertmanager | opsgenie | grafana | webhook | freetext",
  "alert_name": "payments-api SLO breach — error rate 12%",
  "service": "payments-api",
  "namespace": "payments",
  "start_time": "2026-03-31T14:32:00Z",
  "severity": "critical | warning",
  "labels": { "env": "prod", "team": "payments" },
  "raw_body": "<original alert text or JSON>"
}
```

`namespace` may be `null` if not determinable from the alert. The tool will emit a
warning to stderr and produce low-confidence output.

Optional fields (used by the reasoning layer for focused correlation):

```json
{
  "emitting_service": "api-gateway",
  "dependencies": ["auth-service", "db-proxy"],
  "playbook_url": "https://your-wiki/playbooks/api-gateway"
}
```

---

## Input: sentinel snapshot

Schema v1.0 — produced by `kubectl-sentinel --json`.
See [GreenerPlatform/kubectl-sentinel](https://github.com/GreenerPlatform/kubectl-sentinel).

---

## Output: triage result

```json
{
  "schema_version": "1.1",
  "generated_at": "<ISO8601>",
  "alert": {
    "source": "pagerduty | alertmanager | opsgenie | grafana | webhook | freetext",
    "name": "<alert name>",
    "service": "<service name | null>",
    "namespace": "<namespace | null>",
    "emitting_service": "<service that emits the alert metric | null>",
    "dependencies": ["<downstream services>"],
    "playbook_url": "<URL | null>",
    "start_time": "<ISO8601 | null>",
    "severity": "critical | warning"
  },
  "sentinel_summary": {
    "context": "<kubeconfig context>",
    "scope": "all namespaces | namespace: <name>",
    "critical": 0,
    "warn": 0,
    "ok": 0
  },
  "correlation": {
    "alert_type": "slo_burn_service | high_error_rate | service_unavailable | crash_loop | oom | latency_spike | kube_app_health | kube_resource | kube_storage | missing_metric | argocd_health | unknown",
    "matched_findings": [
      {
        "section": "PODS | WORKLOADS | HTTP | EVENTS | JOBS | PDBS | QUOTAS | DNS | CERTS | ...",
        "severity": "CRITICAL | WARN",
        "message": "<sentinel finding message>",
        "relevance": "direct | contributing",
        "relevance_reason": "<why this finding is relevant to the alert>"
      }
    ],
    "unmatched_alert": false
  },
  "what_changed": {
    "detected": true,
    "summary": "<one-line likely trigger + how long before the alert>",
    "trigger": {
      "section": "PODS | WORKLOADS | EVENTS | ...",
      "message": "<sentinel finding message>",
      "reason": "<event reason, e.g. BackOff, FailedMount>",
      "change_type": "config change | image/registry change | deployment rollout | resource change | capacity/scheduling change | quota change | health/rollout change | recent change surfaced by <SECTION>",
      "event_time": "<ISO8601>",
      "seconds_before_alert": 135
    },
    "signals": [ "<up to 5 change candidates, earliest first, same shape as trigger>" ],
    "method": "temporal correlation of sentinel event timestamps vs alert start time (deterministic; no external lookups)"
  },
  "causation_chain": [
    {
      "level": 1,
      "label": "root_cause",
      "description": "<what caused the alert>",
      "evidence": "<sentinel finding that supports this>"
    },
    {
      "level": 2,
      "label": "intermediate",
      "description": "<how the root cause propagated>",
      "evidence": "<sentinel finding>"
    },
    {
      "level": 3,
      "label": "symptom",
      "description": "<user-visible degradation>",
      "evidence": "<alert source>"
    },
    {
      "level": 4,
      "label": "alert",
      "description": "Alert triggered: <alert name>",
      "evidence": "Start time: <ISO8601>"
    }
  ],
  "fix_plan": {
    "p1": {
      "action": "<stop the bleeding — immediate action>",
      "command": "<complete kubectl command | null>",
      "expected_outcome": "<what healthy state looks like>"
    },
    "p2": {
      "action": "<confirm recovery>",
      "command": "kubectl get pods -n <namespace> -w",
      "expected_outcome": "<what you expect to see>"
    },
    "p3": {
      "action": "<prevent recurrence>",
      "command": "<kubectl or config change | null>",
      "expected_outcome": "<what protection this provides>"
    }
  },
  "blast_radius": "<what else is affected by the same root cause>",
  "confidence": "high | medium | low",
  "confidence_reason": "<one sentence explaining the confidence level>"
}
```

---

## Confidence levels

| Level | Criteria |
|-------|---------|
| `high` | Direct CRITICAL finding with event timestamp within 5 minutes of alert start |
| `medium` | Direct CRITICAL finding but no timestamp correlation |
| `low` | No direct match — causation chain is a hypothesis |

## Alert types

| Type | Matched by |
|------|-----------|
| `slo_burn_probe` | probe, correctness, workflowstatus, measured at probe |
| `slo_burn_service` | burn rate, availability, measured at service, error budget |
| `kube_app_health` | crashloopbackoff, notready, replicasmismatch, kubedeployment |
| `kube_resource` | oomkilled, memory pressure, cpu pressure |
| `kube_storage` | pvc, persistent volume, fillingup |
| `argocd_health` | argocd, outofsync, argoappnothealthy |
| `high_error_rate` | error rate, 5xx, 500, 502, 503, 504, slo breach |
| `service_unavailable` | unavailable, down, no endpoints, 0 replicas |
| `latency_spike` | latency, timeout, p99, p95, slow |
| `oom` | oom, out of memory |
| `crash_loop` | restart count, restarting, exit code |
| `missing_metric` | missing, absent, no data |
| `unknown` | default when no keyword matches |

## Exit codes

| Code | When |
|------|------|
| `0` | Triage complete, valid output |
| `1` | Namespace unknown — provide `--namespace` |
| `2` | Sentinel snapshot missing or invalid |
| `3` | No direct findings match alert — low confidence output produced |

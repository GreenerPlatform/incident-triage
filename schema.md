# JSON Contract — CLI 1.3.2 / output schema 1.2

This file defines the JSON interface between the `incident-triage` CLI tool and any
consuming layer (an AI agent via MCP, a CI pipeline, or custom tooling).

---

## Input: alert descriptor

Passed to `incident-triage` as `--alert <file.json>`, or parsed from free text.

```json
{
  "alert_source": "<informational source name>",
  "alert_name": "payments-api SLO breach — error rate 12%",
  "service": "payments-api",
  "namespace": "payments",
  "start_time": "2026-03-31T14:32:00Z",
  "severity": "critical | warning",
  "labels": { "env": "prod", "team": "payments" },
  "raw_body": "<original alert text or JSON>"
}
```

`namespace` may be `null` if not determinable from the alert. The tool emits a warning,
but namespace absence has no dedicated exit code. Vendor-native payloads are not parsed;
an adapter must map them to this normalized descriptor.

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

Produced by `kubectl-sentinel --json`. Schema 1.2 is the current tested input. Older
1.0/1.1 snapshots are accepted on a best-effort basis; the tool does not perform complete
structural JSON Schema validation.
See [GreenerPlatform/kubectl-sentinel](https://github.com/GreenerPlatform/kubectl-sentinel).

---

## Output: triage result

```json
{
  "schema_version": "1.2",
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
    "alert_type": "slo_burn_probe | slo_burn_service | high_error_rate | service_unavailable | crash_loop | oom | latency_spike | kube_app_health | kube_resource | kube_storage | missing_metric | argocd_health | unknown",
    "matched_findings": [
      {
        "section": "PODS | WORKLOADS | HTTP | EVENTS | JOBS | PDBS | QUOTAS | DNS | CERTS | ...",
        "severity": "CRITICAL | WARN",
        "message": "<sentinel finding message>",
        "relevance": "direct | contributing | parallel",
        "relevance_reason": "<why this finding is relevant to the alert>",
        "signals": {
          "restart_count": "<integer | omitted>",
          "exit_code": "<integer | omitted>",
          "replicas_ready": "<integer | omitted>",
          "replicas_desired": "<integer | omitted>",
          "last_event_age_seconds": "<integer | omitted>"
        },
        "subjects": [
          { "kind": "<kind>", "namespace": "<namespace>", "name": "<name>", "uid": "<uid>" }
        ]
      }
    ],
    "unmatched_alert": false
  },
  "parallel_findings": [
    {
      "section": "JOBS",
      "severity": "CRITICAL",
      "message": "<unrelated CRITICAL finding>",
      "recommendation": "<candidate next step | null>",
      "relevance_reason": "<why this is separate from the primary chain>"
    }
  ],
  "what_changed": {
    "detected": true,
    "summary": "<one-line likely trigger + how long before the alert>",
    "trigger": {
      "section": "PODS | WORKLOADS | EVENTS | ...",
      "message": "<sentinel finding message>",
      "reason": "<event reason, e.g. BackOff, FailedMount>",
      "change_type": "config change | image/registry change | deployment rollout | resource change | capacity/scheduling change | quota change | health/rollout change | recent change surfaced by <SECTION>",
      "event_time": "<ISO8601 | null>",
      "seconds_before_alert": "<integer | null>"
    },
    "signals": [ "<up to 5 change candidates, earliest first, same shape as trigger>" ],
    "method": "temporal correlation of sentinel event timestamps vs alert start time"
  },
  "causation_chain": [
    {
      "level": 1,
      "label": "root_cause",
      "description": "<highest-ranked candidate cause>",
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
      "action": "<highest-priority evidence or response step>",
      "command": "<candidate command | null>",
      "expected_outcome": "<evidence or state the operator should review>"
    },
    "p2": {
      "action": "<capture current workload state>",
      "command": "kubectl get pods -n <namespace> -o wide",
      "expected_outcome": "<state available for operator review>"
    },
    "p3": {
      "action": "<review related evidence or recurrence controls>",
      "command": "<candidate command | null>",
      "expected_outcome": "<validated prevention decision>"
    }
  },
  "blast_radius": "<observed related impact, or undetermined from available evidence>",
  "confidence": "high | medium | low",
  "confidence_reason": "<one sentence explaining the correlation strength>",
  "evidence_gaps": [
    {
      "code": "historical_incident | collector_degraded",
      "collection_status": "failed | partial | not_available",
      "check_id": "<optional section or check ID>",
      "message": "<evidence limitation>"
    }
  ]
}
```

---

## Interpretation

`causation_chain` is a compatibility name. `root_cause` and `intermediate` entries are
hypotheses unless logs, traces, owner references, deployment history, or another explicit
dependency record verifies causation. Confidence measures correlation strength, not the
probability that the proposed cause is correct.

Subject matching is token-based. It does not validate a complete UID ownership graph.
Namespace overlap alone must not be treated as causal proof.

The schema version covers the core contract. Additive optional fields may be introduced
without a version bump; removals, type changes, or semantic changes require a bump.

---

## Confidence levels

| Level | Criteria |
|-------|---------|
| `high` | Direct CRITICAL correlation with an event timestamp within 5 minutes of alert start |
| `medium` | Direct CRITICAL finding but no timestamp correlation |
| `low` | No direct match; any chain is a weak hypothesis |

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
| `0` | Full triage completed with a direct match; namespace may still be unknown |
| `1` | Invoked without both required inputs |
| `2` | One input is missing, the snapshot is unreadable/invalid, or argument parsing failed |
| `3` | Full triage completed without a direct finding |

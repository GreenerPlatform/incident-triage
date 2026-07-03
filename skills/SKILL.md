---
name: triage
description: >
  Incident triage — given an alert (PagerDuty, free text, or a sentinel JSON
  snapshot), finds the root cause in the cluster, builds a causation chain, and
  delivers a prioritised fix plan with concrete kubectl commands. Use when an alert
  fires or a user reports a service is down. Invokes /sentinel internally; accepts
  a pre-collected sentinel JSON snapshot.
compatibility: Requires kubectl and kubectl-sentinel. incident-triage (Python CLI)
  is optional — Phase 1b fallback works without it.
allowed-tools: Bash(kubectl-sentinel:*) Bash(incident-triage:*) mcp__pagerduty-mcp__get_incident mcp__pagerduty-mcp__list_incidents mcp__pagerduty-mcp__list_alerts_from_incident mcp__pagerduty-mcp__list_incident_notes mcp__pagerduty-mcp__get_past_incidents mcp__pagerduty-mcp__get_related_incidents mcp__pagerduty-mcp__get_outlier_incident mcp__pagerduty-mcp__list_change_events mcp__kubernetes__kubectl_context mcp__kubernetes__ping mcp__kubernetes__kubectl_get mcp__kubernetes__kubectl_describe mcp__kubernetes__kubectl_logs mcp__kubernetes__kubectl_generic mcp__kubernetes__kubectl_rollout mcp__kubernetes__kubectl_scale
---

**Arguments:** $ARGUMENTS

> **Reference integration.** This skill is one worked example of the reasoning layer:
> Claude Code as the runtime, PagerDuty as the incident source. The deterministic core
> (`kubectl-sentinel` + `incident-triage`) is vendor-neutral — swap the PagerDuty phases
> for Alertmanager/Opsgenie/Grafana, or drive the same CLIs from any agent via the
> GreenerPlatform MCP server. Nothing below is required to use the tools.

---

## Argument parsing

- Empty → prompt user for alert description
- Free text → treat as alert description (e.g. "payments API returning 503 since 14:30")
- `--pd-incident <id>` → fetch live incident from PagerDuty by ID; runs Phase 0.5 before Phase 1
- `--sentinel-json <path>` → use this pre-collected snapshot, skip live sentinel invocation
- `-n <namespace>` → scope sentinel to this namespace (overrides namespace extracted from alert or PD incident)
- `--context <name>` → pass to kubectl-sentinel for a specific kubeconfig context

---

## Phase 0.5 — PagerDuty fetch (only if `--pd-incident` provided)

**Step 1 — Fetch the incident and enrich in parallel.**

Call all three simultaneously:
- `mcp__pagerduty-mcp__get_incident` with the provided ID
- `mcp__pagerduty-mcp__list_alerts_from_incident` — alert payload often contains metric labels, namespace, environment
- `mcp__pagerduty-mcp__list_incident_notes` — engineers may have added namespace or context

Collect: title, body.details, alert labels, note bodies. This is the raw material for namespace extraction.

**Step 2 — Extract namespace.**

Search in this order — stop at first match:
1. `-n <namespace>` argument → use directly
2. Alert payload labels from `list_alerts_from_incident` → look for `namespace`, `kubernetes_namespace`, `exported_namespace`
3. Incident notes from `list_incident_notes` → same regex patterns
4. `incident.body.details` — `namespace[=:\s]+(\w[\w-]+)` or `kubernetes_namespace[=\s]+(\w[\w-]+)`
5. `incident.title` — regex `namespace[=:\s]+(\w[\w-]+)` or `in (\w[\w-]+) namespace`

If namespace found → sentinel runs scoped with `-n <namespace>`.
If still not found → sentinel runs cluster-wide. Do not ask the user.

**Step 3 — Normalize to alert descriptor and write to temp file.**

Build the JSON object:
- `alert_source` = `"pagerduty"`
- `alert_name` ← `incident.title`
- `service` ← `incident.service.summary`
- `namespace` ← resolved value or `null`
- `start_time` ← `incident.created_at`
- `severity` ← `"critical"` if `incident.urgency == "high"` else `"warning"`
- `labels` ← merged from alert payload labels
- `raw_body` ← `incident.title` + `" "` + `incident.body.details` + alert annotation summary

Write the JSON to `/tmp/pd-alert.json`.

**Step 4 — Continue to Phase 1a.**

Sentinel is invoked with `-n <namespace>` if namespace was resolved, cluster-wide if null.

**Step 5 — PD intelligence enrichment (run in parallel with sentinel invocation).**

Call all four simultaneously while sentinel collects cluster state:
- `mcp__pagerduty-mcp__get_past_incidents` — last 6 months of incidents for this service; extract frequency count and date of most recent prior occurrence
- `mcp__pagerduty-mcp__get_outlier_incident` — whether this incident is statistically unusual for this service
- `mcp__pagerduty-mcp__get_related_incidents` — other incidents correlated by PD's ML (shared alert patterns, same time window)
- `mcp__pagerduty-mcp__list_change_events` with `since` = 24 hours before `incident.created_at` — deployments, config changes, or infra changes near the alert

Record for Phase 2 rendering:
- `frequency`: count + date of last occurrence (e.g., "4th time in 6 months — last: 2026-02-14")
- `outlier_flag`: true/false + PD's reason if provided
- `related_incidents`: list of IDs and titles (max 3)
- `last_change_event`: summary and timestamp of the most recent change event before the alert; delta in minutes; note if change preceded alert by < 30 min

**403 fallback — if Event Intelligence tier not available:**

If `get_past_incidents`, `get_outlier_incident`, or `get_related_incidents` return 403:
- Call `mcp__pagerduty-mcp__list_incidents` filtered by alert name fragment, client-side
- Count matches → frequency; sort by `created_at` → date of last occurrence
- Report as: `"<Nth occurrence — last: YYYY-MM-DD (approximated)"`

---

## Phase 0 — Pre-flight

Run all three checks in order. Stop at the first failure — do not proceed.

**Step 1 — Context.**
`mcp__kubernetes__kubectl_context(operation="get")`
If no active context: `ERROR: No kubectl context configured.`

**Step 2 — API reachability.**
`mcp__kubernetes__ping()`
If ping fails: `ERROR: Cannot reach the Kubernetes API server. Check VPN/proxy.`

**Step 3 — Credential validation.**

```bash
kubectl get ns --request-timeout=5s 2>&1 | head -3
```

- If output lists namespaces → credentials valid, continue
- If output contains `exec: executable ... failed` or `Reauthentication` or `credentials` → credentials expired

On credential failure: surface the error and stop with:
```
ERROR: kubectl credential chain failed — cannot collect cluster state.
<paste the first error line>
Refresh credentials (e.g. `gcloud auth login`, `az aks get-credentials`, or `kubelogin`) then re-run /triage.
```

**Step 4 — Tool availability.**
```bash
command -v incident-triage && echo "incident-triage: found" || echo "incident-triage: not found"
command -v glow && echo "glow: found" || echo "glow: not found"
```
- `incident-triage`: proceed to Phase 1a if found; Phase 1b if not.
- `glow`: if found, write `/tmp/triage-report.md` and run `glow /tmp/triage-report.md` at report end.

---

## Phase 1a — Primary path (incident-triage available)

**Step 1 — Parse the alert.**

If `--sentinel-json` was provided, skip to Step 2 with that file.

Extract from the alert or arguments:
- Service name, namespace, alert type, start time
- If namespace cannot be determined, ask exactly one question before proceeding:
  `"Which namespace is the affected service in?"` — then continue.

**Step 2 — Collect cluster state.**

If no `--sentinel-json` provided:
```bash
kubectl-sentinel --json [-n <namespace>] [--context <name>] > /tmp/sentinel-snap.json
```
Save to a temp file. Exit codes 0, 1, 2 are all valid.

**Step 3 — Run incident-triage.**

```bash
incident-triage \
  --sentinel-json /tmp/sentinel-snap.json \
  --alert "<alert text or path to alert JSON>" \
  [--namespace <ns>]
```

Capture the JSON output. Note the exit code:
- 0 → full triage, proceed to Phase 2
- 1 → namespace unknown — ask the user (one question), rerun with `--namespace`
- 2 → snapshot invalid — re-collect with kubectl-sentinel
- 3 → no direct match — proceed to Phase 2 with confidence: low

**Do not show the raw JSON to the user.** Render it using the Phase 2 format.

---

## Phase 1b — Fallback path (incident-triage not installed)

Note: `incident-triage` not found — using inline correlation.

**Step 1 — Parse the alert manually.**
Extract: service name, namespace, alert type, start time.

Alert type keywords for classification:

| Type | Keywords |
|------|----------|
| `high_error_rate` | error rate, 5xx, 500, 502, 503, 504, slo breach |
| `service_unavailable` | unavailable, down, no endpoints, 0 replicas |
| `latency_spike` | latency, timeout, p99, p95, slow |
| `crash_loop` | restart count, restarting, exit code |
| `oom` | oom, out of memory |
| `kube_app_health` | crashloopbackoff, notready, replicasmismatch |
| `kube_resource` | oomkilled, memory pressure, cpu pressure |
| `kube_storage` | pvc, persistent volume, fillingup |
| `missing_metric` | missing, absent, no data |

**Step 2 — Run sentinel.**
```bash
kubectl-sentinel --json [-n <namespace>] [--context <name>]
```

**Step 3 — Apply correlation rules.**

Section priority by alert type (highest relevance first):

| Alert type | Priority sections |
|------------|------------------|
| `high_error_rate` | HTTP, PODS, WORKLOADS, EVENTS, HPAS |
| `service_unavailable` | WORKLOADS, PODS, HTTP, EVENTS |
| `crash_loop` | PODS, EVENTS, WORKLOADS |
| `oom` | PODS, RESOURCES, EVENTS, NODES |
| `kube_app_health` | PODS, WORKLOADS, EVENTS |
| `kube_resource` | RESOURCES, PODS, NODES |
| `kube_storage` | PVCS, EVENTS, PODS |
| `latency_spike` | HTTP, RESOURCES, PODS, HPAS |

Apply your reasoning beyond these rules:
- Look for correlated patterns (FailedMount + 0 replicas → missing secret)
- Assess cross-namespace blast radius when root cause is node-level
- State confidence and reasoning explicitly

Produce the same causation chain, fix plan, and confidence assessment as Phase 1a.

---

## Phase 2 — Render the INCIDENT TRIAGE report

**Always render the sentinel output first** in the same format as `/sentinel`, then the incident analysis.

```
══ INCIDENT TRIAGE ══
Alert   : <alert name>
Service : <service> (<namespace>)
Time    : <start_time> — <duration since alert>
Source  : incident-triage v1.0 | direct kubectl (fallback)
Confidence: HIGH | MEDIUM | LOW — <one-sentence reason>

── PD INTELLIGENCE ──
  Frequency   : <Nth occurrence in 6 months — last: YYYY-MM-DD | "First occurrence">
  Outlier     : <YES — <reason> | NO — within normal pattern for this service>
  Related     : <incident IDs + titles, or "None">
  Last change : <summary of most recent change event — Δ<N>min before alert | "No changes in 24h">
                <if Δ < 30min: "⚑ Change preceded alert by <N>min — investigate as potential trigger">

── SENTINEL STATE ──
[render sentinel findings using the same table format as /sentinel]
[all 10 sections; OK sections in one row; CRITICAL/WARN expanded]

── CAUSATION CHAIN ──
  Root cause   → <root cause description>
                 Evidence: <sentinel finding or event>

  Via          → <how root cause propagates to the next effect>
                 Mechanism : <synchronous HTTP | async queue | shared database | shared node resource>
                 ⚑ Confidence: CONFIRMED (seen in logs/traces) | INFERRED (architectural assumption)
                 Verify    : <kubectl command to confirm if INFERRED>

  Intermediate → <effect 1>
  Symptom      → <user-visible symptom>
  Alert        → <alert name and trigger>
  Blast radius : <what else is affected>

── ROOT CAUSE CLASSIFICATION ──
  Finding type   : <OOMKill | CrashLoopBackOff | ImagePullBackOff | Pending |
                    FailedMount | HPA at max | Probe failure | Node NotReady | other>
  Classification : <derive from evidence signals below>
  Evidence       : <what supports this classification>
  Next action    : <derived from action rules below — never a generic "restart" or "raise limit">

Classification lookup:

  OOMKill
    LIMIT TOO LOW      : runtime < 5 min before kill AND peer pods stable → safe to raise limit
    POSSIBLE LEAK      : runtime hours/days, memory growing → do NOT raise limit; escalate with memory trend
    INPUT TRIGGERED    : kill correlates with large request burst → cap input size or add streaming

  CrashLoopBackOff (check exit code from kubectl describe Last State)
    APP ERROR (exit 1)    : stack trace in logs → escalate to dev team
    OOM (exit 137)        : reclassify as OOMKill above
    SEGFAULT (exit 139)   : native binary crash → immediate dev escalation
    SIGTERM (exit 143)    : probe killing pod → increase initialDelaySeconds / failureThreshold

  ImagePullBackOff
    REGISTRY AUTH      : imagePullSecret missing or expired → rotate secret and redeploy
    IMAGE NOT FOUND    : tag absent from registry → verify tag; fix pipeline if never published
    NETWORK ISSUE      : registry unreachable from node → check egress firewall / proxy config

  Pending pod
    RESOURCE PRESSURE  : events "Insufficient cpu/memory" → scale node pool or lower requests
    AFFINITY MISMATCH  : events "no nodes matched" → relax rules or label node
    PVC UNBOUND        : PVC in Pending state → check storageclass, provisioner, PV availability

  FailedMount
    SECRET MISSING     : secret absent in namespace → create or copy from source namespace
    CONFIGMAP MISSING  : configmap absent → apply manifest
    PVC MISSING        : PVC deleted or in wrong namespace → restore PVC

  HPA at max replicas
    GENUINE LOAD SPIKE : metrics above target + all replicas at capacity → scale node pool or raise max
    FIXED REPLICAS     : minReplicas == maxReplicas in HPA spec → HPA is a no-op; raise max to unlock
    METRIC BACKEND DOWN: HPA condition ScalingActive=False → investigate metrics-server

  Probe failure
    SLOW STARTUP       : initialDelaySeconds < app boot time → increase initialDelaySeconds
    UNHEALTHY APP      : probe correct but app returning non-200 → check logs
    WRONG PORT/PATH    : probe spec mismatch → fix probe in deployment spec

  Node NotReady
    NETWORK PARTITION  : node isolated, kubelet logs normal → check node network and CNI plugin
    KUBELET DEAD       : kubelet systemd unit inactive → cordon node, investigate OS
    DISK/MEM PRESSURE  : node conditions True → evict pods or add nodes
    OOM CASCADE        : node-level OOMKill of kubelet → cordon node immediately

── FIX PLAN ──
  Playbook: <playbook URL if known, or "None on record">

  P1 (stop bleeding)    : <action>
                          kubectl <command>
                          Expected: <what healthy state looks like>

  P2 (confirm recovery) : <action>
                          kubectl <command>
                          Expected: <what you expect to see>

  P3 (prevent recurrence): <action>
                            <command or config change, or "None identified">

── EXECUTE ──
  P1: <action>
  Command: <exact kubectl command from fix plan>
  Run it now? [yes / no / show only]

── POST-INCIDENT ──
  Should I create a work item for this incident? [yes/no]
  Should I propose a playbook update based on findings? [yes/no/no playbook on record]

── REPORT RENDERING ──
  1. [TERMINAL]  Write /tmp/triage-report.md, then run `glow /tmp/triage-report.md` if glow is installed
  2. [HTML]      incident-triage --output-format html > /tmp/triage.html && xdg-open /tmp/triage.html
  Note: do not upload this report to third-party rendering tools — it contains internal service names,
        namespace topology, and incident details.
```

### Report rules

- Never paste raw JSON or raw kubectl output verbatim
- Causation chain must always have at least two levels — even when root cause is unknown: "Root cause unclear — see matched findings for hypotheses"
- Fix plan commands must use resource names from the sentinel output — no invented names, no `<your-namespace>` placeholders (use the actual namespace from the alert or sentinel scope)
- Confidence must be stated in the header — never omit
- If unmatched_alert is true in the triage JSON, lead the causation chain with: "Alert symptom does not directly map to a sentinel finding — cluster state collected for context"
- **Challenge an implausible root cause — this is the reasoning layer's job.** The deterministic
  tool ranks by section priority + name/namespace overlap; it can present a *correlation* as a root
  cause. Before rendering `causation_chain[0]`, sanity-check it against the alert type: a failed
  batch/CronJob is not a cause of a container-restart or latency alert; a chronic-hygiene finding is
  not an acute cause; "same namespace" is not "caused it". If the tool's root cause is not causally
  plausible for this alert, **demote it**: state `⚑ Tool matched <X> on namespace overlap, but it is
  not a plausible cause of <alert> — treating as a parallel finding`, then lead with the honest
  "root cause unclear" and the real hypotheses. Never launder a namespace coincidence into a
  confident root cause. (The deterministic layer prevents invented cluster state; the reasoning
  layer must prevent implausible correlation — each guards the other.)
- **When confidence is `low` / root cause is `Unknown` / exit code is 3, do not invent a cause.**
  Present `parallel_findings` as separate hypotheses, note that a point-in-time snapshot cannot see a
  *resolved or intermittent* condition, and recommend the live check that would confirm it (pod
  deep-dive: `kubectl get pod -o wide` + `kubectl describe pod` for `restartCount` and
  `lastState.terminated` exit code). Honest absence beats a confident guess.
- Cross-service causation links not confirmed by logs or traces must be marked `⚑ INFERRED` with a concrete verification command
- Root cause classification: always add the `── ROOT CAUSE CLASSIFICATION ──` block when sentinel surfaces a dominant finding. Classify before recommending any fix.

### EXECUTE block — on user confirmation

When the user says yes to the EXECUTE prompt:

**Rule: one write operation per confirmation. State the action, confirm, execute, verify.**

| P1 situation | Tool |
|---|---|
| Restart a crashing deployment | `mcp__kubernetes__kubectl_rollout(subCommand="restart", resourceType="deployment", name, namespace)` |
| Roll back a bad deployment | `mcp__kubernetes__kubectl_rollout(subCommand="undo", resourceType="deployment", name, namespace)` |
| Scale up to restore capacity | `mcp__kubernetes__kubectl_scale(resourceType="deployment", name, namespace, replicas)` |
| Delete failed/evicted pods | `mcp__kubernetes__kubectl_generic(command="delete", resourceType="pods", namespace, flags={"field-selector": "status.phase=Failed"})` |

After executing P1: run `mcp__kubernetes__kubectl_rollout(subCommand="status", ...)` then `mcp__kubernetes__kubectl_get(resourceType="pods", namespace)`. Report result in one line before moving to POST-INCIDENT.

For interactive investigation during triage (logs, describe): use `mcp__kubernetes__kubectl_logs` and `mcp__kubernetes__kubectl_describe` directly — no confirmation needed for read operations.

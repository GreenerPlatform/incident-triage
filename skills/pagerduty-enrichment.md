# PagerDuty enrichment (optional)

Use this add-on when the agent runtime has PagerDuty MCP tools. The core triage path
needs only `kubectl-sentinel` and `incident-triage`. See [SKILL.md](SKILL.md).

## When to run

Run these steps only when the user passes `--pd-incident <id>`.

## Phase 0.5 — Fetch and normalize

**Step 1 — Fetch the incident.**

Call these in parallel:

- `mcp__pagerduty-mcp__get_incident` with the incident ID
- `mcp__pagerduty-mcp__list_alerts_from_incident`
- `mcp__pagerduty-mcp__list_incident_notes`

Collect title, `body.details`, alert labels, and note bodies.

**Step 2 — Resolve namespace.**

Check in order. Stop at the first match.

1. `-n <namespace>` from the user
2. Alert labels: `namespace`, `kubernetes_namespace`, `exported_namespace`
3. Incident notes with the same label keys
4. `incident.body.details` with `namespace[=:\s]+(\w[\w-]+)` or `kubernetes_namespace[=\s]+(\w[\w-]+)`
5. `incident.title` with `namespace[=:\s]+(\w[\w-]+)` or `in (\w[\w-]+) namespace`

If you find a namespace, run sentinel with `-n <namespace>`. If not, run cluster-wide.
Do not ask the user to pick a namespace.

**Step 3 — Write alert descriptor JSON.**

Write `/tmp/pd-alert.json`:

- `alert_source`: `"pagerduty"`
- `alert_name`: `incident.title`
- `service`: `incident.service.summary`
- `namespace`: resolved value or `null`
- `start_time`: `incident.created_at`
- `severity`: `"critical"` if `incident.urgency == "high"`, else `"warning"`
- `labels`: merged alert payload labels
- `raw_body`: title, body details, and alert annotation summary

Continue to sentinel collection and `incident-triage` in [SKILL.md](SKILL.md).

**Step 4 — History enrichment (parallel with sentinel).**

While sentinel runs, call:

- `mcp__pagerduty-mcp__get_past_incidents` (last 6 months for this service)
- `mcp__pagerduty-mcp__get_outlier_incident`
- `mcp__pagerduty-mcp__get_related_incidents`
- `mcp__pagerduty-mcp__list_change_events` with `since` = 24 hours before `incident.created_at`

Record for the report footer:

- `frequency`: count and date of last occurrence
- `outlier_flag`: boolean and PD reason if present
- `related_incidents`: up to 3 IDs and titles
- `last_change_event`: summary, timestamp, minutes before alert (flag if under 30 minutes)

**403 fallback**

If past, outlier, or related calls return 403, use `mcp__pagerduty-mcp__list_incidents`
filtered by alert name fragment. Count matches for frequency. Sort by `created_at` for last
occurrence. Label the line as approximated.

## Report block

When enrichment ran, add this block after the header in the Phase 2 report:

```
── PD INTELLIGENCE ──
  Frequency   : <Nth occurrence in 6 months — last: YYYY-MM-DD | First occurrence>
  Outlier     : <YES — reason | NO — within normal pattern>
  Related     : <IDs and titles | None>
  Last change : <summary — Δ<N>min before alert | No changes in 24h>
```

If a change event preceded the alert by under 30 minutes, note it as a possible trigger.
Do not treat it as confirmed causation.

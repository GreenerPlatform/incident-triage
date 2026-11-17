# Offline evidence pack

Reproducible proof that `incident-triage` returns the same ranked causation result for a fixed kubectl-sentinel snapshot and alert. No live cluster is required.

## Contents

| File | Role |
| --- | --- |
| `sentinel-snapshot.json` | kubectl-sentinel `--json` fixture (payments namespace sample) |
| `alert.json` | Normalized alert descriptor for that incident |
| `expected-triage.json` | Golden triage output (schema-stable fields) |
| `verify.sh` | Runs triage twice and compares to the golden file |

## Verify

From the repository root:

```bash
bash evidence/offline-pack/verify.sh
```

Requirements: Python 3.10+ on `PATH`. The script picks the newest available interpreter.

Success prints `offline evidence pack: PASS` and exits `0`. Drift exits non-zero.

## What is compared

The checker normalizes wall-clock fields before compare:

- `generated_at`
- `correlation.matched_findings[*].signals.last_event_age_seconds`

Everything else must match across two runs and against `expected-triage.json`.

## Limits

- This pack proves offline determinism for the checked-in fixtures. It does not prove that a live cluster collection is correct.
- Collecting a fresh snapshot still needs kubectl-sentinel against a cluster. Commit the JSON here when you want a new golden case.
- Hypothesis labels such as `root_cause` remain hypotheses until an operator confirms them.

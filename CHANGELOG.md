# Changelog

All notable changes to incident-triage are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [1.0.0] — 2026-04-11

Initial public release.

### Added

- Alert classification across 12 alert types: `slo_burn_probe`, `slo_burn_service`, `kube_app_health`, `kube_resource`, `kube_storage`, `argocd_health`, `missing_metric`, `high_error_rate`, `service_unavailable`, `latency_spike`, `oom`, `crash_loop`
- Section priority scoring: sentinel sections ranked by relevance to alert type
- Finding relevance classification: `direct` · `contributing` · `background`
- Alert-service-map scoping: restrict findings to causal scope when `emitting_service` is known
- Known-noisy finding suppression list
- Causation chain builder: root cause → intermediate → symptom → alert
- Fix plan builder: P1 (stop bleeding) · P2 (confirm recovery) · P3 (prevent recurrence)
- P1 command sourced from sentinel `recommendation` field; template fallback when null
- Confidence scoring: `high` · `medium` · `low` with one-sentence reason
- Blast radius assessment across affected sections
- JSON output (schema v1.0)
- HTML output: self-contained report with severity colour coding, no external dependencies
- Exit codes: `0` complete · `1` namespace unknown · `2` snapshot missing · `3` no match (low confidence)
- Free-text alert parsing: extracts service, namespace, and timestamps via regex
- Alert descriptor JSON input support
- `--namespace`: override namespace when not determinable from alert
- `install.sh`: installs to `~/bin` or a custom path
- Python 3.10+ · stdlib only · no pip dependencies
- Test fixtures: `tests/fixtures/sample-report.json` and `tests/fixtures/sample-alert.json`

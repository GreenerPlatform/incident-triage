# Changelog

All notable changes to incident-triage are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [1.2.1] — 2026-07-03

### Changed
- Relicensed to **Apache-2.0** (patent grant + attribution); added `NOTICE`, `TRADEMARKS.md`, and SPDX headers. Copyright standardized to Olawale Ogundiran.
- Module renamed `incident-triage` → `incident_triage.py` so it is importable and packageable. The installed command is still `incident-triage`.
- Docs, schema, and exit-code messages are vendor-neutral (alert sources: PagerDuty / Alertmanager / Opsgenie / Grafana / webhook / freetext; reasoning layer via MCP or a reference skill).

### Added
- **PyPI/pipx** packaging (`pyproject.toml` + `incident-triage` console entry point) and a Trusted-Publishing release workflow — `pipx install incident-triage`.
- **Homebrew** formula template under `packaging/homebrew/`.
- `Documentation voice` standard in `CONTRIBUTING.md`.

_No behavioural change to the triage logic._

---

## [1.2.0] — 2026-07-03

### Added
- **`what_changed` correlation** — a new top-level output section answering *"what changed right before the alert?"* Purely deterministic: it correlates sentinel event timestamps against the alert start time (root causes precede symptoms) and classifies the likely trigger by change type — config (Secret/ConfigMap), image/registry, deployment rollout (ProgressDeadlineExceeded), resource/OOM, scheduling/capacity, quota, or probe/health. No external lookups, no model; fully reproducible for a given (snapshot, alert) pair. Rendered in both JSON and HTML.
- Triage now scores findings from the five new sentinel sections (**JOBS, PDBS, QUOTAS, DNS, CERTS**), wired into the per-alert-type section-priority map.

### Changed
- `schema_version` bumped to **1.1** (additive: new `what_changed` object). All existing fields unchanged.

---

## [1.1.1] — 2026-07-02

### Fixed
- HTML report (`--output-format html`) now shows the `Expected` outcome for each P1/P2/P3 fix step — it was reading the wrong key (`expected` instead of `expected_outcome`) and always rendering blank

### Changed
- `--output-format` now accepts only its documented values (`json`, `html`); the undocumented `text` value previously fell through to JSON silently

### Added
- GitHub Actions CI: byte-compile, `--version`, and the fixtures smoke test (JSON validity + HTML render) on every push and pull request

---

## [1.1.0] — 2026-04-11

### Added
- `extract_signals()` — parses structured signals from sentinel finding messages: `restart_count`, `exit_code` (inferred as 137 for OOMKill), `replicas_ready/desired`, `last_event_age_seconds`; emitted in matched finding output for skill-layer classification
- `--version` flag — prints `incident-triage 1.1.0` and exits

### Changed
- P1 fix plan: when sentinel `recommendation` field is null, emit `kubectl describe pod/<name>` (or `deploy/<name>`) instead of template-filling a guessed command — gather evidence before prescribing a fix
- `VERSION` constant added to script (`VERSION = "1.1.0"`)

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

# Contributing

Issues and pull requests welcome.

## Getting started

```bash
git clone https://github.com/GreenerPlatform/incident-triage
cd incident-triage
bash install.sh ~/bin

# Smoke test (no cluster needed)
python3 incident_triage.py \
  --sentinel-json tests/fixtures/sample-report.json \
  --alert tests/fixtures/sample-alert.json \
  | python3 -m json.tool
```

## Design principles

- **Classify before recommending** — the correct P1 action depends on the class of problem; OOMKill, CrashLoop, and missing secret all need different fixes
- **Deterministic** — same inputs must always produce the same output; no randomness, no LLM calls, no network access
- **Exit codes are a public API** — never change what an exit code means without bumping the major version
- **Use the sentinel recommendation** — the `recommendation` field in sentinel findings is already a complete kubectl command; use it directly as P1 rather than reconstructing it
- **stdlib only** — no pip dependencies; the tool must work on any machine with Python 3.10+

## Smoke test

```bash
python3 incident_triage.py \
  --sentinel-json tests/fixtures/sample-report.json \
  --alert tests/fixtures/sample-alert.json
```

Expected: exit code `0`, JSON output with `confidence: "medium"` or higher, causation chain with at least 2 levels.

## Making changes

1. Fork the repo and create a branch: `git checkout -b fix/your-change`
2. Make your change
3. Run the smoke test to verify JSON output is valid
4. Open a pull request with what you changed and why

## Adding a new alert type

Alert types are defined in `ALERT_TYPE_KEYWORDS` (top of the script). To add a new type:

1. Add an entry to `ALERT_TYPE_KEYWORDS` with a list of keywords
2. Add a corresponding entry to `SECTION_PRIORITY` with the ordered sentinel sections to check
3. Test with a free-text alert that matches your keywords
4. Add a fixture if the alert type has a distinct correlation pattern

## Reporting bugs

Include:
- Python version (`python3 --version`)
- The exact command you ran
- The sentinel JSON file (or a minimal reproducer)
- The alert text or file
- The full output and exit code (`echo $?`)

## Documentation voice

Docs represent production reliability engineering. Keep them firm and clean.

- Lead with the fact, not the feeling. State what it does and the number that proves it.
- Every claim is verifiable — a command, an exit code, a measurement — or it is cut.
- Second person, present tense, active voice. Short sentences.
- Do not use: leverage, robust, seamless, powerful, effortless, delve, game-changing,
  cutting-edge, supercharge, unlock, revolutionary, world-class, "in today's ...".
- No "it's not just X, it's Y" constructions. No emoji in prose.

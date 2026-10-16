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

- **Correlate before recommending** — rank the evidence, preserve uncertainty, and do not
  present a candidate cause as verified causation
- **Reproducible rules** — classifications should remain stable for a fixed snapshot,
  alert, configuration, CLI version, and evaluation time
- **Exit codes are a public API** — never change what an exit code means without bumping the major version
- **Preserve the sentinel recommendation** — copy it without inventing a command, but treat
  it as untrusted operational input that requires review
- **stdlib only** — no pip dependencies; the tool must work on any machine with Python 3.10+

## Smoke test

```bash
python3 incident_triage.py \
  --sentinel-json tests/fixtures/sample-report.json \
  --alert tests/fixtures/sample-alert.json
```

Expected: exit code `0` and valid JSON. This proves process execution and parsing only; it
does not prove causal correctness or command safety.

Run the complete suite:

```bash
python -m unittest discover -s tests -v
```

Add negative fixtures for false matches, degraded evidence, unsafe recommendations, and
schema drift. Before release, verify that `VERSION`, `incident_triage.VERSION`, and
`[project].version` agree and that the documented schema matches `SCHEMA_VERSION`.

## Making changes

1. Fork the repo and create a branch: `git checkout -b fix/your-change`
2. Make your change
3. Run the complete test suite and add a regression fixture
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
- A minimal sanitized sentinel fixture
- A sanitized alert descriptor or free-text alert
- The smallest output excerpt and exit code needed to show the problem

Do not post credentials, tokens, customer data, internal hostnames, or identifying
operational metadata.

## Documentation voice

Docs represent production reliability engineering. Keep them firm and clean.

- Lead with the fact, not the feeling. State what it does and the number that proves it.
- Every claim is verifiable — a command, an exit code, a measurement — or it is cut.
- Second person, present tense, active voice. Short sentences.
- Do not use: leverage, robust, seamless, powerful, effortless, delve, game-changing,
  cutting-edge, supercharge, unlock, revolutionary, world-class, "in today's ...".
- No "it's not just X, it's Y" constructions. No emoji in prose.

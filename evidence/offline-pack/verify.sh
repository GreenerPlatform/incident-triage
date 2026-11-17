#!/usr/bin/env bash
# Offline evidence pack: same fixture inputs must produce schema-stable triage twice.
# Requires Python 3.10+ (matches project metadata). No cluster access.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PACK="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

pick_python() {
  local c ver major minor
  for c in python3.15 python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      ver="$("$c" -c 'import sys; print("%d.%d" % (sys.version_info[0], sys.version_info[1]))')"
      major="${ver%%.*}"
      minor="${ver#*.}"
      if [[ "$major" -gt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -ge 10 ]]; }; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

if ! PYTHON="$(pick_python)"; then
  echo "FAIL: need Python 3.10+ on PATH (found only older interpreters)" >&2
  exit 1
fi

echo "== offline-pack: interpreter =="
"$PYTHON" --version

normalize() {
  "$PYTHON" - "$@" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)

data["generated_at"] = "NORMALIZED"

def scrub(node):
    if isinstance(node, dict):
        if "signals" in node and isinstance(node["signals"], dict):
            node["signals"].pop("last_event_age_seconds", None)
        for value in node.values():
            scrub(value)
    elif isinstance(node, list):
        for item in node:
            scrub(item)

scrub(data)
print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
PY
}

run_triage() {
  local out="$1"
  set +e
  "$PYTHON" incident_triage.py \
    --sentinel-json "$PACK/sentinel-snapshot.json" \
    --alert "$PACK/alert.json" \
    --output-format json >"$out"
  local rc=$?
  set -e
  if [[ "$rc" != "0" && "$rc" != "3" ]]; then
    echo "FAIL: triage exit $rc (stdout in $out)" >&2
    exit 1
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== offline-pack: run 1 =="
run_triage "$TMP/run1.json"
echo "== offline-pack: run 2 =="
run_triage "$TMP/run2.json"

normalize "$TMP/run1.json" >"$TMP/run1.norm.json"
normalize "$TMP/run2.json" >"$TMP/run2.norm.json"
normalize "$PACK/expected-triage.json" >"$TMP/expected.norm.json"

echo "== offline-pack: run1 vs run2 =="
if ! diff -u "$TMP/run1.norm.json" "$TMP/run2.norm.json"; then
  echo "FAIL: triage output drifted between two runs on the same fixtures" >&2
  exit 1
fi

echo "== offline-pack: runs vs expected-triage.json =="
if ! diff -u "$TMP/expected.norm.json" "$TMP/run1.norm.json"; then
  echo "FAIL: triage output drifted from evidence/offline-pack/expected-triage.json" >&2
  exit 1
fi

echo "offline evidence pack: PASS"

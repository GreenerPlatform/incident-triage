#!/usr/bin/env bash
# install.sh — install incident-triage to ~/bin (or a custom path)
# Usage: bash install.sh [<destination-dir>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/incident_triage.py"
INSTALL_DIR="${1:-/usr/local/bin}"
DEST="$INSTALL_DIR/incident-triage"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: incident-triage not found at $SRC" >&2
  exit 1
fi

# Strip CRLF line endings that Windows git may introduce, then install
if [[ -w "$INSTALL_DIR" ]]; then
  tr -d '\r' < "$SRC" > "$DEST"
  chmod +x "$DEST"
else
  echo "Needs sudo to write to $INSTALL_DIR"
  tr -d '\r' < "$SRC" | sudo tee "$DEST" > /dev/null
  sudo chmod +x "$DEST"
fi

echo "Installed incident-triage → $DEST"

# Verify python3 is available
if ! command -v python3 &>/dev/null; then
  echo "WARNING: python3 not found in PATH — incident-triage requires Python 3.10+" >&2
fi

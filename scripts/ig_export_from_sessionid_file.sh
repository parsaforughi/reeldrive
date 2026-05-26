#!/bin/sh
# Paste sessionid into scripts/.bridge_sessionid (one line, gitignored), then:
#   ./scripts/ig_export_from_sessionid_file.sh
set -e
cd "$(dirname "$0")/.."
FILE="scripts/.bridge_sessionid"

if [ ! -f "$FILE" ]; then
  echo "Create $FILE with one line: your instagram sessionid cookie"
  echo "  (Safari/Chrome → instagram.com → DevTools → Cookies → sessionid)"
  exit 1
fi

SESSION_ID=$(tr -d ' \n\r"' < "$FILE")
if [ -z "$SESSION_ID" ]; then
  echo "$FILE is empty"
  exit 1
fi

PY=python3.13
command -v "$PY" >/dev/null 2>&1 || PY=python3
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
fi
. .venv/bin/activate
pip install -q -r scripts/requirements-ig-export.txt

export INSTAGRAM_BRIDGE_SESSION_ID="$SESSION_ID"
python scripts/ig_export_session.py

echo ""
echo "Next: tell the agent «انجام شد» or set Railway:"
echo "  railway variables set INSTAGRAM_BRIDGE_SESSION_ID=\"...\" --service <name>"

#!/bin/sh
# Copy to ig_export_local.sh (gitignored) and fill in credentials:
#   cp scripts/ig_export_local.example.sh scripts/ig_export_local.sh
set -e
cd "$(dirname "$0")/.."

# Option 1: password login (use EMAIL if @handle fails)
export INSTAGRAM_BRIDGE_LOGIN="your_ig_login_or_email"
export INSTAGRAM_BRIDGE_PASSWORD="your_password"
# export INSTAGRAM_2FA_CODE="123456"

# Option 2: browser cookie (skip password API) — see docs/BRIDGE_SETUP_FA.md
# export INSTAGRAM_BRIDGE_SESSION_ID="paste_sessionid_from_browser"

PY=python3.13
command -v "$PY" >/dev/null 2>&1 || PY=python3

if [ ! -d .venv ] || ! .venv/bin/python -c 'import sys; exit(0 if sys.version_info < (3,14) else 1)' 2>/dev/null; then
  rm -rf .venv
  "$PY" -m venv .venv
fi
. .venv/bin/activate
pip install -q -r scripts/requirements-ig-export.txt

python scripts/ig_export_session.py

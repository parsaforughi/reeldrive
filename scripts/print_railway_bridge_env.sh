#!/bin/sh
# Prints Railway variable values from local session file (run on your Mac only).
set -e
cd "$(dirname "$0")/.."
FILE="scripts/.bridge_sessionid"
[ -f "$FILE" ] || { echo "Missing $FILE"; exit 1; }
SID=$(python3 -c "from urllib.parse import unquote; print(unquote(open('$FILE').read().strip()))")
echo "Copy into Railway → Variables:"
echo ""
echo "INSTAGRAM_BRIDGE_ENABLED=true"
echo "INSTAGRAM_BRIDGE_FORCE_LOGIN=false"
echo "INSTAGRAM_BRIDGE_LOGIN=reeldrivebot"
echo "INSTAGRAM_BRIDGE_SESSION_ID=$SID"
echo "# Optional (from same browser cookies page):"
echo "# INSTAGRAM_BRIDGE_CSRFTOKEN=..."
echo "# INSTAGRAM_BRIDGE_MID=..."

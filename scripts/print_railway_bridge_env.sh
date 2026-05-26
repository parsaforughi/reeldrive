#!/bin/sh
set -e
cd "$(dirname "$0")/.."
FILE="scripts/.bridge_sessionid"
[ -f "$FILE" ] || { echo "Missing $FILE"; exit 1; }
SID=$(python3 -c "from urllib.parse import unquote; print(unquote(open('$FILE').read().strip()))")
echo "Railway → Variables → add ONE variable:"
echo ""
echo "INSTAGRAM_BRIDGE_SESSION_ID=$SID"

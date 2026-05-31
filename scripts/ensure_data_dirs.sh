#!/bin/sh
# Creates persistent data directories before bot + dashboard start.
set -e
cd "$(dirname "$0")/.."

DATA="${RAILWAY_VOLUME_MOUNT_PATH:-/app/data}"
mkdir -p "$DATA/sessions" data sessions 2>/dev/null || true

if [ -n "$RAILWAY_ENVIRONMENT" ]; then
  echo "[data] persistent dir: $DATA"
else
  echo "[data] local dir: ./data"
fi

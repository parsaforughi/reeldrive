#!/bin/sh
# یک سرویس Railway: ربات در پس‌زمینه + داشبورد روی PORT (health check)
set -e
cd "$(dirname "$0")/.."
sh scripts/ensure_data_dirs.sh

PYTHON=python
if [ -x /opt/venv/bin/python ]; then
  PYTHON=/opt/venv/bin/python
fi

echo "[start] Telegram bot (background)..."
"$PYTHON" -m bot.main &
BOT_PID=$!

cleanup() {
  echo "[start] Stopping bot (pid $BOT_PID)..."
  kill "$BOT_PID" 2>/dev/null || true
  wait "$BOT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[start] Dashboard on port ${PORT:-8080}..."
exec "$PYTHON" -m dashboard

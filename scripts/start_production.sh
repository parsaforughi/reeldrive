#!/bin/sh
# یک سرویس Railway: ربات در پس‌زمینه + داشبورد روی PORT (health check)
set -e
mkdir -p sessions data

echo "[start] Telegram bot (background)..."
python -m bot.main &
BOT_PID=$!

cleanup() {
  echo "[start] Stopping bot (pid $BOT_PID)..."
  kill "$BOT_PID" 2>/dev/null || true
  wait "$BOT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[start] Dashboard on port ${PORT:-8080}..."
exec python -m dashboard

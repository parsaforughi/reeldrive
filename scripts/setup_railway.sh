#!/bin/sh
# Railway one-time setup (run on your Mac after: npm i -g @railway/cli && railway login)
set -e
cd "$(dirname "$0")/.."

echo "=== Reeldrive Railway setup ==="
echo ""

if ! command -v railway >/dev/null 2>&1; then
  echo "Install Railway CLI:"
  echo "  npm install -g @railway/cli"
  echo "  railway login"
  echo "  railway link"
  exit 1
fi

echo "1) Adding PostgreSQL (persistent DB — connections survive redeploy)..."
railway add --database postgres 2>/dev/null || railway add -d postgres 2>/dev/null || {
  echo "   Could not auto-add Postgres. In dashboard: + New → Database → PostgreSQL"
  echo "   Then link it to your Reeldrive service."
}

echo ""
echo "2) Optional: Volume for SQLite fallback / session files..."
echo "   Dashboard → Service → Volumes → mount path: /app/data"
echo "   Or: railway volume add --mount-path /app/data"
echo ""

echo "3) Required variables (set if missing):"
echo "   TELEGRAM_BOT_TOKEN"
echo "   HIKERAPI_KEY"
echo "   INSTAGRAM_BRIDGE_SESSION_ID"
echo "   DASHBOARD_PASSWORD"
echo "   DASHBOARD_SECRET"
echo ""

echo "4) Deploy:"
railway up --detach 2>/dev/null || echo "   railway up"
echo ""
echo "After deploy, check logs for:"
echo "   Database: PostgreSQL (persistent across deploys)"
echo "   Bridge IG ready (web DM API)"
echo ""
echo "See docs/RAILWAY_DB_FA.md for details."

# دیتابیس پایدار — اتصال پیج بعد از deploy از بین نرود

## سریع (یک بار)

```bash
npm install -g @railway/cli
railway login
railway link
chmod +x scripts/setup_railway.sh
./scripts/setup_railway.sh
```

یا در Dashboard:

1. **+ New → Database → PostgreSQL**
2. Postgres را به سرویس Reeldrive **Link** کن
3. **Redeploy**

---

## روش ۱ — PostgreSQL (پیشنهادی)

Railway خودش `DATABASE_URL` می‌گذارد. ربات آن را به `postgresql+asyncpg://` تبدیل می‌کند.

لاگ موفق:
```
Database: PostgreSQL (persistent across deploys)
```

Health check: `GET /health` → `"database": "postgres", "database_ok": true`

---

## روش ۲ — Volume + SQLite

1. Service → **Volumes** → **Add Volume**
2. Mount path: **`/app/data`**
3. Redeploy

ربات خودکار DB را می‌گذارد: `/app/data/reeldrive.db`  
Session files هم در `/app/data/sessions/` ذخیره می‌شوند.

اگر Volume وصل باشد، Railway متغیر `RAILWAY_VOLUME_MOUNT_PATH` را ست می‌کند.

---

## چک بعد از deploy

| لاگ | وضعیت |
|-----|--------|
| `Database: PostgreSQL` | ✅ اتصال‌ها می‌مانند |
| `Database: SQLite at /app/data (Railway Volume)` | ✅ با Volume |
| `SQLite at /app/data — add Postgres or Volume` | ⚠️ هنوز پایدار نیست |

---

## متغیرهای لازم Railway

```
TELEGRAM_BOT_TOKEN=
APIFY_TOKEN=
INSTAGRAM_BRIDGE_SESSION_ID=
DASHBOARD_PASSWORD=
DASHBOARD_SECRET=
```

`DATABASE_URL` را **دستی نگذار** اگر Postgres Link کردی — Railway خودش می‌دهد.

---

## محلی

```bash
DATABASE_URL=sqlite+aiosqlite:///./data/reeldrive.db
```

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
2. سرویس **Reeldrive** → **Variables**
3. اگر `DATABASE_URL=sqlite...` داری → **حذفش کن**
4. **New Variable** → `DATABASE_URL` = `${{Postgres.DATABASE_PRIVATE_URL}}`  
   (یا از منوی Postgres → **Connect** به Reeldrive)
5. **Redeploy**

---

## روش ۱ — PostgreSQL (پیشنهادی)

ربات اول Postgres را از env می‌خواند (`DATABASE_PRIVATE_URL`, `DATABASE_URL`, `PGHOST`, …).

لاگ موفق:
```
Database: PostgreSQL via DATABASE_PRIVATE_URL (persistent)
Postgres empty — importing from /app/data/reeldrive.db
SQLite → Postgres migration completed
```

اگر Postgres خالی است ولی `/connect` کار کرده → داده‌ها هنوز در **SQLite روی Volume** هستند، نه Postgres. بعد از Link درست + Redeploy، import خودکار انجام می‌شود.

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
| `Database: PostgreSQL via …` | ✅ اتصال‌ها می‌مانند |
| `Postgres URL found in … but bot still uses SQLite` | ❌ `DATABASE_URL=sqlite` را حذف کن |
| `Database: SQLite at /app/data (Volume)` | ⚠️ Postgres وصل نیست — داده روی Volume است |

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

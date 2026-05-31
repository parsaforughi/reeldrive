# دیتابیس پایدار روی Railway (اتصال پیج بعد از deploy از بین نرود)

هر redeploy بدون Postgres/Volume، فایل SQLite روی دیسک موقت پاک می‌شود → `/connect` دوباره لازم است.

---

## روش ۱ — PostgreSQL (پیشنهادی)

1. در Railway پروژه → **+ New** → **Database** → **PostgreSQL**
2. سرویس Postgres را به سرویس Reeldrive **Link** کن (یا `DATABASE_URL` را کپی کن)
3. Railway خودش `DATABASE_URL` می‌گذارد — ربات آن را به `postgresql+asyncpg://` تبدیل می‌کند
4. **Redeploy**

در لاگ باید ببینی: `Database: PostgreSQL (persistent across deploys)`

اتصال پیج‌ها، زبان کاربران و لاگ‌ها **بعد از هر deploy** می‌مانند.

---

## روش ۲ — Volume برای SQLite

اگر Postgres نمی‌خواهی:

1. Railway → سرویس Reeldrive → **Volumes** → **Add Volume**
2. Mount path: **`/app/data`**
3. Redeploy

ربات روی Railway خودکار DB را می‌گذارد: `/app/data/reeldrive.db`

Volume باید روی **همان سرویسی** باشد که `start_production.sh` اجرا می‌شود.

---

## چک

| لاگ | معنی |
|-----|------|
| `Database: PostgreSQL` | ✅ پایدار |
| `Database: SQLite at /app/data` | ✅ اگر Volume وصل باشد |
| `Database: SQLite local` | فقط مک — Railway نیست |

---

## نکته

`INSTAGRAM_BRIDGE_SESSION_ID` جدا از DB است — در **Variables** می‌ماند و با deploy پاک نمی‌شود.

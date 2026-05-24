# Reeldrive

ربات تلگرام شبیه [@Regrambot](https://t.me/Regrambot) — دانلود از اینستاگرام + اتصال پیج با کد تأیید.

**دایرکت دانلود (لینک)** از **Apify** — `APIFY_TOKEN` در Railway.  
**اتصال پیج** از اکانت اینستاگرام bridge ربات (`INSTAGRAM_BRIDGE_*`).  
پروفایل/استوری اختیاری با `INSTAGRAM_USERNAME` (instagrapi).

## امکانات

- **دایرکت دانلود:** لینک پست/ریل/کاروسel، استوری، هایلایت، پروفایل HD
- **اتصال پیج:** `/connect` → کد → DM به اکانت bridge در IG → دریافت لینک‌ها در تلگرام
- **زیپ:** `zip stories user` | `zip posts user`
- **هشتگ:** `#tag` یا `hashtag name`
- **لیست نظارت:** `/watch add|list|remove` (اتصال پیج لازم)

## Railway

**سرویس Web (داشبورد)** — `railway.toml`  
- Start: `python -m dashboard`  
- دامنه: [https://reeldrive.up.railway.app](https://reeldrive.up.railway.app)  
- Railway خودش `PORT` را ست می‌کند (معمولاً 8080 نیست؛ کد از `PORT` استفاده می‌کند)

**سرویس Worker (ربات)** — `railway.worker.toml`  
- در Railway → Settings → Config file path: `railway.worker.toml`  
- Start: `python -m bot.main` (بدون URL عمومی)

Variables **هر دو سرویس:** `DATABASE_URL` (Postgres توصیه می‌شود)، `TELEGRAM_BOT_TOKEN`, `APIFY_TOKEN`, `INSTAGRAM_BRIDGE_*`  
Variables **فقط Web:** `DASHBOARD_PASSWORD`, `DASHBOARD_SECRET`

Volume: `sessions/` و `data/` (روی Worker؛ Web فقط DB مشترک لازم دارد)

## داشبورد ادمین

UI با تم Telegram × Instagram: کاربران، لاگ زنده، اشتراک‌ها (free/pro/premium)، وضعیت Apify/IG.

```bash
python -m dashboard
# → http://localhost:8080
```

## محلی

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m bot.main   # ترمینال ۱
python -m dashboard  # ترمینال ۲
```

## منوی تلگرام (مثل Regrambot)

دکمه **Menu** کنار چت: `/start`, `/connect`, `/directdownload`, `/myinstagram`, `/search`, `/unfollowers`, `/feed`, `/settings`, `/help`, `/privacy`

| دستور | کار |
|--------|-----|
| `/start` | 🏠 منوی اصلی |
| `/connect` | 🔐 اتصال پیج |
| `/directdownload` | ⚡ دایرکت دانلود |
| `/myinstagram` | 📩 پیج متصل |
| `/search` | 🔍 جستجو |
| `/disconnect` | قطع اتصال |

## امنیت

توکن و پسورد را commit نکن. اگر توکن لو رفت: BotFather → `/revoke`.

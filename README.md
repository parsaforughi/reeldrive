# Reeldrive

ربات تلگرام شبیه [@Regrambot](https://t.me/Regrambot) — دانلود از اینستاگرام + اتصال پیج با کد تأیید.

**دایرکت دانلود (لینک)** از **Apify** — `APIFY_TOKEN` در Railway.  
**اتصال پیج** از اکانت اینستاگرام bridge ربات (`INSTAGRAM_BRIDGE_*`).  
پروفایل/استوری اختیاری با `INSTAGRAM_USERNAME` (instagrapi).

## امکانات

- **دایرکت دانلود:** لینک پست/ریل/کاروسel، استوری، هایلایت، پروفایل HD
- **اتصال پیج:** `/connect` → کد → DM به اکانت bridge در IG → دریافت لینک‌ها در تلگرام
- **زیپ:** `zip stories user` | `zip posts user`
- **فالووینگ:** `/following` یا `following user` — لیست کسانی که آن آیدی فالو کرده. اول از Apify (بدون نیاز به لاگین IG، فقط پیج پابلیک) امتحان می‌شود؛ اگر Apify نبود/fail شد، به instagrapi (نیاز به اتصال IG سرویس) برمی‌گردد.
- **هشتگ:** `#tag` یا `hashtag name`
- **لیست نظارت:** `/watch add|list|remove` (اتصال پیج لازم)

## Railway

**یک سرویس (پیش‌فرض)** — `railway.toml`  
- Start: `sh scripts/start_production.sh` → ربات + داشبورد با هم  
- دامنه: [https://reeldrive.up.railway.app](https://reeldrive.up.railway.app)  
- **DB پایدار:** `./scripts/setup_railway.sh` یا Postgres در Dashboard — [راهنما](docs/RAILWAY_DB_FA.md)

**دو سرویس جدا (اختیاری، پایدارتر)**  
- Web: `railway.web.toml` → فقط `python -m dashboard`  
- Worker: `railway.worker.toml` → فقط `python -m bot.main`  
- در Railway برای هر سرویس مسیر Config file را جدا بگذار

Variables **هر دو سرویس:** `DATABASE_URL` (Postgres توصیه می‌شود — [راهنما](docs/RAILWAY_DB_FA.md))، `TELEGRAM_BOT_TOKEN`, `APIFY_TOKEN`, `INSTAGRAM_BRIDGE_*`  
Variables **فقط Web:** `DASHBOARD_PASSWORD`, `DASHBOARD_SECRET`

Volume: `sessions/` و `data/` (روی Worker؛ Web فقط DB مشترک لازم دارد)

## پرداخت آنلاین Pro (بله‌پی)

اشتراک Pro علاوه بر Telegram Stars و کارت‌به‌کارت دستی، می‌تواند از طریق یک فروشگاه WooCommerce با افزونه بله‌پی به‌صورت خودکار فعال شود — [راهنمای کامل راه‌اندازی](docs/BALEPAY_SETUP_FA.md).

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

دکمه **Menu** کنار چت: `/start`, `/connect`, `/directdownload`, `/myinstagram`, `/search`, `/following`, `/unfollowers`, `/feed`, `/settings`, `/help`, `/privacy`

| دستور | کار |
|--------|-----|
| `/start` | 🏠 منوی اصلی |
| `/connect` | 🔐 اتصال پیج |
| `/directdownload` | ⚡ دایرکت دانلود |
| `/myinstagram` | 📩 پیج متصل |
| `/search` | 🔍 جستجو |
| `/following` | ➡️ بفرست آیدی، لیست فالووینگ‌هاش رو بده |
| `/disconnect` | قطع اتصال |

## امنیت

توکن و پسورد را commit نکن. اگر توکن لو رفت: BotFather → `/revoke`.

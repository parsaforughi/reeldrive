# Reeldrive

ربات تلگرام شبیه [@Regrambot](https://t.me/Regrambot) — دانلود از اینستاگرام + اتصال پیج با کد تأیید.

**دایرکت دانلود (لینک)** از **HikerAPI** — `HIKERAPI_KEY` در Railway.
**اتصال پیج** از اکانت اینستاگرام bridge ربات (`INSTAGRAM_BRIDGE_*`).
**اتصال پیشرفته** با session رمزگذاری‌شده هر کاربر برای دسترسی مجاز به پیج‌های خصوصی.

## امکانات

- **دایرکت دانلود:** لینک پست/ریل/کاروسel، استوری، هایلایت، پروفایل HD
- **اتصال پیج:** `/connect` → کد → DM به اکانت bridge در IG → دریافت لینک‌ها در تلگرام
- **اتصال پیشرفته:** `/advancedconnect` → Mini App امن → استوری و Following پیج‌های خصوصی‌ای که اکانت متصل دنبال می‌کند
- **زیپ:** `zip stories user` | `zip posts user`
- **فالووینگ:** `/following` یا `following user` — عمومی از HikerAPI؛ خصوصی فقط از session همان کاربر و بدون استفاده از session اکانت bridge.
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

Variables **هر دو سرویس:** `DATABASE_URL` (Postgres توصیه می‌شود — [راهنما](docs/RAILWAY_DB_FA.md))، `TELEGRAM_BOT_TOKEN`, `HIKERAPI_KEY`, `INSTAGRAM_BRIDGE_*`, `INSTAGRAM_SESSION_ENCRYPTION_KEY`
Variables **فقط Web:** `DASHBOARD_PASSWORD`, `DASHBOARD_SECRET`

راه‌اندازی و تست اتصال پیشرفته: [docs/ADVANCED_CONNECT_FA.md](docs/ADVANCED_CONNECT_FA.md)

Volume: `sessions/` و `data/` (روی Worker؛ Web فقط DB مشترک لازم دارد)

## داشبورد ادمین

UI با تم Telegram × Instagram: کاربران، لاگ زنده، اشتراک‌ها (free/pro/premium)، وضعیت HikerAPI/IG.

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

دکمه **Menu** کنار چت: `/start`, `/connect`, `/advancedconnect`, `/directdownload`, `/myinstagram`, `/search`, `/following`, `/unfollowers`, `/feed`, `/settings`, `/help`, `/privacy`

| دستور | کار |
|--------|-----|
| `/start` | 🏠 منوی اصلی |
| `/connect` | 🔐 اتصال پیج |
| `/advancedconnect` | 🔓 اتصال امن برای محتوای خصوصی مجاز |
| `/directdownload` | ⚡ دایرکت دانلود |
| `/myinstagram` | 📩 پیج متصل |
| `/search` | 🔍 جستجو |
| `/following` | ➡️ بفرست آیدی، لیست فالووینگ‌هاش رو بده |
| `/disconnect` | قطع اتصال |

## امنیت

توکن و پسورد را commit نکن. پسورد اینستاگرام در دیتابیس ذخیره نمی‌شود؛ session پیشرفته با `INSTAGRAM_SESSION_ENCRYPTION_KEY` رمزگذاری می‌شود. اگر توکن ربات لو رفت: BotFather → `/revoke`.

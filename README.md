# Reeldrive

ربات تلگرام شبیه [@Regrambot](https://t.me/Regrambot) — دانلود از اینستاگرام + اتصال پیج با کد تأیید.

**همه امکانات فعلاً رایگان** — بدون Apify و بدون اشتراک پولی. فقط `instagrapi` و اکانت اینستاگرام خودت.

## امکانات

- **دایرکت دانلود:** لینک پست/ریل/کاروسel، استوری، هایلایت، پروفایل HD
- **اتصال پیج:** `/connect` → کد → DM به اکانت bridge در IG → دریافت لینک‌ها در تلگرام
- **زیپ:** `zip stories user` | `zip posts user`
- **هشتگ:** `#tag` یا `hashtag name`
- **لیست نظارت:** `/watch add|list|remove` (اتصال پیج لازم)

## Railway

1. Repo: https://github.com/parsaforughi/reeldrive
2. Variables: `TELEGRAM_BOT_TOKEN`, `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD`
3. برای پل تأیید: `INSTAGRAM_BRIDGE_USERNAME` / `PASSWORD` (یا همان سرویس)
4. `INSTAGRAM_BRIDGE_DISPLAY` — نام نمایشی در پیام‌ها
5. Volume روی `sessions/` و `data/`
6. Start: `python -m bot.main`

## محلی

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m bot.main
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

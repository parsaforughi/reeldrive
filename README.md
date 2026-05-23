# Regram Pro

ربات تلگرام برای دانلود پروفایل، استوری و پست/ریل اینستاگرام (شبیه Regrambot).

## راه‌اندازی محلی

```bash
cd "regram pro"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# توکن و اکانت اینستاگرام را در .env پر کن
python -m bot.main
```

## دیپلوی روی Railway

1. پروژه را در [Railway](https://railway.app) بساز و این ریپو را وصل کن (یا `railway up` از CLI).
2. در **Variables** این‌ها را اضافه کن:

| متغیر | توضیح |
|--------|--------|
| `TELEGRAM_BOT_TOKEN` | توکن از @BotFather |
| `INSTAGRAM_USERNAME` | اکانت IG ربات |
| `INSTAGRAM_PASSWORD` | پسورد همان اکانت |
| `BOT_NAME` | اختیاری — نام نمایشی |

3. سرویس به‌صورت **Worker** اجرا می‌شود (`python -m bot.main` با polling).
4. Volume (اختیاری): مسیر `sessions/` را mount کن تا سشن اینستاگرام بعد از ری‌استارت بماند.

## امنیت

- توکن را هرگز در گیت commit نکن.
- اگر توکن لو رفت، در BotFather با `/revoke` توکن جدید بگیر.

## دستورات ربات

- `/start` — خوش‌آمد
- `/help` — راهنما
- `/status` — وضعیت اتصال اینستاگرام

ارسال یوزرنیم یا لینک پست/ریل اینستاگرام.

# راه‌اندازی دایرکت اینستاگرام → تلگرام

برای اینکه کاربر لینک را در **دایرکت @reeldrivebot** بفرستد و در **تلگرام** بگیرد، سرور باید به اینستاگرام لاگین باشد.

ریل‌وی با **پسورد** معمولاً لاگین نمی‌شود (IP بلاک). راه‌حل: **یک‌بار** session از مک شخصی.

## ۱) روی مک خودت (خانه)

```bash
cd "/Users/parsa/Desktop/regram pro"

# Python 3.13 — not 3.14 (pydantic build fails on 3.14)
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements-ig-export.txt

# اگر با ایمیل لاگین می‌کنی:
export INSTAGRAM_BRIDGE_LOGIN="email@example.com"
# یا یوزرنیم API:
# export INSTAGRAM_BRIDGE_LOGIN="reeldrivebot"

export INSTAGRAM_BRIDGE_PASSWORD="پسورد_اینستاگرام"
python scripts/ig_export_session.py
```

فایل ساخته می‌شود: `sessions/bridge.json`

## ۲) Railway

1. **Volume** بساز و به سرویس وصل کن
2. Mount path: `/app/sessions`
3. فایل `bridge.json` را داخل همان پوشه بگذار
4. Variables:
   - `INSTAGRAM_BRIDGE_LOGIN` = ایمیل یا یوزرنیم لاگین (نه لزوماً @reeldrivebot)
   - `INSTAGRAM_BRIDGE_PASSWORD` = پسورد (برای تمدید session)
   - `INSTAGRAM_BRIDGE_ENABLED=true`
   - `INSTAGRAM_BRIDGE_FORCE_LOGIN=false` (پیش‌فرض)

5. **Redeploy**

## ۳) چک لاگ

باید ببینی:

```
Bridge IG ready — DMs to @reeldrivebot will forward...
```

## ۴) استفاده کاربر

1. `/connect` → Bio → `/verify`
2. از **همان پیج متصل‌شده** لینک را در دایرکت **@reeldrivebot** بفرست
3. محتوا در تلگرام می‌آید

---

**نکته:** فایل session مثل sessionid در env نیست — هفته‌ها تا چند ماه معمولاً کافی است و ربات خودش تمدید می‌کند.

**جایگزین:** `INSTAGRAM_PROXY` (پروکسی residential) اگر session منقضی شد.

# راه‌اندازی دایرکت اینستاگرام → تلگرام

برای اینکه کاربر لینک را در **دایرکت @reeldrivebot** بفرستد و در **تلگرام** بگیرد، سرور باید به اینستاگرام لاگین باشد.

ریل‌وی با **پسورد** معمولاً لاگین نمی‌شود (IP بلاک). راه‌حل: **یک‌بار** session از مک شخصی.

## روش A — بدون پسورد API (پیشنهادی اگر BadPassword می‌گیری)

1. در **Safari/Chrome** به [instagram.com](https://www.instagram.com) برو و با اکانت `reeldrivebot` لاگین کن (همان پسورد).
2. DevTools → Application → Cookies → `instagram.com` → کپی مقدار **`sessionid`**
3. در ترمینال:

```bash
cd "/Users/parsa/Desktop/regram pro"
source .venv/bin/activate
export INSTAGRAM_BRIDGE_SESSION_ID="مقدار_sessionid"
python3 scripts/ig_export_session.py
```

4. فایل `sessions/bridge.json` ساخته می‌شود.

**Railway (بدون آپلود فایل):** در Variables بگذار:

- `INSTAGRAM_BRIDGE_SESSION_ID` = همان sessionid با **دو نقطه** (`:`) نه `%3A`
- `INSTAGRAM_BRIDGE_CSRFTOKEN` = کوکی `csrftoken` (همان صفحه DevTools)
- `INSTAGRAM_BRIDGE_MID` = کوکی `mid`
- `INSTAGRAM_BRIDGE_LOGIN` = `reeldrivebot`
- `INSTAGRAM_BRIDGE_ENABLED` = `true`
- `INSTAGRAM_BRIDGE_FORCE_LOGIN` = `false`
- پسورد را روی Railway **نگذار** اگر sessionid داری (challenge می‌خورد)

یا روی مک: `./scripts/print_railway_bridge_env.sh` و مقادیر را کپی کن.

اگر لاگ `467` یا `challenge` دیدی: اپ اینستاگرام را باز کن → «Was this you?» را تأیید کن. اگر باز نشد، علاوه بر `sessionid` کوکی‌های **`csrftoken`** و **`mid`** را هم کپی کن.

---

## روش B — پسورد در ترمینال

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
# اگر 2FA داری:
# export INSTAGRAM_2FA_CODE="123456"
./scripts/ig_export_local.sh
```

**اگر `reeldrivebot` خطا داد:** در اینستاگرام با چه ایمیل/یوزرنیمی لاگین می‌کنی همان را بگذار:

```bash
export INSTAGRAM_BRIDGE_LOGIN="youremail@gmail.com"
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

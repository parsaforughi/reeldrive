# دایرکت اینستا → تلگرام (Bridge)

فقط **یک متغیر** روی Railway:

```
INSTAGRAM_BRIDGE_SESSION_ID=مقدار_کوکی_sessionid
```

از مرورگر: لاگین `reeldrivebot` → DevTools → Application → Cookies → `instagram.com` → **`sessionid`**  
می‌توانی با `%3A` یا `:` کپی کنی — هر دو کار می‌کند.

Redeploy. در لاگ: `Bridge IG ready`.

---

## اگر لاگ `467` یا inbox blocked دیدی

sessionid درست است، ولی **IP سرور Railway** برای خواندن DM بلاک می‌شود.

در Railway یک متغیر دیگر بگذار:

```
INSTAGRAM_PROXY=http://USER:PASS@HOST:PORT
```

پروکسی باید **residential** باشد (نه datacenter). بعد redeploy.

همچنین در اپ اینستاگرام «Was this you?» را تأیید کن.

---

## اگر `TelegramConflictError` دیدی

ربات **دو جا** روشن است (مثلاً Railway + ترمینال مک). روی مک `Ctrl+C` بزن و فقط Railway بماند.

**نیاز نیست:** پسورد، csrftoken، mid — فقط `sessionid` (+ پروکسی روی Railway).

---

## روی مک (اختیاری)

```bash
echo 'SESSIONID_HERE' > scripts/.bridge_sessionid
./scripts/ig_export_from_sessionid_file.sh
```

یا:

```bash
export INSTAGRAM_BRIDGE_SESSION_ID="..."
python3 scripts/ig_export_session.py
```

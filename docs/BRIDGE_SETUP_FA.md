# دایرکت اینستا → تلگرام (Bridge)

ربات DM اکانت `@reeldrivebot` را از **API وب اینستاگرام** (`www.instagram.com`) می‌خواند.
این روش با کوکی مرورگر کار می‌کند و خطای `467` / proxy ندارد.

فقط **یک متغیر** روی Railway:

```
INSTAGRAM_BRIDGE_SESSION_ID=مقدار_کوکی_sessionid
```

از مرورگر: لاگین `reeldrivebot` → DevTools → Application → Cookies → `instagram.com` → **`sessionid`**
با `%3A` یا `:` هر دو کار می‌کند.

Redeploy. در لاگ: `Bridge IG ready (web DM API)`.

---

## اگر DM نیامد

session منقضی/باطل شده. کافی است **sessionid تازه** بگیری:

1. در مرورگر دوباره با `reeldrivebot` لاگین کن
2. کوکی `sessionid` تازه را کپی کن
3. `INSTAGRAM_BRIDGE_SESSION_ID` را در Railway عوض کن → redeploy

در لاگ باید `Bridge IG ready (web DM API)` بیاید.

---

## اگر `TelegramConflictError` دیدی

ربات **دو جا** روشن است (مثلاً Railway + ترمینال مک). روی مک `Ctrl+C` بزن و فقط Railway بماند.

**نیاز نیست:** پسورد، csrftoken، mid، proxy — فقط `sessionid`.

---

## روی مک (تست محلی)

```bash
echo 'SESSIONID_HERE' > scripts/.bridge_sessionid
./scripts/ig_export_from_sessionid_file.sh
```

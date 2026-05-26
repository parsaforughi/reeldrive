# دایرکت اینستا → تلگرام (Bridge)

فقط **یک متغیر** روی Railway:

```
INSTAGRAM_BRIDGE_SESSION_ID=مقدار_کوکی_sessionid
```

از مرورگر: لاگین `reeldrivebot` → DevTools → Application → Cookies → `instagram.com` → **`sessionid`**  
می‌توانی با `%3A` یا `:` کپی کنی — هر دو کار می‌کند.

Redeploy. در لاگ: `Bridge IG ready`.

---

## اگر DM کار نکرد

1. در **اپ اینستاگرام** پیام امنیتی را تأیید کن.
2. **sessionid تازه** بگیر و دوباره در Railway بگذار.
3. اگر سرور Railway است: گاهی IP بلاک است — `INSTAGRAM_PROXY` (پروکسی residential) بگذار.

**نیاز نیست:** پسورد، csrftoken، mid، آپلود فایل — فقط `sessionid`.

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

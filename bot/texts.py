from bot.config import settings

NAME = settings.bot_name
BRIDGE = settings.bridge_ig_handle

START_FA = f"""سلام! 👋 به <b>{NAME}</b> خوش اومدی.

⚡ برای استفاده ساده، از <b>دایرکت دانلود</b> استفاده کن — لینک یا یوزرنیم اینستاگرام را بفرست.

🔐 برای اتصال پیج شخصی: /connect

همه امکانات فعلاً <b>رایگان</b> است.

از دکمه <b>Menu</b> کنار چت، دستورها را ببین 👇
"""

FEATURES_FA = f"""💬 <b>امکانات {NAME}</b>

همه امکانات فعلاً <b>رایگان</b> هستند.

<b>⚡ دایرکت دانلود:</b>
• لینک پست / ریل / کاروسel
• پست تک‌عکس، استوری، هایلایت
• یوزرنیم → پروفایل HD + آمار + استوری

<b>🔐 اتصال پیج:</b> /connect → کد → دایرکت {BRIDGE}

<b>دستورات:</b>
<code>highlights user</code> | <code>highlight user 1</code>
<code>zip stories user</code> | <code>zip posts user</code>
<code>#tag</code> — هشتگ
"""

HELP_DIRECT_FA = f"""⚡ <b>دایرکت دانلود (رایگان)</b>

همین‌جا در چت بفرست:

1️⃣ <b>لینک</b> پست / ریل / اسلاید
2️⃣ <b>یوزرنیم</b> — مثلاً <code>instagram</code>
3️⃣ <b>هایلایت</b> — <code>highlights username</code> سپس <code>highlight username 1</code>
4️⃣ <b>زیپ</b> — <code>zip stories user</code> | <code>zip posts user</code>

بعد از /connect می‌توانی لینک را در دایرکت {BRIDGE} هم بفرستی.
"""

HELP_SEARCH_FA = """🔍 <b>جستجو در اینستاگرام</b>

بعد از /search یکی از این‌ها را بفرست:
• یوزرنیم — <code>username</code>
• هشتگ — <code>#tag</code>
• لینک پست — <code>instagram.com/p/...</code>
"""

HELP_FEED_FA = """🗄️ <b>فید</b>

پیج‌هایی که دنبال می‌کنی:
/watch add username — افزودن
/watch list — لیست
/watch remove username — حذف

به‌زودی: اعلان پست جدید خودکار.
"""

HELP_UNFOLLOWERS_FA = """🚶‍♂️ <b>آنفالویاب</b>

ابتدا پیج را با /connect متصل کن.

به‌زودی: لیست کسانی که آنفالو کرده‌اند.
"""

SETTINGS_FA = f"""⚙️ <b>تنظیمات {NAME}</b>

از دکمه‌های زیر استفاده کن:
"""

PRIVACY_FA = f"""📜 <b>Privacy Policy — {NAME}</b>

• ما پسورد اینستاگرام تو را ذخیره نمی‌کنیم.
• فقط یوزرنیم متصل‌شده و شناسه تلگرام برای ارتباط سرویس نگه داشته می‌شود.
• تو می‌توانی هر وقت با /disconnect اتصال را قطع کنی.
• محتوای ارسالی فقط برای دانلود و تحویل به خودت پردازش می‌شود.

سوالات: از طریق سازنده ربات.
"""

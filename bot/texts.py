from bot.config import settings

NAME = settings.bot_name
BRIDGE = settings.bridge_ig_handle

FEATURES_FA = f"""💬 <b>امکانات {NAME}</b>

همه امکانات فعلاً <b>رایگان</b> هستند (بدون اشتراک).

<b>📃 دایرکت دانلود (رایگان):</b>
• لینک پست / ریل / اسلاید
• پست تک‌عکس، استوری، هایلایت
• یوزرنیم → پروفایل HD + آمار + استوری

<b>🔗 اتصال پیج:</b>
• /connect — کد تأیید → دایرکت {BRIDGE}
• بعد از اتصال: لینک‌ها را در تلگرام یا دایرکت {BRIDGE} بفرست

<b>دستورات ویژه:</b>
<code>highlights username</code> — لیست هایلایت
<code>highlight username 1</code> — دانلود هایلایت
<code>zip stories username</code> — زیپ استوری‌ها
<code>zip posts username</code> — زیپ پست‌ها (تا {settings.max_zip_posts})
<code>#tag</code> — جستجوی هشتگ

/help_directdownload — راهنمای دانلود
/help_watchlist — لیست نظارت
"""

HELP_DIRECT_FA = f"""📃 <b>راهنمای دایرکت دانلود</b>

1️⃣ <b>لینک</b> — هر لینک پست/ریل/اسلاید را بفرست
2️⃣ <b>یوزرنیم</b> — <code>instagram</code> → پروفایل + استوری
3️⃣ <b>هایلایت</b> — <code>highlights username</code> سپس <code>highlight username 1</code>
4️⃣ <b>زیپ</b> — <code>zip stories user</code> | <code>zip posts user</code>

⚠️ پیج‌های پرایوت فقط با /connect (و فالو متقابل) در آینده کامل‌تر می‌شود.
"""

HELP_CONNECT_FA = f"""🔗 <b>اتصال پیج</b>

1. /connect
2. یوزرنیم پیجت را بفرست
3. کد را در <b>دایرکت اینستاگرام</b> به {BRIDGE} بفرست
4. پس از تأیید، لینک‌ها را در تلگرام یا همان دایرکت بفرست

/disconnect — قطع اتصال
"""

HELP_WATCHLIST_FA = """👁 <b>لیست نظارت</b>

/watch add username — افزودن
/watch list — نمایش لیست
/watch remove username — حذف

وقتی پست جدید بیاید (به‌زودی اعلان خودکار).
"""

START_FA = f"""سلام! 👋 من <b>{NAME}</b> هستم.

{FEATURES_FA}

از منوی زیر یا /help استفاده کن.
"""

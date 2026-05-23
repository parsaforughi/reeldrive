from bot.config import settings

NAME = settings.bot_name

START_FA = f"""سلام! 👋 من <b>{NAME}</b> هستم.

یوزرنیم اینستاگرام یا لینک پست/ریل/استوری رو بفرست:

• <code>@username</code> یا <code>username</code>
• پروفایل + عکس پروفایل + آمار
• استوری‌های فعال (اگر عمومی باشه)

• لینک پست: <code>instagram.com/p/...</code>
• لینک ریل: <code>instagram.com/reel/...</code>

دستورات:
/help — راهنما
/status — وضعیت اتصال اینستاگرام
"""

START_EN = f"""Hi! 👋 I'm <b>{NAME}</b>.

Send an Instagram username or link:

• <code>@username</code> or <code>username</code>
• Profile picture + account stats
• Active stories (public accounts)

• Post link: <code>instagram.com/p/...</code>
• Reel link: <code>instagram.com/reel/...</code>

Commands:
/help — Help
/status — Instagram connection status
"""

HELP_FA = """<b>راهنما</b>

<b>پروفایل:</b> یوزرنیم بفرست (مثلاً <code>instagram</code>)
<b>پست/ریل:</b> لینک کامل اینستاگرام
<b>استوری:</b> یوزرنیم — استوری‌های ۲۴ ساعته ارسال می‌شه

⚠️ اکانت‌های پرایوت قابل دسترسی نیستند.
⚠️ برای استوری، ربات باید به اینستاگرام لاگین باشه (/status).
"""

HELP_EN = """<b>Help</b>

<b>Profile:</b> Send a username (e.g. <code>instagram</code>)
<b>Post/Reel:</b> Send full Instagram URL
<b>Stories:</b> Send username — active stories will be sent

⚠️ Private accounts are not supported.
⚠️ Stories require Instagram login (/status).
"""

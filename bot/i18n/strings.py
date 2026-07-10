"""User-facing strings: fa, en, ar."""

from bot.config import settings

NAME = settings.bot_name
BRIDGE = settings.bridge_ig_handle

# key -> {fa, en, ar}
MESSAGES: dict[str, dict[str, str]] = {
    "choose_language": {
        "fa": "🌐 زبان را انتخاب کن:",
        "en": "🌐 Choose your language:",
        "ar": "🌐 اختر لغتك:",
    },
    "lang_set": {
        "fa": "✅ زبان روی فارسی تنظیم شد.",
        "en": "✅ Language set to English.",
        "ar": "✅ تم تعيين اللغة إلى العربية.",
    },
    "lang_set_fa": {
        "fa": "✅ زبان روی فارسی تنظیم شد.",
        "en": "✅ Language set to Persian.",
        "ar": "✅ تم تعيين اللغة إلى الفارسية.",
    },
    "lang_set_en": {
        "fa": "✅ زبان روی انگلیسی تنظیم شد.",
        "en": "✅ Language set to English.",
        "ar": "✅ تم تعيين اللغة إلى الإنجليزية.",
    },
    "lang_set_ar": {
        "fa": "✅ زبان روی عربی تنظیم شد.",
        "en": "✅ Language set to Arabic.",
        "ar": "✅ تم تعيين اللغة إلى العربية.",
    },
    "start": {
        "fa": f"""سلام! 👋 به <b>{NAME}</b> خوش اومدی.

⚡ <b>دایرکت دانلود:</b> لینک پست / ریل را بفرست — <b>۳ بار رایگان</b>، بعد اشتراک Pro.
🛒 فروشگاه: /subscribe

🔐 اتصال پیج (اختیاری): /connect

از دکمه آبی <b>Menu</b> کنار چت استفاده کن 👇""",
        "en": f"""Hi! 👋 Welcome to <b>{NAME}</b>.

⚡ <b>Direct download:</b> send a post/reel link — <b>3 free</b>, then Pro.
🛒 Shop: /subscribe

🔐 Connect page (optional): /connect

Use the blue <b>Menu</b> button next to the chat 👇""",
        "ar": f"""مرحباً! 👋 أهلاً بك في <b>{NAME}</b>.

⚡ <b>تحميل مباشر</b> — أرسل رابط المنشور / الريل — <b>٣ مجاناً</b> ثم Pro.
🛒 المتجر: /subscribe

🔐 ربط الحساب: /connect

استخدم زر <b>Menu</b> الأزرق بجانب المحادثة 👇""",
    },
    "features": {
        "fa": f"""💬 <b>امکانات {NAME}</b>

<b>⚡ دایرکت دانلود:</b> ۳ لینک رایگان، بعد Pro
• پست / ریل / کاروسel
🛒 /subscribe

<b>⭐ Pro:</b> دانلود نامحدود + AI — ۲۰ ستاره/ماه

<b>🔐 اتصال پیج:</b> /connect → کد → دایرکت {BRIDGE}

<b>دستورات:</b>
<code>highlights user</code> | <code>zip stories user</code> | <code>following user</code> | <code>#tag</code>""",
        "en": f"""💬 <b>{NAME} features</b>

<b>⚡ Direct download:</b> 3 free links, then Pro
• Post / Reel / carousel
🛒 /subscribe

<b>⭐ Pro:</b> unlimited download + AI — 20 Stars/month

<b>🔐 Connect page:</b> /connect → code → DM {BRIDGE}

<b>Commands:</b>
<code>highlights user</code> | <code>zip stories user</code> | <code>following user</code> | <code>#tag</code>""",
        "ar": f"""💬 <b>ميزات {NAME}</b>

<b>⚡ تحميل مباشر:</b> ٣ روابط مجاناً ثم Pro
• منشور / ريل / كاروسel
🛒 /subscribe

<b>⭐ Pro:</b> تحميل غير محدود + AI — 20 نجمة/شهر

<b>🔐 ربط الحساب:</b> /connect → رمز → رسالة {BRIDGE}

<b>أوامر:</b>
<code>highlights user</code> | <code>zip stories user</code> | <code>following user</code> | <code>#tag</code>""",
    },
    "help_direct": {
        "fa": f"""⚡ <b>دایرکت دانلود</b>

<b>لینک</b> پست / ریل را بفرست — <b>۳ بار رایگان</b> با لینک مستقیم.
بعد از آن: اشتراک Pro (۲۰ ⭐/ماه) — /subscribe

پروفایل/استوری (اختیاری):
• یوزرنیم — <code>instagram</code>
• <code>highlights user</code>

<b>اتصال پیج:</b> /connect → کد را به {BRIDGE} بفرست.""",
        "en": f"""⚡ <b>Direct download</b>

Send a <b>post / Reel link</b> — <b>3 free</b> direct-link downloads.
Then: Pro (20 ⭐/month) — /subscribe

Profile/stories (optional):
• Username — <code>instagram</code>
• <code>highlights user</code>

<b>Connect:</b> /connect → send code to {BRIDGE}.""",
        "ar": f"""⚡ <b>تحميل مباشر</b>

أرسل <b>رابط منشور / ريل</b> — <b>٣ مجاناً</b> برابط مباشر.
ثم: Pro (20 ⭐/شهر) — /subscribe

الملف/القصص (اختياري):
• اسم المستخدم — <code>instagram</code>
• <code>highlights user</code>

<b>الربط:</b> /connect → أرسل الرمز إلى {BRIDGE}.""",
    },
    "help_search": {
        "fa": """🔍 <b>جستجو</b>

بعد از /search بفرست:
• یوزرنیم
• هشتگ — <code>#tag</code>
• لینک پست""",
        "en": """🔍 <b>Search</b>

After /search send:
• Username
• Hashtag — <code>#tag</code>
• Post link""",
        "ar": """🔍 <b>بحث</b>

بعد /search أرسل:
• اسم المستخدم
• هاشتاغ — <code>#tag</code>
• رابط المنشور""",
    },
    "help_feed": {
        "fa": """🗄️ <b>فید</b>

/watch add username — افزودن
/watch list — لیست
/watch remove username — حذف""",
        "en": """🗄️ <b>Feed</b>

/watch add username — add
/watch list — list
/watch remove username — remove""",
        "ar": """🗄️ <b>الفيد</b>

/watch add username — إضافة
/watch list — القائمة
/watch remove username — حذف""",
    },
    "help_unfollowers": {
        "fa": """🚶‍♂️ <b>آنفالویاب</b>

ابتدا /connect را انجام بده.

به‌زودی: لیست آنفالوها.""",
        "en": """🚶‍♂️ <b>Unfollowers</b>

Connect your page with /connect first.

Coming soon: unfollowers list.""",
        "ar": """🚶‍♂️ <b>من ألغى المتابعة</b>

قم بـ /connect أولاً.

قريباً: قائمة من ألغوا المتابعة.""",
    },
    "settings": {
        "fa": f"⚙️ <b>تنظیمات {NAME}</b>\n\nاز دکمه Menu دستورها را ببین.\n/language — تغییر زبان",
        "en": f"⚙️ <b>{NAME} settings</b>\n\nUse the Menu button for commands.\n/language — change language",
        "ar": f"⚙️ <b>إعدادات {NAME}</b>\n\nاستخدم زر Menu للأوامر.\n/language — تغيير اللغة",
    },
    "privacy": {
        "fa": f"""📜 <b>حریم خصوصی — {NAME}</b>

• پسورد اینستاگرام ذخیره نمی‌شود.
• فقط یوزرنیم متصل و شناسه تلگرام نگه داشته می‌شود.
• /disconnect — قطع اتصال
• محتوا فقط برای تحویل به خودت پردازش می‌شود.""",
        "en": f"""📜 <b>Privacy — {NAME}</b>

• We never store your Instagram password.
• Only connected username and Telegram ID are kept.
• /disconnect — disconnect anytime
• Content is processed only to deliver downloads to you.""",
        "ar": f"""📜 <b>الخصوصية — {NAME}</b>

• لا نحفظ كلمة مرور إنستغرام.
• نحفظ اسم المستخدم المرتبط ومعرف تيليجرام فقط.
• /disconnect — إلغاء الربط
• المحتوى يُعالَج فقط لتسليمه إليك.""",
    },
    "connect_ask_username": {
        "fa": "یوزرنیم پیج اینستاگرامت را بفرست (مثلاً <code>myshop</code>):",
        "en": "Send your Instagram page username (e.g. <code>myshop</code>):",
        "ar": "أرسل اسم مستخدم صفحة إنستغرام (مثلاً <code>myshop</code>):",
    },
    "connect_cancel": {
        "fa": "لغو شد.",
        "en": "Cancelled.",
        "ar": "تم الإلغاء.",
    },
    "connect_cancelled_for_link": {
        "fa": "اتصال پیج لغو شد — دایرکت دانلود:",
        "en": "Connect cancelled — direct download:",
        "ar": "تم إلغاء الربط — تحميل مباشر:",
    },
    "connect_invalid_username": {
        "fa": "یوزرنیم نامعتبر است.",
        "en": "Invalid username.",
        "ar": "اسم المستخدم غير صالح.",
    },
    "connect_bridge_offline": {
        "fa": (
            "\n\n💡 <b>دایرکت {bridge} الان فعال نیست</b> — از روش Bio + /verify استفاده کن."
        ),
        "en": (
            "\n\n💡 <b>DM to {bridge} is offline</b> — use Bio + /verify instead."
        ),
        "ar": (
            "\n\n💡 <b>الرسائل إلى {bridge} غير متاحة</b> — استخدم السيرة + /verify."
        ),
    },
    "connect_wrong_account": {
        "fa": (
            "❌ کد از اکانت <b>@{got}</b> آمد، ولی تو پیج <b>@{expected}</b> را ثبت کرده بودی.\n"
            "از همان پیجی که در /connect نوشتی کد را بفرست."
        ),
        "en": (
            "❌ Code came from <b>@{got}</b>, but you registered <b>@{expected}</b>.\n"
            "Send the code from the same Instagram account."
        ),
        "ar": (
            "❌ الرمز من <b>@{got}</b> لكنك سجّلت <b>@{expected}</b>.\n"
            "أرسل الرمز من نفس حساب إنستغرام."
        ),
    },
    "connect_code": {
        "fa": (
            "✅ پیج: <b>@{username}</b>\n\n"
            "کد تأیید: <code>{code}</code>\n"
            "⏱ تا {ttl} دقیقه معتبر است.\n\n"
            "<b>روش ۱ (پیشنهادی — بدون session):</b>\n"
            "۱. کد <code>{code}</code> را در <b>Bio</b> اینستاگرام بگذار\n"
            "۲. اینجا بزن: /verify\n\n"
            "<b>روش ۲ (اختیاری):</b> همان کد را در دایرکت {bridge} بفرست "
            "(فقط اگر bridge سرور آنلاین باشد)."
        ),
        "en": (
            "✅ Page: <b>@{username}</b>\n\n"
            "Code: <code>{code}</code>\n"
            "⏱ Valid for {ttl} minutes.\n\n"
            "<b>Method 1 (recommended — no server session):</b>\n"
            "1. Put <code>{code}</code> in your Instagram <b>bio</b>\n"
            "2. Tap /verify here\n\n"
            "<b>Method 2 (optional):</b> DM the code to {bridge} "
            "(only if server bridge is online)."
        ),
        "ar": (
            "✅ الحساب: <b>@{username}</b>\n\n"
            "الرمز: <code>{code}</code>\n"
            "⏱ صالح لمدة {ttl} دقيقة.\n\n"
            "<b>الطريقة ١ (موصى بها):</b>\n"
            "١. ضع <code>{code}</code> في <b>السيرة</b>\n"
            "٢. اضغط /verify هنا\n\n"
            "<b>الطريقة ٢:</b> أرسل الرمز إلى {bridge} في الرسائل."
        ),
    },
    "verify_ok": {
        "fa": "✅ پیج <b>@{username}</b> متصل شد! می‌توانی Bio را به حالت قبل برگردانی.",
        "en": "✅ Connected to <b>@{username}</b>! You can restore your bio.",
        "ar": "✅ تم ربط <b>@{username}</b>! يمكنك إعادة السيرة كما كانت.",
    },
    "verify_ok_ig_dm_active": {
        "fa": (
            "📩 <b>دایرکت اینستاگرام فعال است</b>\n\n"
            "لینک پست/ریل را در دایرکت {bridge} بفرست "
            "(از همان پیجی که الان وصل کردی: @{username}).\n"
            "ربات همان را اینجا در تلگرام تحویل می‌دهد.\n\n"
            "یا لینک را همین‌جا در چت تلگرام هم بفرست."
        ),
        "en": (
            "📩 <b>Instagram DM relay is ON</b>\n\n"
            "Send post/reel links in DM to {bridge} (from @{username}).\n"
            "You will receive them here in Telegram.\n\n"
            "You can also paste links in this chat."
        ),
        "ar": (
            "📩 <b>رسائل إنستغرام مفعّلة</b>\n\n"
            "أرسل الروابط إلى {bridge} من @{username}.\n"
            "ستصل هنا في تيليجرام."
        ),
    },
    "verify_ok_ig_dm_offline": {
        "fa": (
            "📩 <b>دایرکت {bridge} → تلگرام هنوز خاموش است</b>\n\n"
            "اینستاگرام اجازه لاگین روی سرور ریل‌وی را نمی‌دهد. "
            "ادمین <b>یک‌بار</b> session را از مک export می‌کند و روی Volume می‌گذارد "
            "(راهنما: <code>docs/BRIDGE_SETUP_FA.md</code>).\n\n"
            "تا آن موقع: لینک را <b>همین‌جا در تلگرام</b> بفرست — دایرکت دانلود کار می‌کند."
        ),
        "en": (
            "📩 <b>DM {bridge} → Telegram is OFF</b>\n\n"
            "Admin must upload a session file once from a PC "
            "(see <code>docs/BRIDGE_SETUP_FA.md</code>).\n\n"
            "Until then: paste links <b>here in Telegram</b>."
        ),
        "ar": (
            "📩 <b>الرسائل {bridge} → تيليجرام غير مفعّلة</b>\n\n"
            "يجب رفع ملف session مرة واحدة (راجع docs/BRIDGE_SETUP_FA.md).\n\n"
            "حالياً: أرسل الروابط هنا في تيليجرام."
        ),
    },
    "verify_no_pending": {
        "fa": "اتصالی در انتظار نیست. اول /connect را بزن.",
        "en": "No pending connection. Use /connect first.",
        "ar": "لا يوجد ربط معلّق. استخدم /connect أولاً.",
    },
    "verify_not_in_bio": {
        "fa": (
            "❌ کد <code>{code}</code> در Bio پیج <b>@{username}</b> دیده نشد.\n"
            "کد را دقیق در Bio بگذار، ذخیره کن، ۱۰ ثانیه صبر کن و دوباره /verify بزن."
        ),
        "en": (
            "❌ Code <code>{code}</code> not found in <b>@{username}</b> bio.\n"
            "Add it to your bio, save, wait 10s, then /verify again."
        ),
        "ar": (
            "❌ الرمز <code>{code}</code> غير موجود في سيرة <b>@{username}</b>.\n"
            "أضفه واحفظ وانتظر 10 ثوانٍ ثم /verify."
        ),
    },
    "verify_private": {
        "fa": "❌ پیج خصوصی است — موقتاً Bio عمومی کن یا از روش دایرکت استفاده کن.",
        "en": "❌ Private account — make bio visible or use DM method.",
        "ar": "❌ الحساب خاص — اجعل السيرة مرئية أو استخدم الرسائل.",
    },
    "verify_apify": {
        "fa": "❌ بررسی Bio ممکن نشد. APIFY_TOKEN را چک کن یا بعداً امتحان کن.",
        "en": "❌ Could not check bio. Check APIFY_TOKEN or try later.",
        "ar": "❌ تعذر فحص السيرة. تحقق من APIFY_TOKEN.",
    },
    "connect_disconnected": {
        "fa": "اتصال قطع شد.",
        "en": "Disconnected.",
        "ar": "تم إلغاء الربط.",
    },
    "connect_not_found": {
        "fa": "پیجی متصل نبود.",
        "en": "No connected page found.",
        "ar": "لا يوجد حساب مرتبط.",
    },
    "connected_ok": {
        "fa": (
            "✅ ربات به پیج <b>@{username}</b> متصل شد!\n"
            "لینک‌ها را اینجا یا در دایرکت {bridge} بفرست."
        ),
        "en": (
            "✅ Connected to <b>@{username}</b>!\n"
            "Send links here or in DM to {bridge}."
        ),
        "ar": (
            "✅ تم ربط البوت بـ <b>@{username}</b>!\n"
            "أرسل الروابط هنا أو في رسالة {bridge}."
        ),
    },
    "processing": {
        "fa": "⏳ در حال پردازش…",
        "en": "⏳ Processing…",
        "ar": "⏳ جاري المعالجة…",
    },
    "hint_invalid_input": {
        "fa": "یوزرنیم، لینک، یا دستور معتبر بفرست.\nاز Menu → /directdownload یا /search",
        "en": "Send a valid username, link, or command.\nUse Menu → /directdownload or /search",
        "ar": "أرسل اسم مستخدم أو رابط أو أمراً صالحاً.\nمن Menu → /directdownload أو /search",
    },
    "search_invalid": {
        "fa": "❌ ورودی نامعتبر. /search را دوباره بزن.",
        "en": "❌ Invalid input. Try /search again.",
        "ar": "❌ إدخال غير صالح. جرّب /search مرة أخرى.",
    },
    "search_prompt": {
        "fa": "🔎 حالا یوزرنیم، #هشتگ یا لینک را بفرست:",
        "en": "🔎 Now send username, #hashtag, or link:",
        "ar": "🔎 أرسل اسم المستخدم أو #هاشتاغ أو رابطاً:",
    },
    "error_generic": {
        "fa": "❌ مشکلی پیش آمد. لطفاً دوباره امتحان کن.",
        "en": "❌ Something went wrong. Please try again.",
        "ar": "❌ حدث خطأ. يرجى المحاولة مرة أخرى.",
    },
    "error_login_required": {
        "fa": "❌ اتصال اینستاگرام سرویس قطع شده. بعداً دوباره امتحان کن.",
        "en": "❌ Instagram service session expired. Try again later.",
        "ar": "❌ انتهت جلسة خدمة إنستغرام. حاول لاحقاً.",
    },
    "error_apify": {
        "fa": "❌ سرویس دانلود موقتاً در دسترس نیست. چند دقیقه بعد دوباره امتحان کن.",
        "en": "❌ Download service is temporarily unavailable. Try again in a few minutes.",
        "ar": "❌ خدمة التحميل غير متاحة مؤقتاً. حاول بعد قليل.",
    },
    "error_not_found": {
        "fa": "❌ محتوا پیدا نشد. لینک یا یوزرنیم را بررسی کن.",
        "en": "❌ Content not found. Check the link or username.",
        "ar": "❌ لم يُعثر على المحتوى. تحقق من الرابط أو اسم المستخدم.",
    },
    "error_private": {
        "fa": "❌ این محتوا خصوصی است یا دسترسی نداریم.",
        "en": "❌ This content is private or not accessible.",
        "ar": "❌ هذا المحتوى خاص أو غير متاح.",
    },
    "error_rate_limit": {
        "fa": "❌ درخواست زیاد است. چند دقیقه صبر کن.",
        "en": "❌ Too many requests. Wait a few minutes.",
        "ar": "❌ طلبات كثيرة. انتظر بضع دقائق.",
    },
    "error_service_ig": {
        "fa": "❌ برای پروفایل/استوری/هایلایت، سرویس اینستاگرام لازم است (فعلاً غیرفعال).",
        "en": "❌ Profile/stories/highlights need the Instagram service (currently off).",
        "ar": "❌ الملف/القصص/الهايلايت يحتاج خدمة إنستغرام (غير مفعّلة).",
    },
    "error_direct_not_ready": {
        "fa": "❌ دایرکت دانلود آماده نیست. لطفاً بعداً دوباره امتحان کن.",
        "en": "❌ Direct download is not ready. Please try again later.",
        "ar": "❌ التحميل المباشر غير جاهز. حاول لاحقاً.",
    },
    "error_invalid_username": {
        "fa": "❌ یوزرنیم نامعتبر است.",
        "en": "❌ Invalid username.",
        "ar": "❌ اسم المستخدم غير صالح.",
    },
    "no_posts": {
        "fa": "پستی پیدا نشد.",
        "en": "No posts found.",
        "ar": "لم يُعثر على منشورات.",
    },
    "no_highlights": {
        "fa": "هایلایتی نیست.",
        "en": "No highlights.",
        "ar": "لا توجد هايلايت.",
    },
    "empty_highlight": {
        "fa": "خالی بود.",
        "en": "Empty.",
        "ar": "فارغ.",
    },
    "no_stories": {
        "fa": "استوری فعالی نیست.",
        "en": "No active stories.",
        "ar": "لا توجد قصص نشطة.",
    },
    "no_following": {
        "fa": "کسی فالو نشده یا لیست خصوصی است.",
        "en": "No following found (or the list is private).",
        "ar": "لا توجد متابَعون (أو القائمة خاصة).",
    },
    "following_count": {
        "fa": "➡️ {count} فالووینگ @{username}",
        "en": "➡️ {count} following of @{username}",
        "ar": "➡️ {count} متابَع لـ @{username}",
    },
    "following_ask_username": {
        "fa": "یوزرنیم یا آیدی اینستاگرام رو بفرست تا لیست فالووینگ‌هاش رو برات بیارم:",
        "en": "Send the Instagram username / ID and I'll fetch their following list:",
        "ar": "أرسل اسم مستخدم إنستغرام وسأجلب قائمة من يتابعهم:",
    },
    "following_cancelled": {
        "fa": "لغو شد.",
        "en": "Cancelled.",
        "ar": "تم الإلغاء.",
    },
    "following_invalid_username": {
        "fa": "یوزرنیم نامعتبر است.",
        "en": "Invalid username.",
        "ar": "اسم المستخدم غير صالح.",
    },
    "following_join_required": {
        "fa": (
            "برای دیدن لیست فالووینگ، اول باید عضو این کانال‌ها بشی:\n\n"
            "{channels}\n\n"
            "بعد از عضویت، دکمه «بررسی مجدد» رو بزن."
        ),
        "en": (
            "To view following-lists, first join these channels:\n\n"
            "{channels}\n\n"
            "Then tap \"Recheck\"."
        ),
        "ar": (
            "لعرض قوائم المتابَعين، انضم أولاً إلى هذه القنوات:\n\n"
            "{channels}\n\n"
            "ثم اضغط \"إعادة الفحص\"."
        ),
    },
    "following_still_missing": {
        "fa": "هنوز عضو این کانال‌ها نیستی:\n\n{channels}\n\nبعد از عضویت دوباره امتحان کن.",
        "en": "You're still not a member of:\n\n{channels}\n\nJoin then try again.",
        "ar": "لا تزال غير منضم إلى:\n\n{channels}\n\nانضم ثم حاول مجدداً.",
    },
    "following_recheck_button": {
        "fa": "✅ بررسی مجدد عضویت",
        "en": "✅ Recheck membership",
        "ar": "✅ إعادة فحص العضوية",
    },
    "following_pages_intro": {
        "fa": (
            "➡️ @{username} در مجموع {count} نفر رو فالو کرده.\n"
            "لیست در {pages} صفحه در دسترسه — {free} صفحه اول رایگانه، بقیه هر صفحه {price} تومان (کارت به کارت).\n\n"
            "صفحه‌ای رو انتخاب کن:"
        ),
        "en": (
            "➡️ @{username} follows {count} accounts in total.\n"
            "The list is split into {pages} pages — the first {free} are free, the rest cost {price} Toman each.\n\n"
            "Pick a page:"
        ),
        "ar": (
            "➡️ @{username} يتابع {count} حساباً إجمالاً.\n"
            "القائمة مقسمة إلى {pages} صفحات — أول {free} صفحات مجانية، والباقي بسعر {price} تومان لكل صفحة.\n\n"
            "اختر صفحة:"
        ),
    },
    "following_pages_menu": {
        "fa": "لیست فالووینگ @{username} — صفحه‌ای رو انتخاب کن:",
        "en": "Following list of @{username} — pick a page:",
        "ar": "قائمة متابَعي @{username} — اختر صفحة:",
    },
    "following_session_expired": {
        "fa": "این جلسه منقضی شده. دوباره /following رو بزن.",
        "en": "This session expired. Run /following again.",
        "ar": "انتهت هذه الجلسة. نفّذ /following مجدداً.",
    },
    "following_page_header": {
        "fa": "➡️ صفحه {page}/{total} فالووینگ @{username} ({count} نفر)",
        "en": "➡️ Page {page}/{total} of @{username}'s following ({count})",
        "ar": "➡️ الصفحة {page}/{total} من متابَعي @{username} ({count})",
    },
    "following_pay_prompt": {
        "fa": (
            "🔒 صفحه {page} فالووینگ @{username} قفل است.\n\n"
            "برای باز شدنش {price} تومان کارت‌به‌کارت واریز کن و رسیدش رو برای پشتیبانی بفرست. "
            "بعد از تأیید، دسترسی برات باز میشه."
        ),
        "en": (
            "🔒 Page {page} of @{username}'s following is locked.\n\n"
            "Send {price} Toman via card-to-card to support to unlock it. "
            "Access is granted after manual confirmation."
        ),
        "ar": (
            "🔒 الصفحة {page} من متابَعي @{username} مقفلة.\n\n"
            "أرسل {price} تومان عبر التحويل البنكي للدعم لفتحها. "
            "سيتم منح الوصول بعد التأكيد اليدوي."
        ),
    },
    "following_pay_button": {
        "fa": "💳 پرداخت {price} تومان (کارت به کارت)",
        "en": "💳 Pay {price} Toman (card-to-card)",
        "ar": "💳 ادفع {price} تومان (تحويل بنكي)",
    },
    "following_back_button": {
        "fa": "◀️ بازگشت به صفحات",
        "en": "◀️ Back to pages",
        "ar": "◀️ العودة إلى الصفحات",
    },
    "following_page_unlocked_notify": {
        "fa": "✅ صفحه {page} فالووینگ @{username} برات باز شد! برو /following بزن و اون صفحه رو ببین.",
        "en": "✅ Page {page} of @{username}'s following is now unlocked! Run /following to view it.",
        "ar": "✅ تم فتح الصفحة {page} من متابَعي @{username}! نفّذ /following لعرضها.",
    },
    "stories_count": {
        "fa": "📖 {count} استوری",
        "en": "📖 {count} stories",
        "ar": "📖 {count} قصة",
    },
    "unfollowers_need_connect": {
        "fa": "\n\n⚠️ ابتدا /connect را انجام بده.",
        "en": "\n\n⚠️ Run /connect first.",
        "ar": "\n\n⚠️ نفّذ /connect أولاً.",
    },
    "status_body": {
        "fa": (
            "<b>{name}</b>\n\n"
            "⭐ اشتراک: {plan}\n"
            "⚡ دایرکت دانلود (Apify): {apify}\n"
            "📥 دانلود لینک: {svc}{ig_extra}\n"
            "💬 پل اتصال {bridge}: {brg}\n"
            "🔗 پیج تو: {page}"
        ),
        "en": (
            "<b>{name}</b>\n\n"
            "⭐ Plan: {plan}\n"
            "⚡ Direct download (Apify): {apify}\n"
            "📥 Link download: {svc}{ig_extra}\n"
            "💬 Bridge {bridge}: {brg}\n"
            "🔗 Your page: {page}"
        ),
        "ar": (
            "<b>{name}</b>\n\n"
            "⭐ الاشتراك: {plan}\n"
            "⚡ تحميل مباشر (Apify): {apify}\n"
            "📥 تحميل الروابط: {svc}{ig_extra}\n"
            "💬 جسر {bridge}: {brg}\n"
            "🔗 حسابك: {page}"
        ),
    },
    "status_plan_free": {
        "fa": "رایگان: {left}/{total} لینک — Pro {pro_stars}⭐ — /subscribe",
        "en": "Free: {left}/{total} links — Pro {pro_stars}⭐ — /subscribe",
        "ar": "مجاني: {left}/{total} روابط — Pro {pro_stars}⭐ — /subscribe",
    },
    "status_plan_pro": {
        "fa": "{plan} تا {date}",
        "en": "{plan} until {date}",
        "ar": "{plan} حتى {date}",
    },
    "status_plan_vip": {
        "fa": "VIP ♾️ — دسترسی کامل",
        "en": "VIP ♾️ — full access",
        "ar": "VIP ♾️ — وصول كامل",
    },
    "pro_upsell": {
        "fa": (
            "⭐ <b>Pro</b> — {stars} ستاره / ماه\n"
            "دانلود نامحدود + دایرکت دانلود.\n"
            "دستور: /subscribe"
        ),
        "en": (
            "⭐ <b>Pro</b> — {stars} Stars / month\n"
            "Unlimited downloads + direct download.\n"
            "Command: /subscribe"
        ),
        "ar": (
            "⭐ <b>Pro</b> — {stars} نجمة / شهر\n"
            "تحميل غير محدود + تحميل مباشر.\n"
            "الأمر: /subscribe"
        ),
    },
    "pro_invoice_title": {
        "fa": "Reeldrive Pro — ماهانه",
        "en": "Reeldrive Pro — monthly",
        "ar": "Reeldrive Pro — شهري",
    },
    "pro_invoice_desc": {
        "fa": "اشتراک Pro {name} — دانلود نامحدود + دایرکت — {days} روز. پرداخت با Stars.",
        "en": "{name} Pro — unlimited + direct download — {days} days. Pay with Stars.",
        "ar": "Pro {name} — تحميل غير محدود + مباشر — {days} يوماً. الدفع بـ Stars.",
    },
    "pro_price_label": {
        "fa": "Pro ماهانه ({days} روز)",
        "en": "Pro monthly ({days} days)",
        "ar": "Pro شهري ({days} يوماً)",
    },
    "pro_already_active": {
        "fa": "✅ Pro فعال است تا {date}.\nمی‌توانی تمدید کنی:",
        "en": "✅ Pro active until {date}.\nYou can renew:",
        "ar": "✅ Pro نشط حتى {date}.\nيمكنك التجديد:",
    },
    "pro_payment_ok": {
        "fa": (
            "🎉 <b>Pro فعال شد!</b>\n\n"
            "⭐ پرداخت: {stars} ستاره\n"
            "📅 اعتبار: {days} روز (تا {date})\n\n"
            "ممنون از حمایتت!"
        ),
        "en": (
            "🎉 <b>Pro activated!</b>\n\n"
            "⭐ Paid: {stars} Stars\n"
            "📅 Valid: {days} days (until {date})\n\n"
            "Thank you!"
        ),
        "ar": (
            "🎉 <b>تم تفعيل Pro!</b>\n\n"
            "⭐ الدفع: {stars} نجمة\n"
            "📅 الصلاحية: {days} يوماً (حتى {date})"
        ),
    },
    "pro_payment_failed": {
        "fa": "❌ پرداخت تأیید نشد. دوباره /subscribe را بزن.",
        "en": "❌ Payment could not be verified. Try /subscribe again.",
        "ar": "❌ تعذر التحقق من الدفع. جرّب /subscribe.",
    },
    "pro_checkout_failed": {
        "fa": "پرداخت نامعتبر است.",
        "en": "Invalid payment.",
        "ar": "دفع غير صالح.",
    },
    "pro_disabled": {
        "fa": "پرداخت Stars فعلاً غیرفعال است.",
        "en": "Stars payments are disabled.",
        "ar": "مدفوعات Stars معطّلة.",
    },
    "btn_pro_buy": {
        "fa": "⭐ خرید Pro ({stars} ⭐)",
        "en": "⭐ Buy Pro ({stars} ⭐)",
        "ar": "⭐ شراء Pro ({stars} ⭐)",
    },
    "btn_pro_renew": {
        "fa": "🔄 تمدید Pro ({stars} ⭐)",
        "en": "🔄 Renew Pro ({stars} ⭐)",
        "ar": "🔄 تجديد Pro ({stars} ⭐)",
    },
    "shop_body": {
        "fa": (
            "🛒 <b>فروشگاه Pro — {name}</b>\n\n"
            "📌 {status}\n\n"
            "🎁 <b>رایگان:</b> {free_total} دانلود با لینک مستقیم\n"
            "⭐ <b>Pro:</b> {pro_stars} ⭐ یا ۹۸,۰۰۰ تومان / ماه\n"
            "⚡ دایرکت دانلود فقط با Pro\n\n"
            "روش پرداخت: Stars یا کارت به کارت 👇"
        ),
        "en": (
            "🛒 <b>Pro Shop — {name}</b>\n\n"
            "📌 {status}\n\n"
            "🎁 <b>Free:</b> {free_total} direct-link downloads\n"
            "⭐ <b>Pro:</b> {pro_stars} ⭐ / month\n"
            "⚡ Direct download requires Pro\n\n"
            "Pay with Stars or bank transfer 👇"
        ),
        "ar": (
            "🛒 <b>متجر Pro — {name}</b>\n\n"
            "📌 {status}\n\n"
            "🎁 <b>مجاني:</b> {free_total} تحميل برابط مباشر\n"
            "⭐ <b>Pro:</b> {pro_stars} ⭐ / شهر\n"
            "⚡ التحميل المباشر يتطلب Pro\n\n"
            "الدفع: Stars أو تحويل بنكي 👇"
        ),
    },
    "shop_status_vip": {
        "fa": "VIP ♾️ — دسترسی کامل",
        "en": "VIP ♾️ — full access",
        "ar": "VIP ♾️ — وصول كامل",
    },
    "shop_status_free_trials": {
        "fa": "🎁 {left} از {total} دانلود رایگان باقی‌مانده",
        "en": "🎁 {left} of {total} free downloads left",
        "ar": "🎁 {left} من {total} تحميل مجاني متبقٍ",
    },
    "shop_status_pro": {
        "fa": "🤖 Pro فعال تا {date}",
        "en": "🤖 Pro active until {date}",
        "ar": "🤖 Pro نشط حتى {date}",
    },
    "shop_status_free": {
        "fa": "بدون اشتراک فعال",
        "en": "No active subscription",
        "ar": "لا يوجد اشتراك نشط",
    },
    "shop_upsell_short": {
        "fa": "🎁 {free_total} لینک رایگان — Pro {pro_stars}⭐ — /subscribe",
        "en": "🎁 {free_total} free links — Pro {pro_stars}⭐ — /subscribe",
        "ar": "🎁 {free_total} روابط مجانية — Pro {pro_stars}⭐ — /subscribe",
    },
    "download_paywall": {
        "fa": (
            "🔒 <b>۳ دانلود رایگان تمام شد!</b>\n\n"
            "هر نفر ۳ بار لینک مستقیم رایگان دارد.\n"
            "برای ادامه: <b>Pro</b> — {pro_stars} ⭐ / ماه 👇"
        ),
        "en": (
            "🔒 <b>3 free downloads used!</b>\n\n"
            "You get 3 free direct-link downloads.\n"
            "To continue: <b>Pro</b> — {pro_stars} ⭐ / month 👇"
        ),
        "ar": (
            "🔒 <b>انتهت التحميلات المجانية!</b>\n\n"
            "٣ تحميلات مجانية لكل مستخدم.\n"
            "<b>Pro</b> — {pro_stars} ⭐ / شهر 👇"
        ),
    },
    "pro_paywall": {
        "fa": (
            "🔒 <b>دایرکت دانلود</b> نیاز به Pro دارد.\n\n"
            "اتصال به اینستاگرام + دانلود نامحدود\n"
            "⭐ {pro_stars} ستاره / ماه 👇"
        ),
        "en": (
            "🔒 <b>Direct download</b> requires Pro.\n\n"
            "Instagram connect + unlimited downloads\n"
            "⭐ {pro_stars} Stars / month 👇"
        ),
        "ar": (
            "🔒 <b>التحميل المباشر</b> يتطلب Pro.\n\n"
            "ربط إنستغرام + تحميل غير محدود\n"
            "⭐ {pro_stars} نجمة / شهر 👇"
        ),
    },
    "download_invoice_title": {
        "fa": "اشتراک دانلود — ۳۰ روز",
        "en": "Download subscription — 30 days",
        "ar": "اشتراك التحميل — 30 يوماً",
    },
    "download_invoice_desc": {
        "fa": "دانلود مستقیم در {name} — {days} روز. پرداخت با Telegram Stars.",
        "en": "{name} direct download — {days} days. Pay with Telegram Stars.",
        "ar": "تحميل مباشر في {name} — {days} يوماً. الدفع بـ Telegram Stars.",
    },
    "download_price_label": {
        "fa": "دانلود ({days} روز)",
        "en": "Download ({days} days)",
        "ar": "تحميل ({days} يوماً)",
    },
    "download_already_active": {
        "fa": "✅ اشتراک دانلود فعال است تا {date}.\nمی‌توانی تمدید کنی:",
        "en": "✅ Download active until {date}.\nYou can renew:",
        "ar": "✅ التحميل نشط حتى {date}.\nيمكنك التجديد:",
    },
    "download_payment_ok": {
        "fa": (
            "🎉 <b>اشتراک دانلود فعال شد!</b>\n\n"
            "⭐ پرداخت: {stars} ستاره\n"
            "📅 اعتبار: {days} روز (تا {date})\n\n"
            "الان لینک بفرست و دانلود کن 🚀"
        ),
        "en": (
            "🎉 <b>Download activated!</b>\n\n"
            "⭐ Paid: {stars} Stars\n"
            "📅 Valid: {days} days (until {date})\n\n"
            "Send a link and download 🚀"
        ),
        "ar": (
            "🎉 <b>تم تفعيل التحميل!</b>\n\n"
            "⭐ الدفع: {stars} نجمة\n"
            "📅 الصلاحية: {days} يوماً (حتى {date})"
        ),
    },
    "btn_buy_download": {
        "fa": "📥 خرید دانلود ({stars} ⭐)",
        "en": "📥 Buy download ({stars} ⭐)",
        "ar": "📥 شراء التحميل ({stars} ⭐)",
    },
    "btn_buy_pro": {
        "fa": "⭐ خرید Pro ({stars} ⭐)",
        "en": "⭐ Buy Pro ({stars} ⭐)",
        "ar": "⭐ شراء Pro ({stars} ⭐)",
    },
    "btn_open_shop": {
        "fa": "🛒 خرید Pro",
        "en": "🛒 Buy Pro",
        "ar": "🛒 شراء Pro",
    },
    "btn_card_to_card": {
        "fa": "💳 کارت به کارت",
        "en": "💳 Bank transfer",
        "ar": "💳 تحويل بنكي",
    },
    "btn_shop_refresh": {
        "fa": "🔄 بروزرسانی فروشگاه",
        "en": "🔄 Refresh shop",
        "ar": "🔄 تحديث المتجر",
    },
    "payments_disabled": {
        "fa": "پرداخت Stars فعلاً غیرفعال است.",
        "en": "Stars payments are disabled.",
        "ar": "مدفوعات Stars معطّلة.",
    },
    "checkout_failed": {
        "fa": "پرداخت نامعتبر است.",
        "en": "Invalid payment.",
        "ar": "دفع غير صالح.",
    },
    "payment_failed": {
        "fa": "❌ پرداخت تأیید نشد. دوباره تلاش کن.",
        "en": "❌ Payment could not be verified. Try again.",
        "ar": "❌ تعذر التحقق من الدفع. حاول مجدداً.",
    },
    "status_pending": {
        "fa": "⏳ منتظر کد — @{username}",
        "en": "⏳ Awaiting code — @{username}",
        "ar": "⏳ بانتظار الرمز — @{username}",
    },
    "status_not_connected": {
        "fa": "❌ متصل نیست — /connect",
        "en": "❌ Not connected — /connect",
        "ar": "❌ غير مرتبط — /connect",
    },
    "myig_none": {
        "fa": "📩 <b>اینستاگرام من</b>\n\nهنوز پیجی متصل نیست.\n/connect",
        "en": "📩 <b>My Instagram</b>\n\nNo page connected yet.\n/connect",
        "ar": "📩 <b>إنستغرامي</b>\n\nلا يوجد حساب مرتبط.\n/connect",
    },
    "myig_pending": {
        "fa": (
            "📩 <b>اینستاگرام من</b>\n\n"
            "پیج: @{username}\n"
            "⏳ در انتظار کد…\n"
            "کد را در دایرکت {bridge} بفرست."
        ),
        "en": (
            "📩 <b>My Instagram</b>\n\n"
            "Page: @{username}\n"
            "⏳ Waiting for code…\n"
            "Send code in DM to {bridge}."
        ),
        "ar": (
            "📩 <b>إنستغرامي</b>\n\n"
            "الحساب: @{username}\n"
            "⏳ بانتظار الرمز…\n"
            "أرسل الرمز إلى {bridge}."
        ),
    },
    "myig_connected": {
        "fa": (
            "📩 <b>اینستاگرام من</b>\n\n"
            "✅ متصل به @{username}\n"
            "📅 از: {date}\n\n"
            "{usage}"
        ),
        "en": (
            "📩 <b>My Instagram</b>\n\n"
            "✅ Connected to @{username}\n"
            "📅 Since: {date}\n\n"
            "{usage}"
        ),
        "ar": (
            "📩 <b>إنستغرامي</b>\n\n"
            "✅ مرتبط بـ @{username}\n"
            "📅 منذ: {date}\n\n"
            "{usage}"
        ),
    },
    "feed_empty": {
        "fa": (
            "🗄️ <b>فید</b>\n\n"
            "لیست خالی است.\n"
            "<code>/watch add username</code>\n\n"
            "/connect"
        ),
        "en": (
            "🗄️ <b>Feed</b>\n\n"
            "List is empty.\n"
            "<code>/watch add username</code>\n\n"
            "/connect"
        ),
        "ar": (
            "🗄️ <b>الفيد</b>\n\n"
            "القائمة فارغة.\n"
            "<code>/watch add username</code>\n\n"
            "/connect"
        ),
    },
    "feed_title": {
        "fa": "🗄️ <b>فید — پیج‌های تحت نظر</b>",
        "en": "🗄️ <b>Feed — watched pages</b>",
        "ar": "🗄️ <b>الفيد — حسابات مراقبة</b>",
    },
    "feed_footer": {
        "fa": "\nبرای دانلود، لینک یا یوزرنیم بفرست.\n/watch list",
        "en": "\nSend a link or username to download.\n/watch list",
        "ar": "\nأرسل رابطاً أو اسم مستخدم للتحميل.\n/watch list",
    },
    "page_connected": {
        "fa": "✅ پیج متصل: @{username}",
        "en": "✅ Connected page: @{username}",
        "ar": "✅ حساب مرتبط: @{username}",
    },
    "forward_ig_prefix": {
        "fa": "📩 <b>دایرکت اینستاگرام</b>\n",
        "en": "📩 <b>Instagram DM</b>\n",
        "ar": "📩 <b>رسالة إنستغرام</b>\n",
    },
    "btn_cancel": {
        "fa": "❌ لغو",
        "en": "❌ Cancel",
        "ar": "❌ إلغاء",
    },
    "invalid": {
        "fa": "نامعتبر",
        "en": "Invalid",
        "ar": "غير صالح",
    },
    "post_expired": {
        "fa": "اطلاعات پست منقضی شده — لینک را دوباره بفرست",
        "en": "Post data expired — send the link again",
        "ar": "انتهت بيانات المنشور — أرسل الرابط مجدداً",
    },
    "no_links_saved": {
        "fa": "لینکی ذخیره نشده",
        "en": "No saved links",
        "ar": "لا توجد روابط محفوظة",
    },
    "no_quality": {
        "fa": "کیفیتی یافت نشد",
        "en": "No quality found",
        "ar": "لم يُعثر على جودة",
    },
    "coming_soon_ai": {
        "fa": "به‌زودی — تحلیل هوش مصنوعی",
        "en": "Coming soon — AI analysis",
        "ar": "قريباً — تحليل بالذكاء الاصطناعي",
    },
    "ai_analyzing": {
        "fa": "⏳ در حال تماشای ریل و استخراج فریم‌ها…",
        "en": "⏳ Watching reel & extracting frames…",
        "ar": "⏳ جاري تحليل الريل…",
    },
    "ai_report_header": {
        "fa": "🤖 <b>تحلیل هوشمند پست</b>",
        "en": "🤖 <b>AI post analysis</b>",
        "ar": "🤖 <b>تحليل المنشور بالذكاء الاصطناعي</b>",
    },
    "ai_not_configured": {
        "fa": "❌ تحلیل AI غیرفعال است — OPENAI_API_KEY را در Railway بگذار (کلید از platform.openai.com).",
        "en": "❌ AI analysis disabled — set OPENAI_API_KEY in Railway (from platform.openai.com).",
        "ar": "❌ تحليل AI معطّل — عيّن OPENAI_API_KEY.",
    },
    "ai_pro_required": {
        "fa": "⭐ تحلیل AI فقط برای <b>Pro</b> است.\n/subscribe",
        "en": "⭐ AI analysis is <b>Pro</b> only.\n/subscribe",
        "ar": "⭐ تحليل AI لـ <b>Pro</b> فقط.\n/subscribe",
    },
    "ai_limit_reached": {
        "fa": "❌ سقف تحلیل ماهانه تمام شد. /subscribe",
        "en": "❌ Monthly analysis limit reached. /subscribe",
        "ar": "❌ تم الوصول لحد التحليل الشهري. /subscribe",
    },
    "ai_failed": {
        "fa": "❌ تحلیل ناموفق بود. دوباره امتحان کن.",
        "en": "❌ Analysis failed. Try again.",
        "ar": "❌ فشل التحليل. حاول مجدداً.",
    },
    "ai_status_download": {
        "fa": "⏳ در حال دانلود و تحلیل ویدیو...",
        "en": "⏳ Downloading and analyzing video...",
        "ar": "⏳ جاري تحميل وتحليل الفيديو...",
    },
    "ai_status_technical": {
        "fa": "🎬 استخراج اطلاعات فنی...",
        "en": "🎬 Extracting technical info...",
        "ar": "🎬 استخراج المعلومات التقنية...",
    },
    "ai_status_audio": {
        "fa": "🎵 تحلیل موزیک و صدا...",
        "en": "🎵 Analyzing audio...",
        "ar": "🎵 تحليل الصوت...",
    },
    "ai_status_frames": {
        "fa": "🖼 استخراج فریم‌های کلیدی...",
        "en": "🖼 Extracting key frames...",
        "ar": "🖼 استخراج الإطارات...",
    },
    "ai_status_visual": {
        "fa": "🤖 تحلیل بصری با AI...",
        "en": "🤖 Visual AI analysis...",
        "ar": "🤖 تحليل بصري بالذكاء الاصطناعي...",
    },
    "ai_video_too_large": {
        "fa": "❌ حجم ویدیو بیش از حد مجاز است (حداکثر ۲۰ مگابایت).",
        "en": "❌ Video is too large (max 20 MB).",
        "ar": "❌ حجم الفيديو كبير جداً (الحد 20 ميجابايت).",
    },
    "ai_no_video": {
        "fa": "❌ ویدیویی برای تحلیل پیدا نشد.",
        "en": "❌ No video found to analyze.",
        "ar": "❌ لم يُعثر على فيديو للتحليل.",
    },
    "ai_already_running": {
        "fa": "⏳ تحلیل قبلی هنوز در حال اجراست. چند ثانیه صبر کن.",
        "en": "⏳ Analysis already running. Wait a moment.",
        "ar": "⏳ التحليل قيد التشغيل. انتظر قليلاً.",
    },
    "ai_deps_missing": {
        "fa": "❌ پکیج‌های تحلیل صدا نصب نیستند (librosa). pip install librosa numpy",
        "en": "❌ Audio analysis deps missing. pip install librosa numpy",
        "ar": "❌ حزم تحليل الصوت غير مثبتة. pip install librosa numpy",
    },
    "ai_auth_failed": {
        "fa": "❌ کلید API OpenAI نامعتبر است.\nOPENAI_API_KEY را در Railway بررسی کن (از platform.openai.com).",
        "en": "❌ Invalid OpenAI API key.\nCheck OPENAI_API_KEY in Railway (platform.openai.com).",
        "ar": "❌ مفتاح OpenAI API غير صالح.\nتحقق من OPENAI_API_KEY.",
    },
    "ai_api_error": {
        "fa": "❌ سرویس هوش مصنوعی موقتاً در دسترس نیست. چند دقیقه بعد دوباره امتحان کن.",
        "en": "❌ AI service temporarily unavailable. Try again in a few minutes.",
        "ar": "❌ خدمة الذكاء الاصطناعي غير متاحة مؤقتاً. حاول لاحقاً.",
    },
    "ai_rate_limit": {
        "fa": "❌ سقف درخواست AI پر شده. چند دقیقه صبر کن.",
        "en": "❌ AI rate limit reached. Wait a few minutes.",
        "ar": "❌ تم تجاوز حد طلبات AI. انتظر قليلاً.",
    },
    "ai_progress_eta": {
        "fa": "⏱ حدود {eta} ثانیه باقی‌مانده",
        "en": "⏱ ~{eta}s remaining",
        "ar": "⏱ ~{eta} ثانية متبقية",
    },
    "video_upload_hint": {
        "fa": "🎬 ویدیو دریافت شد. برای تحلیل کامل روی دکمه زیر بزن:",
        "en": "🎬 Video received. Tap below to run full analysis:",
        "ar": "🎬 تم استلام الفيديو. اضغط الزر للتحليل:",
    },
    "coming_soon_subs": {
        "fa": "به‌زودی — زیرنویس ویدیو",
        "en": "Coming soon — video subtitles",
        "ar": "قريباً — ترجمة الفيديو",
    },
    "coming_soon_audio": {
        "fa": "به‌زودی — دانلود صدا",
        "en": "Coming soon — audio download",
        "ar": "قريباً — تحميل الصوت",
    },
    "refreshing": {
        "fa": "⏳ در حال بروزرسانی…",
        "en": "⏳ Refreshing…",
        "ar": "⏳ جاري التحديث…",
    },
    "download_failed": {
        "fa": "❌ دانلود ناموفق. لینک را دوباره بفرست.",
        "en": "❌ Download failed. Send the link again.",
        "ar": "❌ فشل التحميل. أرسل الرابط مجدداً.",
    },
    "download_error": {
        "fa": "❌ خطا در دانلود. از «دریافت لینک» استفاده کن.",
        "en": "❌ Download error. Use «Get download link».",
        "ar": "❌ خطأ في التحميل. استخدم «رابط التحميل».",
    },
    "watch_need_connect": {
        "fa": "برای لیست نظارت ابتدا /connect کن.",
        "en": "Connect your page with /connect first.",
        "ar": "اربط حسابك بـ /connect أولاً.",
    },
    "watch_usage": {
        "fa": "/watch add username\n/watch list\n/watch remove username",
        "en": "/watch add username\n/watch list\n/watch remove username",
        "ar": "/watch add username\n/watch list\n/watch remove username",
    },
    "watch_empty": {
        "fa": "لیست خالی است.",
        "en": "Watchlist is empty.",
        "ar": "القائمة فارغة.",
    },
    "watch_list_title": {
        "fa": "👁 <b>لیست نظارت:</b>",
        "en": "👁 <b>Watchlist:</b>",
        "ar": "👁 <b>قائمة المراقبة:</b>",
    },
    "watch_need_username": {
        "fa": "یوزرنیم را وارد کن.",
        "en": "Enter a username.",
        "ar": "أدخل اسم المستخدم.",
    },
    "watch_added": {
        "fa": "✅ @{username} اضافه شد.",
        "en": "✅ @{username} added.",
        "ar": "✅ تمت إضافة @{username}.",
    },
    "watch_removed": {
        "fa": "🗑 @{username} حذف شد.",
        "en": "🗑 @{username} removed.",
        "ar": "🗑 تم حذف @{username}.",
    },
    "watch_bad_command": {
        "fa": "دستور نامعتبر.",
        "en": "Invalid command.",
        "ar": "أمر غير صالح.",
    },
    "downloading": {
        "fa": "⏳ دانلود {label}…",
        "en": "⏳ Downloading {label}…",
        "ar": "⏳ تحميل {label}…",
    },
}

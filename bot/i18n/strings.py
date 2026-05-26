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

⚡ برای استفاده ساده، <b>دایرکت دانلود</b> — لینک یا یوزرنیم اینستاگرام را بفرست.

🔐 اتصال پیج شخصی: /connect

همه امکانات فعلاً <b>رایگان</b> است.

از دکمه آبی <b>Menu</b> کنار چت استفاده کن 👇""",
        "en": f"""Hi! 👋 Welcome to <b>{NAME}</b>.

⚡ <b>Direct download</b> — send an Instagram link or username.

🔐 Connect your page: /connect

Everything is <b>free</b> for now.

Use the blue <b>Menu</b> button next to the chat 👇""",
        "ar": f"""مرحباً! 👋 أهلاً بك في <b>{NAME}</b>.

⚡ <b>تحميل مباشر</b> — أرسل رابط أو اسم مستخدم إنستغرام.

🔐 ربط حسابك: /connect

كل الميزات <b>مجانية</b> حالياً.

استخدم زر <b>Menu</b> الأزرق بجانب المحادثة 👇""",
    },
    "features": {
        "fa": f"""💬 <b>امکانات {NAME}</b>

همه امکانات فعلاً <b>رایگان</b> هستند.

<b>⚡ دایرکت دانلود:</b>
• لینک پست / ریل / کاروسel
• استوری، هایلایت، پروفایل HD

<b>🔐 اتصال پیج:</b> /connect → کد → دایرکت {BRIDGE}

<b>دستورات:</b>
<code>highlights user</code> | <code>zip stories user</code> | <code>#tag</code>""",
        "en": f"""💬 <b>{NAME} features</b>

All features are <b>free</b> for now.

<b>⚡ Direct download:</b>
• Post / Reel / carousel links
• Stories, highlights, HD profile

<b>🔐 Connect page:</b> /connect → code → DM {BRIDGE}

<b>Commands:</b>
<code>highlights user</code> | <code>zip stories user</code> | <code>#tag</code>""",
        "ar": f"""💬 <b>ميزات {NAME}</b>

كل الميزات <b>مجانية</b> حالياً.

<b>⚡ تحميل مباشر:</b>
• روابط المنشور / الريل / الكاروسel
• القصص، الهايلايت، الملف الشخصي

<b>🔐 ربط الحساب:</b> /connect → رمز → رسالة {BRIDGE}

<b>أوامر:</b>
<code>highlights user</code> | <code>zip stories user</code> | <code>#tag</code>""",
    },
    "help_direct": {
        "fa": f"""⚡ <b>دایرکت دانلود</b>

<b>لینک</b> پست / ریل را بفرست.

پروفایل/استوری (اختیاری):
• یوزرنیم — <code>instagram</code>
• <code>highlights user</code>

<b>اتصال پیج:</b> /connect → کد را به {BRIDGE} بفرست.""",
        "en": f"""⚡ <b>Direct download</b>

Send a <b>post / Reel link</b>.

Profile/stories (optional):
• Username — <code>instagram</code>
• <code>highlights user</code>

<b>Connect:</b> /connect → send code to {BRIDGE}.""",
        "ar": f"""⚡ <b>تحميل مباشر</b>

أرسل <b>رابط منشور / ريل</b>.

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
    "connect_invalid_username": {
        "fa": "یوزرنیم نامعتبر است.",
        "en": "Invalid username.",
        "ar": "اسم المستخدم غير صالح.",
    },
    "connect_bridge_offline": {
        "fa": (
            "\n\n⚠️ <b>توجه:</b> سرویس دریافت دایرکت اینستاگرام الان آفلاین است. "
            "تا وقتی ادمین اکانت bridge را وصل نکند، کد تأیید خوانده نمی‌شود."
        ),
        "en": (
            "\n\n⚠️ <b>Note:</b> Instagram DM bridge is offline. "
            "Your code cannot be read until the bridge account is configured."
        ),
        "ar": (
            "\n\n⚠️ <b>تنبيه:</b> جسر رسائل إنستغرام غير متصل. "
            "لن يُقرأ الرمز حتى يتم إعداد حساب الجسر."
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
            "کد تأیید: <code>{code}</code>\n\n"
            "این کد را در <b>دایرکت اینستاگرام</b> به {bridge} بفرست.\n"
            "⏱ تا {ttl} دقیقه معتبر است.\n\n"
            "بعد از چند دقیقه پیام «متصل شد» می‌گیری."
        ),
        "en": (
            "✅ Page: <b>@{username}</b>\n\n"
            "Verification code: <code>{code}</code>\n\n"
            "Send this code in <b>Instagram DM</b> to {bridge}.\n"
            "⏱ Valid for {ttl} minutes.\n\n"
            "You will get a «connected» message shortly."
        ),
        "ar": (
            "✅ الحساب: <b>@{username}</b>\n\n"
            "رمز التحقق: <code>{code}</code>\n\n"
            "أرسل هذا الرمز في <b>رسالة إنستغرام</b> إلى {bridge}.\n"
            "⏱ صالح لمدة {ttl} دقيقة.\n\n"
            "ستصلك رسالة «تم الربط» قريباً."
        ),
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
            "⚡ دایرکت دانلود (Apify): {apify}\n"
            "📥 دانلود لینک: {svc}{ig_extra}\n"
            "💬 پل اتصال {bridge}: {brg}\n"
            "🔗 پیج تو: {page}"
        ),
        "en": (
            "<b>{name}</b>\n\n"
            "⚡ Direct download (Apify): {apify}\n"
            "📥 Link download: {svc}{ig_extra}\n"
            "💬 Bridge {bridge}: {brg}\n"
            "🔗 Your page: {page}"
        ),
        "ar": (
            "<b>{name}</b>\n\n"
            "⚡ تحميل مباشر (Apify): {apify}\n"
            "📥 تحميل الروابط: {svc}{ig_extra}\n"
            "💬 جسر {bridge}: {brg}\n"
            "🔗 حسابك: {page}"
        ),
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
            "لینک‌ها را اینجا یا در دایرکت {bridge} بفرست."
        ),
        "en": (
            "📩 <b>My Instagram</b>\n\n"
            "✅ Connected to @{username}\n"
            "📅 Since: {date}\n\n"
            "Send links here or DM {bridge}."
        ),
        "ar": (
            "📩 <b>إنستغرامي</b>\n\n"
            "✅ مرتبط بـ @{username}\n"
            "📅 منذ: {date}\n\n"
            "أرسل الروابط هنا أو إلى {bridge}."
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

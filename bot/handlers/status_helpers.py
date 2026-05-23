from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import WatchlistEntry
from bot.services.apify import apify_downloader
from bot.services.client_pool import client_pool
from bot.services.direct_download import direct_download_ready
from bot.services.verification import get_connection
from sqlalchemy import select


async def build_status_text(telegram_id: int) -> str:
    apify = "✅" if apify_downloader.ready else "❌"
    svc = "✅" if direct_download_ready() else "❌"
    ig_extra = " (instagrapi)" if client_pool.service_ready else ""
    brg = "✅" if client_pool.bridge_ready else "❌"
    conn = await get_connection(telegram_id)

    if conn and conn.status == "connected":
        page = f"✅ @{conn.instagram_username}"
    elif conn and conn.status == "pending":
        page = f"⏳ منتظر کد — @{conn.instagram_username}"
    else:
        page = "❌ متصل نیست — /connect"

    return (
        f"<b>{settings.bot_name}</b>\n\n"
        f"⚡ دایرکت دانلود (Apify): {apify}\n"
        f"📥 دانلود لینک: {svc}{ig_extra}\n"
        f"💬 پل اتصال پیج {settings.bridge_ig_handle}: {brg}\n"
        f"🔗 پیج اینستاگرام تو: {page}"
    )


async def build_myinstagram_text(telegram_id: int) -> str:
    conn = await get_connection(telegram_id)
    if not conn:
        return (
            "📩 <b>اینستاگرام من</b>\n\n"
            "هنوز پیجی متصل نیست.\n"
            "با /connect یا دکمه زیر وصل شو."
        )
    if conn.status == "pending":
        return (
            f"📩 <b>اینستاگرام من</b>\n\n"
            f"پیج: @{conn.instagram_username}\n"
            f"⏳ در انتظار کد تأیید…\n"
            f"کد را در دایرکت {settings.bridge_ig_handle} بفرست."
        )
    connected_at = ""
    if conn.connected_at:
        connected_at = conn.connected_at.strftime("%Y-%m-%d %H:%M")
    return (
        f"📩 <b>اینستاگرام من</b>\n\n"
        f"✅ متصل به @{conn.instagram_username}\n"
        f"📅 از: {connected_at or '—'}\n\n"
        f"لینک‌ها را اینجا یا در دایرکت {settings.bridge_ig_handle} بفرست."
    )


async def build_feed_text(telegram_id: int) -> str:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(WatchlistEntry).where(WatchlistEntry.telegram_id == telegram_id)
            )
        ).scalars().all()

    if not rows:
        return (
            "🗄️ <b>فید</b>\n\n"
            "لیست خالی است.\n"
            "<code>/watch add username</code> — افزودن پیج\n\n"
            "نیاز به اتصال پیج: /connect"
        )

    lines = ["🗄️ <b>فید — پیج‌های تحت نظر</b>\n"]
    for r in rows:
        lines.append(f"• @{r.instagram_username}")
    lines.append("\nبرای دانلود پست جدید، لینک یا یوزرنیم بفرست.")
    lines.append("/watch list — مدیریت لیست")
    return "\n".join(lines)

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import WatchlistEntry
from bot.i18n import require_user_lang, t, tu
from bot.services.apify import apify_downloader
from bot.services.client_pool import client_pool
from bot.services.direct_download import direct_download_ready
from bot.services.verification import get_connection
from sqlalchemy import select


async def build_status_text(telegram_id: int) -> str:
    lang = await require_user_lang(telegram_id)
    apify = "✅" if apify_downloader.ready else "❌"
    svc = "✅" if direct_download_ready() else "❌"
    ig_extra = " (instagrapi)" if client_pool.service_ready else ""
    brg = "✅" if client_pool.bridge_ready else "❌"
    conn = await get_connection(telegram_id)

    if conn and conn.status == "connected":
        page = f"✅ @{conn.instagram_username}"
    elif conn and conn.status == "pending":
        page = t("status_pending", lang, username=conn.instagram_username)
    else:
        page = t("status_not_connected", lang)

    return t(
        "status_body",
        lang,
        name=settings.bot_name,
        apify=apify,
        svc=svc,
        ig_extra=ig_extra,
        bridge=settings.bridge_ig_handle,
        brg=brg,
        page=page,
    )


async def build_myinstagram_text(telegram_id: int) -> str:
    lang = await require_user_lang(telegram_id)
    conn = await get_connection(telegram_id)
    bridge = settings.bridge_ig_handle

    if not conn:
        return t("myig_none", lang)
    if conn.status == "pending":
        return t(
            "myig_pending",
            lang,
            username=conn.instagram_username,
            bridge=bridge,
        )
    connected_at = ""
    if conn.connected_at:
        connected_at = conn.connected_at.strftime("%Y-%m-%d %H:%M")
    return t(
        "myig_connected",
        lang,
        username=conn.instagram_username,
        date=connected_at or "—",
        bridge=bridge,
    )


async def build_feed_text(telegram_id: int) -> str:
    lang = await require_user_lang(telegram_id)
    async with async_session() as session:
        rows = (
            await session.execute(
                select(WatchlistEntry).where(WatchlistEntry.telegram_id == telegram_id)
            )
        ).scalars().all()

    if not rows:
        return t("feed_empty", lang)

    lines = [t("feed_title", lang)]
    for r in rows:
        lines.append(f"• @{r.instagram_username}")
    lines.append(t("feed_footer", lang))
    return "\n".join(lines)

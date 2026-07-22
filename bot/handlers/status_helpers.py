from bot.config import settings
from bot.handlers.connect_hints import connected_usage_hint
from bot.db.engine import async_session
from bot.db.models import WatchlistEntry
from bot.i18n import require_user_lang, t, tu
from bot.keyboards import subscription_shop_kb
from bot.services.apify import apify_downloader
from bot.services.client_pool import client_pool
from bot.services.direct_download import direct_download_ready
from bot.services.hikerapi import hiker_client
from bot.services.subscription import (
    direct_link_downloads_remaining,
    get_bot_user,
    has_pro_access,
    is_ai_unlimited,
    is_plan_active,
)
from bot.services.verification import get_connection
from sqlalchemy import select


async def build_status_text(telegram_id: int, username: str | None = None) -> str:
    lang = await require_user_lang(telegram_id)
    apify = "✅" if apify_downloader.ready else "❌"
    svc = "✅" if direct_download_ready() else "❌"
    ig_extra = " (HikerAPI)" if hiker_client.ready else ""
    brg = "✅" if client_pool.bridge_ready else "❌"
    conn = await get_connection(telegram_id)
    user = await get_bot_user(telegram_id)

    if await is_ai_unlimited(telegram_id, username):
        sub_line = t("status_plan_vip", lang)
    elif is_plan_active(user) and user and user.subscription_plan in (
        "download",
        "pro",
        "premium",
    ):
        exp = user.subscription_expires_at
        exp_text = exp.strftime("%Y-%m-%d") if exp else "—"
        sub_line = t("status_plan_pro", lang, plan="PRO", date=exp_text)
    else:
        left = await direct_link_downloads_remaining(telegram_id, username)
        sub_line = t(
            "status_plan_free",
            lang,
            left=left,
            total=settings.free_direct_downloads,
            pro_stars=settings.pro_stars_price,
        )

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
        plan=sub_line,
    )


async def build_settings_message(
    telegram_id: int, username: str | None = None
) -> tuple[str, object | None]:
    lang = await require_user_lang(telegram_id)
    status = await build_status_text(telegram_id, username)
    kb = None
    vip = await is_ai_unlimited(telegram_id, username)
    if settings.stars_payment_enabled and not vip:
        kb = subscription_shop_kb(lang)
    text = await tu(telegram_id, "settings") + "\n\n" + status
    if settings.stars_payment_enabled and not vip and not await has_pro_access(
        telegram_id, username
    ):
        text += "\n\n" + t(
            "shop_upsell_short",
            lang,
            pro_stars=settings.pro_stars_price,
            free_total=settings.free_direct_downloads,
        )
    return text, kb


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
        usage=connected_usage_hint(lang, username=conn.instagram_username),
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

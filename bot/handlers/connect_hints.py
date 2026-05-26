from bot.config import settings
from bot.i18n import Lang, t
from bot.services.client_pool import client_pool


def connected_usage_hint(lang: Lang, username: str = "") -> str:
    bridge = settings.bridge_ig_handle
    if client_pool.bridge_ready:
        return t(
            "verify_ok_ig_dm_active",
            lang,
            bridge=bridge,
            username=username or "…",
        )
    return t("verify_ok_ig_dm_offline", lang, bridge=bridge)

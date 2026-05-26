from bot.config import settings
from bot.i18n import Lang, t
from bot.services.client_pool import client_pool


def connected_usage_hint(lang: Lang) -> str:
    bridge = settings.bridge_ig_handle
    if client_pool.bridge_ready:
        return t("verify_ok_dm_also", lang, bridge=bridge)
    return t("verify_ok_use_telegram", lang, bridge=bridge)

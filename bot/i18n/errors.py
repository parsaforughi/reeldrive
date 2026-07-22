"""Map backend exceptions to user-friendly localized messages."""

import logging

from instagrapi.exceptions import LoginRequired

from bot.i18n.core import Lang, t

logger = logging.getLogger(__name__)


_KNOWN_VALUE_KEYS = frozenset(
    {
        "ai_not_configured",
        "ai_pro_required",
        "ai_limit_reached",
        "ai_video_too_large",
        "ai_no_video",
        "ai_already_running",
        "ai_deps_missing",
        "ai_auth_failed",
        "ai_api_error",
        "ai_rate_limit",
    }
)


def friendly_error(exc: Exception, lang: Lang) -> str:
    if isinstance(exc, LoginRequired):
        return t("error_login_required", lang)

    if isinstance(exc, ValueError):
        key = str(exc)
        if key in _KNOWN_VALUE_KEYS:
            return t(key, lang)
        raw = key.lower()
        if raw.startswith("ai error"):
            return t("ai_api_error", lang)
        if any(x in raw for x in ("hikerapi", "402")):
            return t("error_hikerapi", lang)
        if any(x in raw for x in ("invalid token", "incorrect api key", "authentication")):
            return t("ai_auth_failed", lang)
        if any(
            x in raw
            for x in (
                "not found",
                "پیدا",
                "یافت",
                "no items",
                "empty",
                "خالی",
            )
        ):
            return t("error_not_found", lang)
        if any(x in raw for x in ("private", "خصوص", "login", "challenge")):
            return t("error_private", lang)
        if any(x in raw for x in ("rate", "limit", "429", "too many", "زیاد")):
            return t("error_rate_limit", lang)
        logger.warning("Unhandled ValueError for user: %s", exc)
        return t("error_generic", lang)

    if isinstance(exc, (TimeoutError,)):
        return t("error_rate_limit", lang)

    logger.exception("Unhandled error shown to user")
    return t("error_generic", lang)

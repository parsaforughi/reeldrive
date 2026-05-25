"""Map backend exceptions to user-friendly localized messages."""

import logging

from instagrapi.exceptions import LoginRequired

from bot.i18n.core import Lang, t

logger = logging.getLogger(__name__)


def friendly_error(exc: Exception, lang: Lang) -> str:
    if isinstance(exc, LoginRequired):
        return t("error_login_required", lang)

    if isinstance(exc, ValueError):
        raw = str(exc).lower()
        if any(x in raw for x in ("apify", "توکن", "token", "اعتبار", "402", "401", "403")):
            return t("error_apify", lang)
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
        return t("error_not_found", lang)

    if isinstance(exc, (TimeoutError,)):
        return t("error_rate_limit", lang)

    logger.exception("Unhandled error shown to user")
    return t("error_generic", lang)

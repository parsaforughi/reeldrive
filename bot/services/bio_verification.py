"""Verify page ownership by placing the code in Instagram bio (Apify, no IG session)."""

import logging

from bot.i18n import Lang
from bot.services.apify import apify_downloader
from bot.services.verification import (
    confirm_connection,
    extract_verification_code,
    get_connection,
)

logger = logging.getLogger(__name__)


def _bio_contains_code(biography: str, code: str) -> bool:
    if not biography or not code:
        return False
    bio_upper = biography.upper()
    code_upper = code.strip().upper()
    if code_upper in bio_upper:
        return True
    return extract_verification_code(biography) == code_upper


async def verify_pending_via_bio(telegram_id: int) -> tuple[bool, str]:
    """
    Returns (success, reason_key).
    reason_key: ok | no_pending | expired | apify | not_in_bio | private
    """
    conn = await get_connection(telegram_id)
    if not conn or conn.status != "pending":
        return False, "no_pending"
    if not conn.verification_code:
        return False, "no_pending"

    if not apify_downloader.ready:
        return False, "apify"

    username = conn.instagram_username
    code = conn.verification_code

    try:
        item = await apify_downloader.fetch_profile_item(username)
    except ValueError as exc:
        logger.warning("Bio verify Apify error for @%s: %s", username, exc)
        return False, "apify"
    except Exception:
        logger.exception("Bio verify failed for @%s", username)
        return False, "apify"

    if item.get("private") is True or item.get("isPrivate") is True:
        return False, "private"

    bio = apify_downloader.profile_biography(item)
    if not _bio_contains_code(bio, code):
        logger.info(
            "Bio verify: code %s not in @%s bio (len=%s)",
            code,
            username,
            len(bio),
        )
        return False, "not_in_bio"

    ig_id = apify_downloader.profile_user_id(item) or username
    await confirm_connection(telegram_id, ig_id, username)
    logger.info("Bio verify OK: telegram %s → @%s", telegram_id, username)
    return True, "ok"

"""Verify page ownership through public profile APIs, without an IG session."""

import logging

from bot.i18n import Lang
from bot.services.apify import apify_downloader
from bot.services.hikerapi import hiker_client
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

    if not hiker_client.ready and not apify_downloader.ready:
        return False, "apify"

    username = conn.instagram_username
    code = conn.verification_code

    item: dict | None = None
    provider = ""
    if hiker_client.ready:
        try:
            item = await hiker_client.fetch_profile_item(username)
            provider = "HikerAPI"
        except Exception:
            logger.warning(
                "Bio verify HikerAPI error for @%s; trying fallback",
                username,
                exc_info=True,
            )
    if item is None and apify_downloader.ready:
        try:
            item = await apify_downloader.fetch_profile_item(username)
            provider = "Apify"
        except Exception:
            logger.warning("Bio verify Apify error for @%s", username, exc_info=True)
    if item is None:
        return False, "apify"

    if any(item.get(key) is True for key in ("private", "isPrivate", "is_private")):
        return False, "private"

    bio = (
        hiker_client.profile_biography(item)
        if provider == "HikerAPI"
        else apify_downloader.profile_biography(item)
    )
    if not _bio_contains_code(bio, code):
        logger.info(
            "Bio verify: code %s not in @%s bio (len=%s)",
            code,
            username,
            len(bio),
        )
        return False, "not_in_bio"

    ig_id = (
        hiker_client.profile_user_id(item)
        if provider == "HikerAPI"
        else apify_downloader.profile_user_id(item)
    ) or username
    await confirm_connection(telegram_id, ig_id, username)
    logger.info("Bio verify OK: telegram %s → @%s", telegram_id, username)
    return True, "ok"

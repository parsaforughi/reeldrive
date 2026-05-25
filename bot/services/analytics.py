"""Track bot users and activity for the admin dashboard."""

import json
import logging
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from bot.db.engine import async_session
from bot.db.models import ActivityLog, BotUser
from bot.time_utils import utc_now

logger = logging.getLogger(__name__)


def _user_from_event(event: TelegramObject) -> User | None:
    if isinstance(event, Message) and event.from_user:
        return event.from_user
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user
    return None


async def touch_user(user: User, *, event_type: str = "message") -> None:
    if user.is_bot:
        return
    now = utc_now()
    async with async_session() as session:
        row = await session.get(BotUser, user.id)
        if row:
            row.username = user.username
            row.first_name = user.first_name
            row.last_name = user.last_name
            row.last_seen_at = now
            if event_type == "command":
                row.command_count = (row.command_count or 0) + 1
        else:
            session.add(
                BotUser(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language="",
                    first_seen_at=now,
                    last_seen_at=now,
                    command_count=1 if event_type == "command" else 0,
                )
            )
        await session.commit()


async def log_activity(
    telegram_id: int | None,
    event_type: str,
    detail: str = "",
    meta: dict | None = None,
) -> None:
    try:
        async with async_session() as session:
            session.add(
                ActivityLog(
                    telegram_id=telegram_id,
                    event_type=event_type,
                    detail=detail[:2000] if detail else None,
                    meta_json=json.dumps(meta, ensure_ascii=False)[:4000]
                    if meta
                    else None,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to log activity %s", event_type)


async def record_download(telegram_id: int, url: str = "", *, user_label: str = "") -> None:
    now = utc_now()
    async with async_session() as session:
        row = await session.get(BotUser, telegram_id)
        if row:
            row.download_count = (row.download_count or 0) + 1
            row.last_seen_at = now
            await session.commit()
    detail = f"{user_label}: {url[:480]}" if user_label else url[:500]
    await log_activity(telegram_id, "download", detail=detail)


async def event_summary(event: TelegramObject) -> tuple[str, str, dict]:
    if isinstance(event, Message):
        text = (event.text or event.caption or "")[:200]
        if event.text and event.text.startswith("/"):
            return "command", event.text.split()[0], {}
        if "instagram.com" in text:
            return "download_request", text[:200], {}
        return "message", text, {}
    if isinstance(event, CallbackQuery):
        return "callback", event.data or "", {}
    return "event", type(event).__name__, {}

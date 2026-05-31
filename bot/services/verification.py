import re
import secrets
from datetime import timedelta

from sqlalchemy import select, update

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import UserConnection
from bot.services.analytics import log_activity
from bot.time_utils import utc_now

VERIFICATION_CODE_RE = re.compile(r"\b([A-F0-9]{6})\b", re.IGNORECASE)


def generate_code() -> str:
    return secrets.token_hex(3).upper()


def extract_verification_code(text: str) -> str | None:
    """Find 6-char hex code inside DM text (e.g. only 'B7D9D6' or 'code B7D9D6')."""
    match = VERIFICATION_CODE_RE.search((text or "").strip())
    return match.group(1).upper() if match else None


async def start_verification(telegram_id: int, instagram_username: str) -> str:
    code = generate_code()
    expires = utc_now() + timedelta(minutes=settings.verification_code_ttl_minutes)
    username = instagram_username.lower().lstrip("@")

    async with async_session() as session:
        existing = await session.get(UserConnection, telegram_id)
        if existing:
            existing.instagram_username = username
            existing.status = "pending"
            existing.verification_code = code
            existing.code_expires_at = expires
            existing.connected_at = None
        else:
            session.add(
                UserConnection(
                    telegram_id=telegram_id,
                    instagram_username=username,
                    status="pending",
                    verification_code=code,
                    code_expires_at=expires,
                )
            )
        await session.commit()
    return code


async def get_pending_by_code(code: str) -> UserConnection | None:
    code = extract_verification_code(code) or code.strip().upper()
    if len(code) != 6:
        return None
    now = utc_now()
    async with async_session() as session:
        result = await session.execute(
            select(UserConnection).where(
                UserConnection.verification_code == code,
                UserConnection.status == "pending",
            )
        )
        row = result.scalar_one_or_none()
        if not row or not row.code_expires_at:
            return None
        if row.code_expires_at < now:
            return None
        return row


async def confirm_connection(
    telegram_id: int, instagram_user_id: str, instagram_username: str
) -> None:
    now = utc_now()
    async with async_session() as session:
        await session.execute(
            update(UserConnection)
            .where(UserConnection.telegram_id == telegram_id)
            .values(
                status="connected",
                instagram_user_id=instagram_user_id,
                instagram_username=instagram_username.lower(),
                verification_code=None,
                code_expires_at=None,
                connected_at=now,
            )
        )
        await session.commit()
    await log_activity(
        telegram_id,
        "connect_ok",
        detail=f"@{instagram_username}",
    )


async def get_connection(telegram_id: int) -> UserConnection | None:
    async with async_session() as session:
        return await session.get(UserConnection, telegram_id)


async def disconnect(telegram_id: int) -> bool:
    async with async_session() as session:
        row = await session.get(UserConnection, telegram_id)
        if not row:
            return False
        await session.delete(row)
        await session.commit()
        return True


async def get_connected_by_ig_user_id(ig_user_id: str) -> UserConnection | None:
    async with async_session() as session:
        result = await session.execute(
            select(UserConnection).where(
                UserConnection.instagram_user_id == str(ig_user_id),
                UserConnection.status == "connected",
            )
        )
        return result.scalar_one_or_none()


async def get_connected_by_username(username: str) -> UserConnection | None:
    username = username.lower().lstrip("@")
    async with async_session() as session:
        result = await session.execute(
            select(UserConnection).where(
                UserConnection.instagram_username == username,
                UserConnection.status == "connected",
            )
        )
        return result.scalar_one_or_none()

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import UserConnection


def generate_code() -> str:
    return secrets.token_hex(3).upper()


async def start_verification(telegram_id: int, instagram_username: str) -> str:
    code = generate_code()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.verification_code_ttl_minutes
    )
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
    code = code.strip().upper()
    now = datetime.now(timezone.utc)
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
        expires = row.code_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            return None
        return row


async def confirm_connection(
    telegram_id: int, instagram_user_id: str, instagram_username: str
) -> None:
    now = datetime.now(timezone.utc)
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

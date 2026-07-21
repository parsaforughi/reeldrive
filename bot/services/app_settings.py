"""Generic runtime-editable key/value settings, stored in the DB so admin
panel changes (e.g. the payment card number) take effect immediately
instead of requiring an env var change + redeploy."""

from sqlalchemy import select

from bot.db.engine import async_session
from bot.db.models import AppSetting


async def get_setting(key: str) -> str | None:
    async with async_session() as session:
        return await session.scalar(select(AppSetting.value).where(AppSetting.key == key))


async def set_setting(key: str, value: str) -> None:
    async with async_session() as session:
        row = await session.get(AppSetting, key)
        if row:
            row.value = value
        else:
            session.add(AppSetting(key=key, value=value))
        await session.commit()

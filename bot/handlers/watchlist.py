from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, select

from bot.db.engine import async_session
from bot.db.models import WatchlistEntry
from bot.i18n import tu
from bot.services.verification import get_connection

router = Router()


@router.message(Command("watch"))
async def cmd_watch(message: Message) -> None:
    uid = message.from_user.id
    conn = await get_connection(uid)
    if not conn or conn.status != "connected":
        await message.answer(await tu(uid, "watch_need_connect"))
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(await tu(uid, "watch_usage"))
        return

    action = parts[1].lower()
    tg_id = uid

    if action == "list":
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(WatchlistEntry).where(
                        WatchlistEntry.telegram_id == tg_id
                    )
                )
            ).scalars().all()
        if not rows:
            await message.answer(await tu(uid, "watch_empty"))
            return
        text = await tu(uid, "watch_list_title") + "\n" + "\n".join(
            f"• @{r.instagram_username}" for r in rows
        )
        await message.answer(text)
        return

    if len(parts) < 3:
        await message.answer(await tu(uid, "watch_need_username"))
        return

    username = parts[2].lstrip("@").lower()

    if action == "add":
        async with async_session() as session:
            session.add(
                WatchlistEntry(telegram_id=tg_id, instagram_username=username)
            )
            await session.commit()
        await message.answer(await tu(uid, "watch_added", username=username))
        return

    if action == "remove":
        async with async_session() as session:
            await session.execute(
                delete(WatchlistEntry).where(
                    WatchlistEntry.telegram_id == tg_id,
                    WatchlistEntry.instagram_username == username,
                )
            )
            await session.commit()
        await message.answer(await tu(uid, "watch_removed", username=username))
        return

    await message.answer(await tu(uid, "watch_bad_command"))

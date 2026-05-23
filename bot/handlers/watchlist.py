from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, select

from bot.db.engine import async_session
from bot.db.models import WatchlistEntry
from bot.services.verification import get_connection

router = Router()


@router.message(Command("watch"))
async def cmd_watch(message: Message) -> None:
    conn = await get_connection(message.from_user.id)
    if not conn or conn.status != "connected":
        await message.answer(
            "برای لیست نظارت ابتدا پیج را /connect کن.\n"
            "Connect your page first with /connect."
        )
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "/watch add username\n/watch list\n/watch remove username"
        )
        return

    action = parts[1].lower()
    tg_id = message.from_user.id

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
            await message.answer("لیست خالی است.\nWatchlist is empty.")
            return
        text = "👁 <b>لیست نظارت:</b>\n" + "\n".join(
            f"• @{r.instagram_username}" for r in rows
        )
        await message.answer(text)
        return

    if len(parts) < 3:
        await message.answer("یوزرنیم را وارد کن.")
        return

    username = parts[2].lstrip("@").lower()

    if action == "add":
        async with async_session() as session:
            session.add(
                WatchlistEntry(telegram_id=tg_id, instagram_username=username)
            )
            await session.commit()
        await message.answer(f"✅ @{username} اضافه شد.")
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
        await message.answer(f"🗑 @{username} حذف شد.")
        return

    await message.answer("دستور نامعتبر.")

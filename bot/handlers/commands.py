from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.keyboards import main_menu_kb
from bot.services.client_pool import client_pool
from bot.services.verification import get_connection
from bot.texts import (
    FEATURES_FA,
    HELP_CONNECT_FA,
    HELP_DIRECT_FA,
    HELP_WATCHLIST_FA,
    START_FA,
)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(START_FA, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(FEATURES_FA)


@router.message(Command("help_directdownload"))
async def cmd_help_direct(message: Message) -> None:
    await message.answer(HELP_DIRECT_FA)


@router.message(Command("help_watchlist"))
async def cmd_help_watchlist(message: Message) -> None:
    await message.answer(HELP_WATCHLIST_FA)


@router.message(Command("help_feed"))
async def cmd_help_feed(message: Message) -> None:
    await message.answer(
        "📰 <b>فید</b>\n"
        "با /watch add پیج‌ها را اضافه کن؛ به‌زودی پست‌های جدید اینجا نمایش داده می‌شود.\n\n"
        "Feed: add pages with /watch — auto notifications coming soon."
    )


@router.message(Command("help_unfollowers"))
async def cmd_help_unfollowers(message: Message) -> None:
    await message.answer(
        "👥 <b>آنفالویاب</b>\n"
        "نیاز به اتصال پیج (/connect) دارد.\n"
        "به‌زودی: مقایسه لیست فالوورها.\n\n"
        "Unfollowers checker — connect page first, feature coming soon."
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    svc = "✅" if client_pool.service_ready else "❌"
    brg = "✅" if client_pool.bridge_ready else "❌"
    conn = await get_connection(message.from_user.id)
    if conn and conn.status == "connected":
        page = f"✅ @{conn.instagram_username}"
    elif conn and conn.status == "pending":
        page = f"⏳ در انتظار کد (@{conn.instagram_username})"
    else:
        page = "❌ متصل نیست"

    await message.answer(
        f"<b>{settings.bot_name}</b> — وضعیت\n\n"
        f"📥 دانلودر IG: {svc}\n"
        f"💬 پل دایرکت ({settings.bridge_ig_handle}): {brg}\n"
        f"🔗 پیج تو: {page}"
    )

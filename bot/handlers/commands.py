from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.config import settings
from bot.handlers.status_helpers import (
    build_feed_text,
    build_myinstagram_text,
    build_status_text,
)
from bot.states import SearchStates
from bot.texts import (
    FEATURES_FA,
    HELP_DIRECT_FA,
    HELP_FEED_FA,
    HELP_SEARCH_FA,
    HELP_UNFOLLOWERS_FA,
    PRIVACY_FA,
    SETTINGS_FA,
    START_FA,
)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_FA, reply_markup=ReplyKeyboardRemove())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(FEATURES_FA)


@router.message(Command("directdownload"))
async def cmd_directdownload(message: Message) -> None:
    await message.answer(HELP_DIRECT_FA)


@router.message(Command("help_directdownload"))
async def cmd_help_direct_legacy(message: Message) -> None:
    await cmd_directdownload(message)


@router.message(Command("myinstagram"))
async def cmd_myinstagram(message: Message) -> None:
    from bot.services.verification import get_connection

    text = await build_myinstagram_text(message.from_user.id)
    conn = await get_connection(message.from_user.id)
    await message.answer(text)


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_query)
    await message.answer(
        HELP_SEARCH_FA + "\n\n🔎 حالا یوزرنیم، #هشتگ یا لینک را بفرست:"
    )


@router.message(Command("unfollowers"))
async def cmd_unfollowers(message: Message) -> None:
    from bot.services.verification import get_connection

    conn = await get_connection(message.from_user.id)
    extra = ""
    if not conn or conn.status != "connected":
        extra = "\n\n⚠️ ابتدا /connect را انجام بده."
    await message.answer(HELP_UNFOLLOWERS_FA + extra)


@router.message(Command("feed"))
async def cmd_feed(message: Message) -> None:
    text = await build_feed_text(message.from_user.id)
    await message.answer(text)


@router.message(Command("help_feed"))
async def cmd_help_feed_legacy(message: Message) -> None:
    await message.answer(HELP_FEED_FA)


@router.message(Command("help_watchlist"))
async def cmd_help_watchlist(message: Message) -> None:
    await message.answer(HELP_FEED_FA)


@router.message(Command("help_unfollowers"))
async def cmd_help_unfollowers_legacy(message: Message) -> None:
    await cmd_unfollowers(message)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    status = await build_status_text(message.from_user.id)
    await message.answer(
        SETTINGS_FA + "\n\n" + status + "\n\nاز دکمه <b>Menu</b> دستورها را ببین."
    )


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(PRIVACY_FA)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer(await build_status_text(message.from_user.id))

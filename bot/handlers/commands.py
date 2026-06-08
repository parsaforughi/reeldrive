from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.handlers.status_helpers import (
    build_feed_text,
    build_myinstagram_text,
    build_settings_message,
    build_status_text,
)
from bot.i18n import get_user_lang, t, tu
from bot.keyboards import language_kb
from bot.services.verification import get_connection
from bot.states import SearchStates

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    if not lang:
        await message.answer(
            t("choose_language", "fa"),
            reply_markup=language_kb(),
        )
        return
    await message.answer(
        t("start", lang),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "features"))


@router.message(Command("directdownload"))
async def cmd_directdownload(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "help_direct"))


@router.message(Command("help_directdownload"))
async def cmd_help_direct_legacy(message: Message) -> None:
    await cmd_directdownload(message)


@router.message(Command("myinstagram"))
async def cmd_myinstagram(message: Message) -> None:
    text = await build_myinstagram_text(message.from_user.id)
    await message.answer(text)


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    await state.set_state(SearchStates.waiting_query)
    await message.answer(
        await tu(uid, "help_search") + "\n\n" + await tu(uid, "search_prompt")
    )


@router.message(Command("unfollowers"))
async def cmd_unfollowers(message: Message) -> None:
    uid = message.from_user.id
    conn = await get_connection(uid)
    extra = ""
    if not conn or conn.status != "connected":
        extra = await tu(uid, "unfollowers_need_connect")
    await message.answer(await tu(uid, "help_unfollowers") + extra)


@router.message(Command("feed"))
async def cmd_feed(message: Message) -> None:
    await message.answer(await build_feed_text(message.from_user.id))


@router.message(Command("help_feed"))
async def cmd_help_feed_legacy(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "help_feed"))


@router.message(Command("help_watchlist"))
async def cmd_help_watchlist(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "help_feed"))


@router.message(Command("help_unfollowers"))
async def cmd_help_unfollowers_legacy(message: Message) -> None:
    await cmd_unfollowers(message)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    uid = message.from_user.id
    text, kb = await build_settings_message(uid)
    await message.answer(text, reply_markup=kb)


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    from bot.handlers.payments import send_pro_invoice

    await send_pro_invoice(message.bot, message.chat.id, message.from_user.id)


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "privacy"))


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer(await build_status_text(message.from_user.id))

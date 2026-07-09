import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import settings
from bot.handlers.download_helpers import send_following_page
from bot.handlers.following_shared import guard_channels, start_following_lookup
from bot.handlers.status_helpers import (
    build_feed_text,
    build_myinstagram_text,
    build_settings_message,
    build_status_text,
)
from bot.i18n import friendly_error, get_user_lang, require_user_lang, t, tu
from bot.keyboards import (
    following_cancel_kb,
    following_pages_kb,
    following_pay_kb,
    language_kb,
)
from bot.services.apify import apify_downloader
from bot.services.client_pool import client_pool
from bot.services.following_access import (
    missing_channels,
    page_count,
    unlocked_pages,
)
from bot.services.subscription import has_direct_link_download_access
from bot.services.verification import get_connection
from bot.states import FollowingStates, SearchStates
from bot.utils import parse_username

router = Router()
logger = logging.getLogger(__name__)


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
    uid = message.from_user.id
    if await has_direct_link_download_access(uid, message.from_user.username):
        await message.answer(await tu(uid, "help_direct"))
        return
    from bot.handlers.payments import send_subscription_shop

    await message.answer(await tu(uid, "help_direct"))
    await send_subscription_shop(
        message.bot, message.chat.id, uid, message.from_user.username
    )


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


@router.message(Command("following"))
async def cmd_following(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    if not await guard_channels(message, uid):
        return
    await state.set_state(FollowingStates.waiting_username)
    await message.answer(
        await tu(uid, "following_ask_username"),
        reply_markup=await following_cancel_kb(uid),
    )


@router.callback_query(F.data == "following:cancel")
async def cancel_following(callback: CallbackQuery, state: FSMContext) -> None:
    uid = callback.from_user.id
    await state.clear()
    await callback.message.edit_text(await tu(uid, "following_cancelled"))
    await callback.answer()


@router.callback_query(F.data == "following:recheck")
async def recheck_following_join(callback: CallbackQuery, state: FSMContext) -> None:
    uid = callback.from_user.id
    try:
        missing = await missing_channels(callback.bot, uid)
        if missing:
            lang = await require_user_lang(uid)
            from bot.keyboards import following_join_kb

            await callback.message.edit_text(
                await tu(
                    uid,
                    "following_still_missing",
                    channels="\n".join(f"• {c}" for c in missing),
                ),
                reply_markup=following_join_kb(missing, lang),
            )
            await callback.answer()
            return
        await state.set_state(FollowingStates.waiting_username)
        await callback.message.edit_text(await tu(uid, "following_ask_username"))
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
    await callback.answer()


@router.message(StateFilter(FollowingStates.waiting_username))
async def receive_following_username(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    text = (message.text or "").strip()
    username = parse_username(text) or text.lstrip("@").lower()

    if not username or " " in username or len(username) > 30:
        await message.answer(await tu(uid, "following_invalid_username"))
        return

    if not await guard_channels(message, uid):
        await state.clear()
        return

    await state.clear()

    if not apify_downloader.ready and not client_pool.service_ready:
        await message.answer(await tu(uid, "error_service_ig"))
        return

    status = await message.answer(await tu(uid, "processing"))
    try:
        await start_following_lookup(message, state, username)
    except ValueError as exc:
        await status.edit_text(friendly_error(exc, lang))
        return
    except Exception:
        logger.exception("Following fetch error")
        await status.edit_text(await tu(uid, "error_generic"))
        return

    await status.delete()


@router.callback_query(F.data.startswith("following:page:"))
async def view_following_page(callback: CallbackQuery, state: FSMContext) -> None:
    uid = callback.from_user.id
    lang = await require_user_lang(uid)
    await callback.answer()

    try:
        page_number = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        return

    data = await state.get_data()
    username = data.get("following_username")
    pages = data.get("following_pages")
    if not username or pages is None:
        await callback.message.answer(await tu(uid, "following_session_expired"))
        return

    if not await guard_channels(callback.message, uid):
        return

    from bot.services.following_access import is_page_unlocked

    if await is_page_unlocked(uid, username, page_number):
        idx = page_number - 1
        page_users = pages[idx] if 0 <= idx < len(pages) else []
        await send_following_page(callback.message, username, page_number, page_count(), page_users)
        return

    import urllib.parse

    support = settings.payment_support_username.lstrip("@")
    prefill = (
        f"سلام، درخواست دسترسی فالووینگ\n"
        f"یوزرنیم هدف: @{username}\n"
        f"صفحه: {page_number}\n"
        f"مبلغ: {settings.following_page_price_toman:,} تومان\n"
        f"شناسه: {uid}"
    )
    support_url = f"https://t.me/{support}?text={urllib.parse.quote(prefill)}"
    await callback.message.answer(
        await tu(
            uid,
            "following_pay_prompt",
            page=page_number,
            username=username,
            price=f"{settings.following_page_price_toman:,}",
        ),
        reply_markup=following_pay_kb(page_number, support_url, lang),
    )


@router.callback_query(F.data == "following:back")
async def back_to_following_pages(callback: CallbackQuery, state: FSMContext) -> None:
    uid = callback.from_user.id
    lang = await require_user_lang(uid)
    await callback.answer()

    data = await state.get_data()
    username = data.get("following_username")
    if not username:
        await callback.message.answer(await tu(uid, "following_session_expired"))
        return

    unlocked = await unlocked_pages(uid, username)
    await callback.message.answer(
        await tu(uid, "following_pages_menu", username=username),
        reply_markup=following_pages_kb(unlocked, lang),
    )


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
    text, kb = await build_settings_message(uid, message.from_user.username)
    await message.answer(text, reply_markup=kb)



@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "privacy"))


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer(
        await build_status_text(message.from_user.id, message.from_user.username)
    )

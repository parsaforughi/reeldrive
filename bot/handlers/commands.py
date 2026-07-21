import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import settings
from bot.handlers.admin import send_receipt_to_admins
from bot.handlers.following_shared import guard_channels, start_following_lookup
from bot.handlers.status_helpers import (
    build_feed_text,
    build_myinstagram_text,
    build_settings_message,
    build_status_text,
)
from bot.i18n import friendly_error, get_user_lang, require_user_lang, t, tu
from bot.keyboards import following_cancel_kb, following_token_pay_kb, language_kb
from bot.services.following import following_ready
from bot.services.following_access import (
    current_support_card,
    missing_channels,
    to_rial,
    token_price,
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

    if not following_ready():
        await message.answer(await tu(uid, "error_apify"))
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


@router.callback_query(F.data.startswith("following:copy:"))
async def copy_payment_value(callback: CallbackQuery) -> None:
    try:
        _, _, kind, value = callback.data.split(":")
    except ValueError:
        await callback.answer()
        return
    if kind == "amount":
        try:
            value = f"{int(value):,}"
        except ValueError:
            pass
    await callback.answer(text=value, show_alert=True)


@router.message(StateFilter(FollowingStates.waiting_token_count))
async def receive_token_count(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    text = (message.text or "").strip()

    if not text.isdigit() or not (1 <= int(text) <= 50):
        await message.answer(await tu(uid, "following_invalid_token_count"))
        return

    count = int(text)
    amount = token_price(count, uid)
    amount_rial = to_rial(amount)
    card = await current_support_card()

    await state.set_state(FollowingStates.waiting_receipt_photo)
    await state.update_data(following_token_count=count, following_token_amount=amount, following_token_card=card)

    import urllib.parse

    support = settings.payment_support_username.lstrip("@")
    prefill = (
        f"سلام، درخواست توکن فالووینگ\n"
        f"تعداد: {count}\n"
        f"مبلغ واریزی: {amount_rial:,} ریال\n"
        f"شناسه: {uid}"
    )
    support_url = f"https://t.me/{support}?text={urllib.parse.quote(prefill)}"

    await message.answer(
        await tu(
            uid,
            "following_token_pay_prompt",
            count=count,
            amount=f"{amount_rial:,}",
            card=card,
            holder=settings.following_card_holder_name,
        ),
        reply_markup=following_token_pay_kb(support_url, lang, card=card, amount_rial=amount_rial),
    )


@router.message(StateFilter(FollowingStates.waiting_receipt_photo), F.photo)
async def receive_token_receipt(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    data = await state.get_data()
    count = data.get("following_token_count")
    amount = data.get("following_token_amount")
    card = data.get("following_token_card")
    await state.clear()

    if not count:
        await message.answer(await tu(uid, "following_session_expired"))
        return

    photo_id = message.photo[-1].file_id
    await send_receipt_to_admins(
        message.bot, uid, message.from_user.username, count, amount, card, photo_id
    )
    await message.answer(await tu(uid, "following_receipt_received"))


@router.message(StateFilter(FollowingStates.waiting_receipt_photo))
async def receive_token_receipt_invalid(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "following_receipt_need_photo"))


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

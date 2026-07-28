import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import settings
from bot.handlers.admin import (
    send_receipt_to_admins,
    send_unfollowers_receipt_to_admins,
)
from bot.handlers.connect import send_connection_code
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
    following_token_pay_kb,
    language_kb,
    unfollowers_connect_kb,
)
from bot.services.following import following_ready
from bot.services.following_access import (
    current_card_holder_name,
    current_support_card,
    missing_channels,
    to_rial,
    token_price,
)
from bot.services.subscription import has_direct_link_download_access
from bot.services.verification import get_connection
from bot.states import FollowingStates, SearchStates, UnfollowersStates
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
async def cmd_unfollowers(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    if not await guard_channels(message, uid):
        return
    if not following_ready():
        await message.answer(await tu(uid, "error_hikerapi"))
        return

    conn = await get_connection(uid)
    if conn and conn.status == "connected":
        await _run_unfollowers_report(
            message, state, conn.instagram_username.lstrip("@").lower()
        )
        return

    if conn and conn.status == "pending" and conn.verification_code:
        await message.answer(
            await tu(
                uid,
                "unfollowers_connection_pending",
                username=conn.instagram_username,
                code=conn.verification_code,
            )
        )
        return

    await state.clear()
    lang = await require_user_lang(uid)
    await message.answer(
        await tu(uid, "unfollowers_connect_intro"),
        reply_markup=unfollowers_connect_kb(lang),
    )


async def _unfollowers_price(username: str) -> tuple[int, int, bool, str, int, int]:
    from bot.services.following_access import tokens_required_for_count
    from bot.services.unfollowers import precheck_counts, token_cost_units

    following_count, follower_count, is_private, user_id = await precheck_counts(
        username
    )
    cost_units = token_cost_units(following_count, follower_count)
    tokens_needed = tokens_required_for_count(cost_units)
    return (
        following_count,
        follower_count,
        is_private,
        user_id,
        cost_units,
        tokens_needed,
    )


async def _start_unfollowers_payment(
    message: Message,
    state: FSMContext,
    *,
    username: str,
    following_count: int,
    cost_units: int,
    tokens_needed: int,
) -> None:
    import urllib.parse

    from bot.services.following_access import get_credit_balance

    uid = message.from_user.id
    balance = await get_credit_balance(uid)
    purchase_count = max(1, tokens_needed - balance)
    amount = token_price(purchase_count, uid)
    amount_rial = to_rial(amount)
    card = await current_support_card()
    holder = await current_card_holder_name()

    await state.set_state(UnfollowersStates.waiting_receipt_photo)
    await state.update_data(
        unfollowers_username=username,
        unfollowers_purchase_count=purchase_count,
        unfollowers_token_amount=amount,
        unfollowers_token_card=card,
    )

    support = settings.payment_support_username.lstrip("@")
    prefill = (
        "سلام، درخواست توکن آنفالویاب\n"
        f"پیج: @{username}\n"
        f"تعداد: {purchase_count}\n"
        f"مبلغ واریزی: {amount_rial:,} ریال\n"
        f"شناسه: {uid}"
    )
    support_url = f"https://t.me/{support}?text={urllib.parse.quote(prefill)}"
    lang = await require_user_lang(uid)
    await message.answer(
        await tu(
            uid,
            "unfollowers_token_pay_prompt",
            username=username,
            following=following_count,
            doubled=cost_units,
            total_tokens=tokens_needed,
            count=purchase_count,
            balance=balance,
            amount=f"{amount_rial:,}",
            card=card,
            holder=holder,
        ),
        reply_markup=following_token_pay_kb(
            support_url,
            lang,
            card=card,
            amount_rial=amount_rial,
        ),
    )


async def _run_unfollowers_report(
    message: Message, state: FSMContext, handle: str
) -> None:
    from bot.handlers.download_helpers import send_unfollowers
    from bot.services.advanced_instagram import advanced_instagram
    from bot.services.following_access import (
        get_credit_balance,
        grant_paid_access,
        has_paid_access,
        is_unlocked,
    )
    from bot.services.unfollowers import (
        UnfollowerAccessRequired,
        build_report,
    )

    uid = message.from_user.id
    lang = await require_user_lang(uid)
    unlock_key = f"unfollowers:{handle}"
    try:
        (
            following_count,
            follower_count,
            is_private,
            user_id,
            cost_units,
            tokens_needed,
        ) = await _unfollowers_price(handle)
    except ValueError as exc:
        await message.answer(friendly_error(exc, lang))
        return

    if not await is_unlocked(uid, unlock_key) and not await has_paid_access(
        uid, unlock_key, tokens_needed
    ):
        await _start_unfollowers_payment(
            message,
            state,
            username=handle,
            following_count=following_count,
            cost_units=cost_units,
            tokens_needed=tokens_needed,
        )
        return

    # Only after token access is ready do we ask for the sensitive private
    # session. No token is consumed until the report itself succeeds below.
    if is_private and not await advanced_instagram.has_session(uid):
        await message.answer(await tu(uid, "unfollowers_private_needs_advanced"))
        return

    status = await message.answer(await tu(uid, "unfollowers_loading"))
    try:
        report = await build_report(
            uid,
            handle,
            following_count=following_count,
            follower_count=follower_count,
            is_private=is_private,
            user_id=user_id,
        )
    except UnfollowerAccessRequired:
        await status.edit_text(await tu(uid, "unfollowers_private_needs_advanced"))
        return
    except ValueError as exc:
        await status.edit_text(friendly_error(exc, lang))
        return
    except Exception:
        logger.exception("Unfollower analysis failed for uid=%s", uid)
        await status.edit_text(await tu(uid, "error_generic"))
        return

    # Spend tokens only after a successful fetch, so a failed/private lookup
    # never costs the user anything (mirrors the /following flow).
    await grant_paid_access(uid, unlock_key, tokens_needed)
    try:
        await status.delete()
    except TelegramBadRequest:
        pass
    await send_unfollowers(message, report)
    tokens_left = await get_credit_balance(uid)
    await message.answer(await tu(uid, "following_tokens_status", tokens=tokens_left))


@router.callback_query(F.data == "unfollowers:connect")
async def start_unfollowers_connect(
    callback: CallbackQuery, state: FSMContext
) -> None:
    uid = callback.from_user.id
    await state.set_state(UnfollowersStates.waiting_username)
    await callback.message.edit_text(await tu(uid, "unfollowers_ask_username"))
    await callback.answer()


@router.message(
    StateFilter(UnfollowersStates.waiting_username), ~F.text.startswith("/")
)
async def receive_unfollowers_username(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    username = parse_username((message.text or "").strip())
    if not username:
        await message.answer(await tu(uid, "connect_invalid_username"))
        return

    try:
        following_count, _, _, _, cost_units, tokens_needed = (
            await _unfollowers_price(username)
        )
    except ValueError as exc:
        await message.answer(friendly_error(exc, lang))
        return

    from bot.services.following_access import has_paid_access

    unlock_key = f"unfollowers:{username}"
    if await has_paid_access(uid, unlock_key, tokens_needed):
        await state.clear()
        await send_connection_code(message.bot, message.chat.id, uid, username)
        return

    await _start_unfollowers_payment(
        message,
        state,
        username=username,
        following_count=following_count,
        cost_units=cost_units,
        tokens_needed=tokens_needed,
    )


@router.message(StateFilter(UnfollowersStates.waiting_receipt_photo), F.photo)
async def receive_unfollowers_receipt(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    data = await state.get_data()
    username = data.get("unfollowers_username")
    count = data.get("unfollowers_purchase_count")
    amount = data.get("unfollowers_token_amount")
    card = data.get("unfollowers_token_card")
    await state.clear()

    if not username or not count or not amount:
        await message.answer(await tu(uid, "following_session_expired"))
        return

    await send_unfollowers_receipt_to_admins(
        message.bot,
        uid,
        message.from_user.username,
        username,
        count,
        amount,
        card,
        message.photo[-1].file_id,
    )
    await message.answer(await tu(uid, "unfollowers_receipt_received"))


@router.message(StateFilter(UnfollowersStates.waiting_receipt_photo))
async def receive_unfollowers_receipt_invalid(message: Message) -> None:
    await message.answer(await tu(message.from_user.id, "following_receipt_need_photo"))


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


@router.message(StateFilter(FollowingStates.waiting_username), ~F.text.startswith("/"))
async def receive_following_username(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    text = (message.text or "").strip()
    username = parse_username(text)

    if not username:
        await message.answer(await tu(uid, "following_invalid_username"))
        return

    if not await guard_channels(message, uid):
        await state.clear()
        return

    await state.clear()

    if not following_ready():
        await message.answer(await tu(uid, "error_hikerapi"))
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
    holder = await current_card_holder_name()

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
            holder=holder,
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
async def cmd_help_unfollowers_legacy(message: Message, state: FSMContext) -> None:
    await cmd_unfollowers(message, state)


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

"""Shared following-list gating flow.

Used by both the /following command flow (bot/handlers/commands.py) and the
free-text quick-command entry point ("following <username>" typed directly
in chat, handled in bot/handlers/messages.py) so that both paths enforce the
same channel-membership + per-account-token gate — no shortcuts.
"""

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.download_helpers import send_following
from bot.i18n import require_user_lang, tu
from bot.keyboards import following_join_kb
from bot.services.following import fetch_following
from bot.services.following_access import (
    check_following_access,
    get_credit_balance,
    missing_channels,
)
from bot.states import FollowingStates


async def send_join_prompt(message: Message, uid: int, missing: list[str]) -> None:
    lang = await require_user_lang(uid)
    await message.answer(
        await tu(
            uid, "following_join_required", channels="\n".join(f"• {c}" for c in missing)
        ),
        reply_markup=following_join_kb(missing, lang),
    )


async def guard_channels(message: Message, uid: int) -> bool:
    """Returns True if the user may proceed, sending the join-prompt (and
    returning False) otherwise."""
    missing = await missing_channels(message.bot, uid)
    if missing:
        await send_join_prompt(message, uid, missing)
        return False
    return True


async def start_following_lookup(
    message: Message, state: FSMContext, username: str
) -> bool:
    """Fetches the following list and, if the user has access to this
    account (already unlocked, free quota, or a token to spend), shows it.
    Otherwise prompts them to buy tokens. Returns False if there was nothing
    to show (caller should already have sent an error/empty message in that
    case)."""
    uid = message.from_user.id
    users = await fetch_following(username)
    if not users:
        await message.answer(await tu(uid, "no_following"))
        return False

    if not await check_following_access(uid, username):
        await state.set_state(FollowingStates.waiting_token_count)
        await message.answer(await tu(uid, "following_need_tokens", username=username))
        return True

    await send_following(message, username, users)

    tokens_left = await get_credit_balance(uid)
    await message.answer(await tu(uid, "following_tokens_status", tokens=tokens_left))
    return True

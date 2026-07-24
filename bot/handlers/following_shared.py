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
from bot.services.following import fetch_following, fetch_following_count
from bot.services.following_access import (
    get_credit_balance,
    grant_access,
    has_access,
    is_unlocked,
    missing_channels,
    tokens_required_for_count,
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
    """Checks access (already unlocked, free quota, or enough tokens to
    spend) BEFORE fetching. Pricing is one token per started batch of 400
    followings, so for a never-unlocked account the follows count is looked
    up first via a cheap profile-details call — BEFORE the expensive
    followings-list scrape runs, so a user without enough tokens never
    triggers it. Only spends tokens after a successful, non-empty fetch, so
    a private/empty account doesn't cost anything either. Returns False if
    there was nothing to show (caller should already have sent an
    error/empty message in that case)."""
    uid = message.from_user.id

    tokens_needed = 1
    if not await is_unlocked(uid, username):
        following_count = await fetch_following_count(username, uid)
        tokens_needed = tokens_required_for_count(following_count)
        if not await has_access(uid, username, tokens_needed):
            await state.set_state(FollowingStates.waiting_token_count)
            await message.answer(
                await tu(
                    uid,
                    "following_need_tokens",
                    username=username,
                    count=following_count,
                    tokens=tokens_needed,
                )
            )
            return True

    users = await fetch_following(username, telegram_id=uid)
    if not users:
        await message.answer(await tu(uid, "no_following"))
        return False

    await grant_access(uid, username, tokens_needed)
    await send_following(message, username, users)

    tokens_left = await get_credit_balance(uid)
    await message.answer(await tu(uid, "following_tokens_status", tokens=tokens_left))
    return True

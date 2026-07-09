"""Shared following-list gating flow.

Used by both the /following command flow (bot/handlers/commands.py) and the
free-text quick-command entry point ("following <username>" typed directly
in chat, handled in bot/handlers/messages.py) so that both paths enforce the
same channel-membership + per-page-payment gate — no shortcuts.
"""

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.i18n import require_user_lang, tu
from bot.keyboards import following_join_kb, following_pages_kb
from bot.services.following import fetch_following
from bot.services.following_access import (
    missing_channels,
    page_count,
    paginate,
    unlocked_pages,
)


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
    """Fetches the following list, paginates it, stores it in FSM state, and
    shows the page-selection menu. Returns False if there was nothing to show
    (caller should already have sent an error/empty message in that case)."""
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    users = await fetch_following(username)
    if not users:
        await message.answer(await tu(uid, "no_following"))
        return False

    pages = paginate(users)
    await state.update_data(following_username=username, following_pages=pages)
    unlocked = await unlocked_pages(uid, username)
    await message.answer(
        await tu(
            uid,
            "following_pages_intro",
            username=username,
            count=len(users),
            pages=page_count(),
            price=f"{settings.following_page_price_toman:,}",
        ),
        reply_markup=following_pages_kb(unlocked, lang),
    )
    return True

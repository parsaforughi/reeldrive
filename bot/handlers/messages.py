import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from instagrapi.exceptions import LoginRequired

from bot.config import settings
from bot.handlers.download_helpers import (
    cleanup,
    run_sync,
    send_media_result,
    send_profile,
    send_stories,
    send_zip,
)
from bot.handlers.following_shared import guard_channels, start_following_lookup
from bot.i18n import friendly_error, require_user_lang, t, tu
from bot.keyboards import paywall_kb
from bot.services.subscription import has_direct_link_download_access
from bot.services.analytics import record_download
from bot.services.client_pool import client_pool
from bot.services.following import following_ready
from bot.time_utils import user_display_label
from bot.services.direct_download import direct_download_ready, download_media_url
from bot.services.instagram import instagram_downloader
from bot.services.verification import get_connection
from bot.states import ConnectStates, SearchStates
from bot.utils import ParsedCommand, parse_command, parse_media_url

router = Router()
logger = logging.getLogger(__name__)


def _paywall_text(lang: str) -> str:
    return t(
        "download_paywall",
        lang,
        free_total=settings.free_direct_downloads,
        pro_stars=settings.pro_stars_price,
    )


async def download_from_text(message: Message, text: str, state: FSMContext | None = None) -> None:
    """Direct download from a message (also used when user sends link during /connect)."""
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    parsed = parse_command(text.strip())
    if not parsed or parsed.kind != "media_url" or not parsed.url:
        await message.answer(await tu(uid, "hint_invalid_input"))
        return
    if not direct_download_ready():
        await message.answer(await tu(uid, "error_direct_not_ready"))
        return
    if not await has_direct_link_download_access(uid, message.from_user.username):
        await message.answer(
            _paywall_text(lang),
            reply_markup=paywall_kb(lang),
        )
        return
    status = await message.answer(await tu(uid, "processing"))
    try:
        await _dispatch(message, status, parsed, lang, state)
    except ValueError as exc:
        logger.warning("User request failed: %s", exc)
        await status.edit_text(friendly_error(exc, lang))
    except LoginRequired:
        await status.edit_text(await tu(uid, "error_login_required"))
    except Exception:
        logger.exception("Download error")
        await status.edit_text(await tu(uid, "error_generic"))


@router.message(F.text)
async def handle_text(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    current = await state.get_state()
    text = (message.text or "").strip()

    if current == ConnectStates.waiting_username.state:
        if not parse_media_url(text):
            return
        await state.clear()
    in_search = current == SearchStates.waiting_query.state

    parsed = parse_command(text)
    if not parsed:
        if in_search:
            await state.clear()
            await message.answer(await tu(uid, "search_invalid"))
        else:
            await message.answer(await tu(uid, "hint_invalid_input"))
        return

    if in_search:
        await state.clear()

    if parsed.kind == "following" and not following_ready():
        await message.answer(await tu(uid, "error_apify"))
        return

    needs_ig = parsed.kind != "media_url"
    if needs_ig and parsed.kind == "following" and following_ready():
        needs_ig = False
    if needs_ig and not client_pool.service_ready:
        await message.answer(await tu(uid, "error_service_ig"))
        return
    if parsed.kind == "media_url" and not direct_download_ready():
        await message.answer(await tu(uid, "error_direct_not_ready"))
        return
    if parsed.kind == "media_url" and not await has_direct_link_download_access(
        uid, message.from_user.username
    ):
        await message.answer(
            _paywall_text(lang),
            reply_markup=paywall_kb(lang),
        )
        return

    if parsed.kind == "following" and not await guard_channels(message, uid):
        return

    status = await message.answer(await tu(uid, "processing"))

    try:
        await _dispatch(message, status, parsed, lang, state)
    except ValueError as exc:
        logger.warning("User request failed: %s", exc)
        await status.edit_text(friendly_error(exc, lang))
    except LoginRequired:
        logger.warning("Instagram login required")
        await status.edit_text(await tu(uid, "error_login_required"))
    except Exception:
        logger.exception("Download error")
        await status.edit_text(await tu(uid, "error_generic"))


async def _dispatch(
    message: Message,
    status: Message,
    cmd: ParsedCommand,
    lang: str,
    state: FSMContext | None = None,
) -> None:
    uid = message.from_user.id
    if cmd.kind == "media_url" and cmd.url:
        logger.info(
            "Direct download telegram=%s url=%s",
            uid,
            cmd.url,
        )
        result = await download_media_url(cmd.url)
        await record_download(
            uid,
            cmd.url,
            user_label=user_display_label(message.from_user),
        )
        await status.delete()
        await send_media_result(message, result)
        return

    if cmd.kind == "hashtag" and cmd.hashtag:
        links = await run_sync(instagram_downloader.search_hashtag, cmd.hashtag, 15)
        await status.delete()
        if not links:
            await message.answer(await tu(uid, "no_posts"))
            return
        text = f"#{cmd.hashtag}\n\n" + "\n".join(links[:15])
        await message.answer(text)
        return

    if not cmd.username:
        await status.edit_text(await tu(uid, "error_invalid_username"))
        return

    user = cmd.username
    conn = await get_connection(uid)
    connected = conn and conn.status == "connected"

    if cmd.kind == "profile":
        await send_profile(message, user, status)
        return

    if cmd.kind == "stories":
        await status.delete()
        await send_stories(message, user)
        return

    if cmd.kind == "following":
        if state is None:
            await status.edit_text(await tu(uid, "error_generic"))
            return
        await start_following_lookup(message, state, user)
        await status.delete()
        return

    if cmd.kind == "highlights_list":
        highlights = await run_sync(instagram_downloader.list_highlights, user)
        await status.delete()
        if not highlights:
            await message.answer(await tu(uid, "no_highlights"))
            return
        lines = [f"📂 @{user}:\n"]
        for i, h in enumerate(highlights, 1):
            lines.append(f"{i}. {h.title} ({h.item_count})")
        lines.append(f"\n<code>highlight {user} 1</code>")
        await message.answer("\n".join(lines))
        return

    if cmd.kind == "highlight_one" and cmd.index:
        items = await run_sync(
            instagram_downloader.download_highlight_by_index, user, cmd.index
        )
        await status.delete()
        if not items:
            await message.answer(await tu(uid, "empty_highlight"))
            return
        for item in items:
            if item.is_video:
                await message.answer_video(
                    FSInputFile(item.path), caption=item.taken_at
                )
            else:
                await message.answer_photo(
                    FSInputFile(item.path), caption=item.taken_at
                )
            cleanup(item.path)
        return

    if cmd.kind == "zip_stories":
        zip_path = await run_sync(instagram_downloader.zip_stories, user)
        await status.delete()
        await send_zip(message, zip_path, f"Stories @{user}")
        return

    if cmd.kind == "zip_posts":
        zip_path = await run_sync(instagram_downloader.zip_posts, user)
        await status.delete()
        await send_zip(message, zip_path, f"Posts @{user}")
        return

    await send_profile(message, user, status)

    if connected:
        await message.answer(
            await tu(uid, "page_connected", username=conn.instagram_username)
        )

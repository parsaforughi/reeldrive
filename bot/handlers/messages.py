import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from instagrapi.exceptions import LoginRequired

from bot.handlers.download_helpers import (
    cleanup,
    run_sync,
    send_media_result,
    send_profile,
    send_stories,
    send_zip,
)
from bot.services.client_pool import client_pool
from bot.services.direct_download import direct_download_ready, download_media_url
from bot.services.instagram import instagram_downloader
from bot.services.verification import get_connection
from bot.states import ConnectStates, SearchStates
from bot.utils import ParsedCommand, parse_command

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text)
async def handle_text(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current == ConnectStates.waiting_username.state:
        return

    text = (message.text or "").strip()
    in_search = current == SearchStates.waiting_query.state

    parsed = parse_command(text)
    if not parsed:
        if in_search:
            await state.clear()
            await message.answer("❌ ورودی نامعتبر.\n/search را دوباره بزن.")
        else:
            await message.answer(
                "یوزرنیم، لینک، یا دستور معتبر بفرست.\n"
                "از دکمه Menu → /directdownload یا /search"
            )
        return

    if in_search:
        await state.clear()

    needs_ig = parsed.kind != "media_url"
    if needs_ig and not client_pool.service_ready:
        await message.answer(
            "⚠️ برای پروفایل/استوری/هایلایت اکانت IG سرویس لازم است.\n"
            "⚠️ Service IG required for profile/stories."
        )
        return
    if parsed.kind == "media_url" and not direct_download_ready():
        await message.answer(
            "⚠️ دایرکت دانلود آماده نیست.\n"
            "APIFY_TOKEN را در Railway بگذار.\n\n"
            "⚠️ Set APIFY_TOKEN for direct download."
        )
        return

    status = await message.answer("⏳ در حال پردازش…")

    try:
        await _dispatch(message, status, parsed)
    except ValueError as exc:
        await status.edit_text(f"❌ {exc}")
    except LoginRequired:
        await status.edit_text("❌ سشن اینستاگرام منقضی شد.")
    except Exception:
        logger.exception("Download error")
        await status.edit_text("❌ خطا. دوباره امتحان کن.")


async def _dispatch(message: Message, status: Message, cmd: ParsedCommand) -> None:
    if cmd.kind == "media_url" and cmd.url:
        result = await download_media_url(cmd.url)
        await status.delete()
        await send_media_result(message, result)
        return

    if cmd.kind == "hashtag" and cmd.hashtag:
        links = await run_sync(instagram_downloader.search_hashtag, cmd.hashtag, 15)
        await status.delete()
        if not links:
            await message.answer("پستی پیدا نشد.")
            return
        text = f"#{cmd.hashtag}\n\n" + "\n".join(links[:15])
        await message.answer(text)
        return

    if not cmd.username:
        await status.edit_text("❌ یوزرنیم نامعتبر")
        return

    user = cmd.username
    conn = await get_connection(message.from_user.id)
    connected = conn and conn.status == "connected"

    if cmd.kind == "profile":
        await send_profile(message, user, status)
        return

    if cmd.kind == "stories":
        await status.delete()
        await send_stories(message, user)
        return

    if cmd.kind == "highlights_list":
        highlights = await run_sync(instagram_downloader.list_highlights, user)
        await status.delete()
        if not highlights:
            await message.answer("هایلایتی نیست.")
            return
        lines = [f"📂 هایلایت‌های @{user}:\n"]
        for i, h in enumerate(highlights, 1):
            lines.append(f"{i}. {h.title} ({h.item_count} آیتم)")
        lines.append(f"\nدانلود: <code>highlight {user} 1</code>")
        await message.answer("\n".join(lines))
        return

    if cmd.kind == "highlight_one" and cmd.index:
        items = await run_sync(
            instagram_downloader.download_highlight_by_index, user, cmd.index
        )
        await status.delete()
        if not items:
            await message.answer("خالی بود.")
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

    # default profile
    await send_profile(message, user, status)

    if connected:
        await message.answer(
            f"✅ پیج متصل: @{conn.instagram_username}"
        )

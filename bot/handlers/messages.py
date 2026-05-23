import asyncio
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.types import FSInputFile, Message
from instagrapi.exceptions import LoginRequired

from bot.services.instagram import (
    ProfileResult,
    StoryItem,
    instagram_service,
)
from bot.utils import parse_media_url, parse_username

router = Router()
logger = logging.getLogger(__name__)


def format_profile(p: ProfileResult) -> str:
    private = "🔒" if p.is_private else "🌐"
    verified = " ✓" if p.is_verified else ""
    bio = f"\n\n{p.biography}" if p.biography else ""
    return (
        f"<b>@{p.username}</b>{verified} {private}\n"
        f"{p.full_name}\n\n"
        f"👥 {p.follower_count:,} followers\n"
        f"➡️ {p.following_count:,} following\n"
        f"📸 {p.media_count:,} posts"
        f"{bio}"
    )


async def _run_sync(func, *args):
    return await asyncio.to_thread(func, *args)


@router.message(F.text)
async def handle_text(message: Message) -> None:
    text = message.text or ""
    media_url = parse_media_url(text)
    username = parse_username(text)

    if not media_url and not username:
        await message.answer(
            "یوزرنیم یا لینک اینستاگرام بفرست.\n"
            "Send an Instagram username or link.\n\n"
            "/help"
        )
        return

    if not instagram_service.is_ready:
        await message.answer(
            "⚠️ ربات هنوز به اینستاگرام وصل نشده. بعداً دوباره امتحان کن.\n"
            "⚠️ Instagram not connected yet. Try again later."
        )
        return

    status = await message.answer("⏳ در حال پردازش… / Processing…")

    try:
        if media_url:
            await _handle_media(message, status, media_url)
        elif username:
            await _handle_profile(message, status, username)
    except ValueError as exc:
        await status.edit_text(f"❌ {exc}")
    except LoginRequired:
        await status.edit_text(
            "❌ اتصال اینستاگرام قطع شده.\n❌ Instagram session expired."
        )
    except Exception:
        logger.exception("Handler error")
        await status.edit_text(
            "❌ خطا رخ داد. دوباره امتحان کن.\n❌ Something went wrong."
        )


async def _handle_profile(message: Message, status: Message, username: str) -> None:
    profile: ProfileResult = await _run_sync(
        instagram_service.get_profile, username
    )
    await status.edit_text(format_profile(profile))

    if profile.profile_pic_path.exists():
        await message.answer_photo(
            FSInputFile(profile.profile_pic_path),
            caption=f"@{profile.username}",
        )

    if profile.is_private:
        await message.answer(
            "اکانت پرایوت — استوری در دسترس نیست.\n"
            "Private account — stories unavailable."
        )
        return

    stories: list[StoryItem] = await _run_sync(
        instagram_service.get_stories, username
    )
    if not stories:
        await message.answer("استوری فعالی نیست.\nNo active stories.")
        return

    await message.answer(
        f"📖 {len(stories)} استوری / {len(stories)} stories"
    )
    for item in stories:
        caption = item.taken_at or None
        if item.is_video:
            await message.answer_video(FSInputFile(item.path), caption=caption)
        else:
            await message.answer_photo(FSInputFile(item.path), caption=caption)
        _cleanup(item.path)

    _cleanup(profile.profile_pic_path)


async def _handle_media(message: Message, status: Message, url: str) -> None:
    result = await _run_sync(instagram_service.download_media_url, url)
    await status.delete()

    if result.caption:
        await message.answer(result.caption[:1024])

    for path in result.paths:
        if not path.exists():
            continue
        if path.suffix.lower() in {".mp4", ".mov"}:
            await message.answer_video(FSInputFile(path))
        else:
            await message.answer_photo(FSInputFile(path))
        _cleanup(path)


def _cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass

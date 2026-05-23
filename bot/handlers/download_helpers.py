import asyncio
from pathlib import Path

from aiogram.types import FSInputFile, Message

from bot.services.instagram import (
    MediaResult,
    ProfileResult,
    StoryItem,
    instagram_downloader,
)


async def run_sync(func, *args):
    return await asyncio.to_thread(func, *args)


def cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def format_profile(p: ProfileResult) -> str:
    private = "🔒" if p.is_private else "🌐"
    verified = " ✓" if p.is_verified else ""
    bio = f"\n\n{p.biography}" if p.biography else ""
    lines = (
        f"<b>@{p.username}</b>{verified} {private}\n"
        f"{p.full_name}\n\n"
        f"👥 {p.follower_count:,} followers\n"
        f"➡️ {p.following_count:,} following\n"
        f"📸 {p.media_count:,} posts"
        f"{bio}"
    )
    if p.direct_urls:
        lines += "\n\n🔗 " + p.direct_urls[0]
    return lines


async def send_profile(message: Message, username: str, status: Message) -> None:
    profile: ProfileResult = await run_sync(instagram_downloader.get_profile, username)
    await status.edit_text(format_profile(profile))
    if profile.profile_pic_path.exists():
        await message.answer_photo(
            FSInputFile(profile.profile_pic_path),
            caption=f"@{profile.username}",
        )
        cleanup(profile.profile_pic_path)
    if profile.is_private:
        await message.answer(
            "اکانت پرایوت — برای استوری/هایلایت پیج را /connect کن.\n"
            "Private — use /connect for more access."
        )
        return
    await send_stories(message, username)


async def send_stories(message: Message, username: str) -> None:
    stories: list[StoryItem] = await run_sync(
        instagram_downloader.get_stories, username
    )
    if not stories:
        await message.answer("استوری فعالی نیست.\nNo active stories.")
        return
    await message.answer(f"📖 {len(stories)} استوری")
    for item in stories:
        cap = item.taken_at or None
        if item.is_video:
            await message.answer_video(FSInputFile(item.path), caption=cap)
        else:
            await message.answer_photo(FSInputFile(item.path), caption=cap)
        cleanup(item.path)


async def send_media_result(message: Message, result: MediaResult) -> None:
    if result.caption:
        await message.answer(result.caption[:1024])
    for path in result.paths:
        if not path.exists():
            continue
        if path.suffix.lower() in {".mp4", ".mov"}:
            await message.answer_video(FSInputFile(path))
        else:
            await message.answer_photo(FSInputFile(path))
        cleanup(path)
    if result.direct_urls:
        await message.answer(
            "🔗 لینک مستقیم:\n" + "\n".join(result.direct_urls[:5])
        )


async def send_zip(message: Message, zip_path: Path, caption: str) -> None:
    await message.answer_document(FSInputFile(zip_path), caption=caption)
    cleanup(zip_path)

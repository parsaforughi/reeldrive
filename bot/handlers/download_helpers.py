from html import escape
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message

from bot.i18n import tu
from bot.keyboards import post_actions_kb
from bot.post_display import PostMeta, format_post_caption
from bot.services.instagram import (
    FollowUser,
    MediaResult,
    ProfileResult,
    StoryItem,
    instagram_downloader,
)
from bot.services.profile import fetch_profile

_CHUNK_LIMIT = 3500


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
    profile: ProfileResult = await fetch_profile(username)
    await status.edit_text(format_profile(profile))
    if profile.profile_pic_path.exists():
        await message.answer_photo(
            FSInputFile(profile.profile_pic_path),
            caption=f"@{profile.username}",
        )
        cleanup(profile.profile_pic_path)


async def send_stories(message: Message, username: str) -> None:
    uid = message.from_user.id
    stories: list[StoryItem] = await instagram_downloader.get_stories(
        username, uid
    )
    if not stories:
        await message.answer(await tu(uid, "no_stories"))
        return
    await message.answer(
        await tu(uid, "stories_count", count=len(stories))
    )
    for item in stories:
        cap = item.taken_at or None
        if item.is_video:
            await message.answer_video(FSInputFile(item.path), caption=cap)
        else:
            await message.answer_photo(FSInputFile(item.path), caption=cap)
        cleanup(item.path)


def _chunk_lines(lines: list[str], limit: int = _CHUNK_LIMIT) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in lines:
        line_len = len(line) + 1
        if current and size + line_len > limit:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def _following_lines(users: list[FollowUser]) -> list[str]:
    lines = []
    for u in users:
        badge = " ✓" if u.is_verified else ""
        lock = " 🔒" if u.is_private else ""
        name = f" — {escape(u.full_name)}" if u.full_name else ""
        username = escape(u.username)
        link = f'<a href="https://instagram.com/{username}">{username}</a>'
        lines.append(f"• {link}{badge}{lock}{name}")
    return lines


async def send_following(message: Message, username: str, users: list[FollowUser]) -> None:
    uid = message.from_user.id
    header = await tu(
        uid, "following_count", count=len(users), username=escape(username)
    )
    await message.answer(header)
    for chunk in _chunk_lines(_following_lines(users)):
        await message.answer(chunk)


async def _send_media_with_markup(
    bot: Bot,
    chat_id: int,
    path: Path,
    *,
    is_video: bool,
    caption: str | None,
    keyboard: InlineKeyboardMarkup | None,
) -> None:
    kwargs = {"caption": caption, "reply_markup": keyboard}
    if is_video:
        await bot.send_video(chat_id, FSInputFile(path), **kwargs)
    else:
        await bot.send_photo(chat_id, FSInputFile(path), **kwargs)


async def deliver_media_result(
    bot: Bot, chat_id: int, result: MediaResult
) -> None:
    meta: PostMeta | None = (
        result.post_meta if isinstance(result.post_meta, PostMeta) else None
    )
    caption_html = (
        format_post_caption(meta) if meta else (result.caption or "")[:1024]
    )
    keyboard = None
    if meta and meta.post_url:
        keyboard = post_actions_kb(meta.post_url, meta.short_code)

    paths = [p for p in result.paths if p.exists()]
    if not paths:
        await bot.send_message(chat_id, "❌ فایل یافت نشد.")
        return

    first = paths[0]
    is_video = first.suffix.lower() in {".mp4", ".mov"}

    await _send_media_with_markup(
        bot,
        chat_id,
        first,
        is_video=is_video,
        caption=caption_html or None,
        keyboard=keyboard,
    )
    cleanup(first)

    for extra in paths[1:]:
        if not extra.exists():
            continue
        if extra.suffix.lower() in {".mp4", ".mov"}:
            await bot.send_video(chat_id, FSInputFile(extra))
        else:
            await bot.send_photo(chat_id, FSInputFile(extra))
        cleanup(extra)


async def send_media_result(message: Message, result: MediaResult) -> None:
    await deliver_media_result(message.bot, message.chat.id, result)


async def send_zip(message: Message, zip_path: Path, caption: str) -> None:
    await message.answer_document(FSInputFile(zip_path), caption=caption)
    cleanup(zip_path)

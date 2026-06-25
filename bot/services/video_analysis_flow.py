"""Orchestrate video download + full analysis pipeline."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp
from aiogram import Bot
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.media_variants import pick_best_download
from bot.services.cdn_download import IG_CDN_HEADERS
from bot.services.post_analysis import check_ai_access
from bot.services.post_cache import CachedPost
from bot.services.subscription import is_ai_unlimited
from bot.services.video_analyzer import TMP, ffmpeg_ready, run_full_analysis
from bot.services.video_frames import _video_variant

logger = logging.getLogger(__name__)

StatusFn = Callable[[str], Awaitable[None]]

_active: set[str] = set()


def _lock_key(chat_id: int, message_id: int) -> str:
    return f"{chat_id}:{message_id}"


def is_analysis_running(chat_id: int, message_id: int) -> bool:
    return _lock_key(chat_id, message_id) in _active


def _acquire(chat_id: int, message_id: int) -> bool:
    key = _lock_key(chat_id, message_id)
    if key in _active:
        return False
    _active.add(key)
    return True


def _release(chat_id: int, message_id: int) -> None:
    _active.discard(_lock_key(chat_id, message_id))


def _video_from_message(message: Message) -> Any | None:
    if message.video:
        return message.video
    doc = message.document
    if doc and doc.mime_type and "video" in doc.mime_type:
        return doc
    return None


async def _download_telegram_video(
    bot: Bot,
    file_id: str,
    dest: Path,
) -> bool:
    try:
        file = await bot.get_file(file_id)
        if file.file_size and file.file_size > 20 * 1024 * 1024:
            return False
        TMP.mkdir(parents=True, exist_ok=True)
        await bot.download_file(file.file_path, dest)
        return dest.is_file() and dest.stat().st_size > 0
    except Exception:
        logger.exception("Telegram video download failed")
        return False


async def _download_cached_video(cached: CachedPost, dest: Path) -> bool:
    var = _video_variant(cached.variants)
    if not var:
        return False
    max_bytes = min(20 * 1024 * 1024, settings.ai_video_max_mb * 1024 * 1024)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(var.url, headers=IG_CDN_HEADERS) as resp:
                if not (200 <= resp.status < 300):
                    return False
                data = await resp.read()
                if not data or len(data) > max_bytes:
                    return False
                TMP.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return True
    except Exception:
        logger.exception("CDN video download for analysis failed")
        return False


async def resolve_video_path(
    *,
    bot: Bot,
    message: Message | None = None,
    cached: CachedPost | None = None,
    file_id: str | None = None,
) -> Path | None:
    """Download video to temp path; caller must delete."""
    TMP.mkdir(parents=True, exist_ok=True)

    if file_id:
        dest = TMP / f"tg_{file_id}.mp4"
        if await _download_telegram_video(bot, file_id, dest):
            return dest
        return None

    if message:
        video = _video_from_message(message)
        if video:
            dest = TMP / f"tg_{video.file_id}.mp4"
            if await _download_telegram_video(bot, video.file_id, dest):
                return dest

    if cached:
        var = _video_variant(cached.variants) or (
            pick_best_download(cached.variants) if cached.variants else None
        )
        if var:
            dest = TMP / f"cdn_{abs(hash(var.url)) % 10_000_000}.mp4"
            if await _download_cached_video(cached, dest):
                return dest

    return None


async def analyze_video_pipeline(
    filepath: Path,
    *,
    on_status: StatusFn | None = None,
) -> str:
    return await run_full_analysis(str(filepath), on_status=on_status)


async def run_video_analysis(
    *,
    bot: Bot,
    telegram_id: int,
    username: str | None,
    chat_id: int,
    message_id: int,
    on_status: StatusFn,
    message: Message | None = None,
    cached: CachedPost | None = None,
    file_id: str | None = None,
    source_detail: str = "",
) -> str:
    """Access check, download, analyze, log usage."""
    from bot.services.analytics import log_activity

    ok, reason = await check_ai_access(telegram_id, username)
    if not ok:
        raise ValueError(reason)

    if not _acquire(chat_id, message_id):
        raise ValueError("ai_already_running")

    filepath: Path | None = None
    try:
        await on_status("download")
        filepath = await resolve_video_path(
            bot=bot,
            message=message,
            cached=cached,
            file_id=file_id,
        )
        if not filepath:
            raise ValueError("ai_no_video")

        report = await analyze_video_pipeline(filepath, on_status=on_status)

        await log_activity(
            telegram_id,
            "ai_analysis",
            detail=(source_detail or str(filepath.name))[:200],
            meta={
                "pipeline": "full_video",
                "ffmpeg": ffmpeg_ready(),
                "vip": await is_ai_unlimited(telegram_id, username),
            },
        )
        return report
    finally:
        _release(chat_id, message_id)
        if filepath:
            try:
                filepath.unlink(missing_ok=True)
            except OSError:
                pass

"""Shared AI analysis callback logic for post button and uploaded videos."""

from __future__ import annotations

import logging

from aiogram.types import CallbackQuery

from bot.config import settings
from bot.i18n import friendly_error, require_user_lang, t, tu
from bot.services.analysis_progress import AnalysisProgress, progress_bar
from bot.services.post_cache import CachedPost
from bot.services.video_analysis_flow import run_video_analysis
from bot.services.video_frames import _is_video_item, ffmpeg_ready

logger = logging.getLogger(__name__)

_STATUS_KEYS = {
    "download": "ai_status_download",
    "technical": "ai_status_technical",
    "audio": "ai_status_audio",
    "frames": "ai_status_frames",
    "visual": "ai_status_visual",
}

_AI_ERROR_KEYS = frozenset(
    {
        "ai_not_configured",
        "ai_pro_required",
        "ai_limit_reached",
        "ai_video_too_large",
        "ai_no_video",
        "ai_already_running",
        "ai_deps_missing",
        "ai_auth_failed",
        "ai_api_error",
        "ai_rate_limit",
    }
)


async def _progress_text(uid: int, stage: str, progress: AnalysisProgress) -> str:
    pct = progress.pct_at_stage(stage)
    eta = progress.eta_seconds(pct)
    stage_label = await tu(uid, _STATUS_KEYS.get(stage, "ai_status_download"))
    bar = progress_bar(pct)
    eta_line = t("ai_progress_eta", await require_user_lang(uid), eta=eta)
    return f"{stage_label}\n\n{bar} {pct}%\n{eta_line}"


async def run_ai_analysis_callback(
    callback: CallbackQuery,
    *,
    cached: CachedPost | None = None,
    file_id: str | None = None,
) -> None:
    uid = callback.from_user.id
    lang = await require_user_lang(uid)
    msg = callback.message
    if not msg:
        return

    await callback.answer(await tu(uid, "ai_analyzing"))
    progress = AnalysisProgress()
    status_msg = await msg.reply(
        await _progress_text(uid, "download", progress)
    )

    async def on_status(stage: str) -> None:
        try:
            await status_msg.edit_text(await _progress_text(uid, stage, progress))
        except Exception:
            pass

    try:
        is_video = bool(file_id)
        if cached:
            is_video = _is_video_item(cached.source_item, cached.variants)
        elif msg.video or (
            msg.document and msg.document.mime_type and "video" in msg.document.mime_type
        ):
            is_video = True

        use_pipeline = is_video and settings.ai_video_frames_enabled and ffmpeg_ready()

        if use_pipeline:
            report = await run_video_analysis(
                bot=callback.bot,
                telegram_id=uid,
                username=callback.from_user.username,
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                on_status=on_status,
                message=msg,
                cached=cached,
                file_id=file_id,
                source_detail=cached.source_url if cached else "upload",
            )
            await status_msg.edit_text(report)
            return

        from bot.services.post_analysis import analyze_cached_post

        if not cached:
            await status_msg.edit_text(await tu(uid, "ai_no_video"))
            return

        report = await analyze_cached_post(
            cached,
            telegram_id=uid,
            lang=lang,
            username=callback.from_user.username,
        )
        header = await tu(uid, "ai_report_header")
        await status_msg.edit_text(f"{header}\n\n{report}")
    except ValueError as exc:
        key = str(exc)
        if key in _AI_ERROR_KEYS:
            await status_msg.edit_text(await tu(uid, key))
        else:
            await status_msg.edit_text(friendly_error(exc, lang))
    except Exception:
        logger.exception("AI analysis failed")
        await status_msg.edit_text(await tu(uid, "ai_failed"))

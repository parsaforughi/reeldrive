"""Handle user-uploaded videos — add analyze button without auto-analysis."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.handlers.ai_analysis import run_ai_analysis_callback
from bot.i18n import tu
from bot.keyboards import video_analyze_kb

router = Router()
logger = logging.getLogger(__name__)


def _video_file_id(message: Message) -> str | None:
    if message.video:
        return message.video.file_id
    doc = message.document
    if doc and doc.mime_type and "video" in doc.mime_type:
        return doc.file_id
    return None


@router.message(F.video)
@router.message(F.document)
async def handle_uploaded_video(message: Message) -> None:
    """Add analyze button; do not start analysis automatically."""
    file_id = _video_file_id(message)
    if not file_id:
        return
    uid = message.from_user.id
    await message.reply(
        await tu(uid, "video_upload_hint"),
        reply_markup=video_analyze_kb(file_id),
    )


@router.callback_query(F.data.startswith("analyze:file:"))
async def analyze_uploaded_video(callback: CallbackQuery) -> None:
    data = callback.data or ""
    file_id = data.split(":", 2)[-1]
    if not file_id:
        await callback.answer(await tu(callback.from_user.id, "invalid"))
        return
    await run_ai_analysis_callback(callback, file_id=file_id)

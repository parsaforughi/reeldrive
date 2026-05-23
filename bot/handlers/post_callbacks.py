from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.post_display import PostMeta, format_post_caption
from bot.services.direct_download import download_media_url
from bot.services.post_cache import get_post
from bot.handlers.download_helpers import send_media_result

router = Router()


def _code_from_callback(data: str) -> str | None:
    parts = data.split(":", 2)
    if len(parts) == 3:
        return parts[2]
    return None


@router.callback_query(F.data.startswith("post:"))
async def post_action(callback: CallbackQuery) -> None:
    data = callback.data or ""
    code = _code_from_callback(data)
    if not code:
        await callback.answer("نامعتبر")
        return

    cached = get_post(code)
    action = data.split(":")[1] if ":" in data else ""

    if action == "ai":
        await callback.answer("به‌زودی — تحلیل هوش مصنوعی", show_alert=True)
        return
    if action == "subs":
        await callback.answer("به‌زودی — زیرنویس ویدیو", show_alert=True)
        return
    if action == "audio":
        await callback.answer("به‌زودی — دانلود صدا", show_alert=True)
        return

    if not cached:
        await callback.answer("اطلاعات پست منقضی شده — لینک را دوباره بفرست", show_alert=True)
        return

    if action == "caption":
        meta = PostMeta(
            short_code=code,
            post_url=cached.source_url,
            caption=str(cached.apify_item.get("caption") or ""),
            hashtags=cached.apify_item.get("hashtags") or [],
        )
        await callback.message.answer(format_post_caption(meta))
        await callback.answer()
        return

    if action == "links" or action == "qualities":
        urls = cached.direct_urls or []
        if not urls:
            await callback.answer("لینکی ذخیره نشده", show_alert=True)
            return
        title = (
            "💽 همه کیفیت‌ها:\n" if action == "qualities" else "🌐 لینک‌های دانلود:\n"
        )
        await callback.message.answer(title + "\n".join(urls[:10]))
        await callback.answer()
        return

    if action == "refresh":
        await callback.answer("⏳ در حال بروزرسانی…")
        try:
            result = await download_media_url(cached.source_url)
            await send_media_result(callback.message, result)
        except ValueError as exc:
            await callback.message.answer(f"❌ {exc}")
        return

    await callback.answer()

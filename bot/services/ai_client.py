"""OpenAI-compatible chat + vision API (GapGPT, OpenAI, etc.)."""

import logging
from typing import Any

import aiohttp

from bot.config import settings
from bot.services.analysis_progress import ai_error_key

logger = logging.getLogger(__name__)

_LANG_NAMES = {"fa": "Persian (Farsi)", "en": "English", "ar": "Arabic"}

VisionFrame = tuple[str, str, str]  # label, b64, mime


class AIClient:
    @property
    def ready(self) -> bool:
        return bool(settings.openai_api_key.strip())

    async def analyze_post(
        self,
        *,
        metrics_text: str,
        lang: str,
        frames: list[VisionFrame] | None = None,
        image_b64: str | None = None,
        image_mime: str = "image/jpeg",
        is_video: bool = False,
    ) -> str:
        if not self.ready:
            raise ValueError("AI not configured")

        lang_name = _LANG_NAMES.get(lang, "Persian (Farsi)")
        system = (
            "You are an expert short-form video editor and Instagram Reels strategist. "
            f"Write the full analysis in {lang_name}. "
            "Use Telegram HTML only: <b> for section titles, no markdown. "
            "Be concrete and actionable. Keep total length under 3500 characters."
        )

        if frames:
            visual_note = (
                "You receive MULTIPLE frames from the SAME reel at different timestamps. "
                "Compare frames to infer cuts, pacing, hook structure, and visual storytelling. "
                "Do NOT guess from caption — base hook/cut/editing analysis ONLY on what you see in frames."
            )
        elif image_b64:
            visual_note = "You receive one preview image. Analyze what is visible; do not invent unseen cuts."
        else:
            visual_note = "No visual provided — keep visual section brief and note limitation."

        if is_video and frames:
            sections = (
                "Include these sections with <b> titles:\n"
                "1) <b>هوک اول ۳ ثانیه</b> — What happens in opening frames? Pattern interrupt? Face/text/hook?\n"
                "2) <b>ساختار و کات</b> — Scene changes, jump cuts, B-roll vs talking head, rhythm between frames\n"
                "3) <b>تحلیل بصری</b> — Composition, lighting, on-screen text, vibe, retention tricks\n"
                "4) <b>کپشن (فقط مکمل)</b> — One short paragraph; do NOT repeat visual analysis from caption\n"
                "5) <b>مقایسه با میانگین پیج</b> — Use stats only\n"
                "6) <b>پیشنهاد ریل بعدی</b> — Specific editing/hook idea\n"
                "7) <b>نمره</b> — X/10 — قوی|متوسط|ضعیف"
            )
        else:
            sections = (
                "Include: content summary, visual analysis, brief caption note, "
                "vs page average, next post tip, score X/10."
            )

        user_text = f"{visual_note}\n\n{sections}\n\nReference data (stats; caption is NOT primary source):\n{metrics_text}"

        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]

        if frames:
            for label, b64, mime in frames:
                content.append({"type": "text", "text": f"Frame: {label}"})
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}",
                            "detail": "low",
                        },
                    }
                )
        elif image_b64 and settings.ai_vision_enabled:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_mime};base64,{image_b64}",
                        "detail": "low",
                    },
                }
            )

        payload = {
            "model": settings.ai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "max_tokens": settings.ai_max_tokens,
            "temperature": 0.5,
        }

        timeout = aiohttp.ClientTimeout(total=settings.ai_timeout_seconds)
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        url = settings.ai_chat_completions_url
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                body = await resp.json()
                if resp.status != 200:
                    err = body.get("error", {})
                    msg = err.get("message") if isinstance(err, dict) else str(body)
                    logger.error("AI API HTTP %s (%s): %s", resp.status, url, msg)
                    raise ValueError(ai_error_key(resp.status))
                choices = body.get("choices") or []
                if not choices:
                    raise ValueError("Empty AI response")
                text = (choices[0].get("message") or {}).get("content") or ""
                text = text.strip()
                if not text:
                    raise ValueError("Empty AI response")
                return text[:3900]


ai_client = AIClient()

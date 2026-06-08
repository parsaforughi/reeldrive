"""OpenAI chat + vision via REST (no extra SDK)."""

import base64
import logging
from typing import Any

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

_LANG_NAMES = {"fa": "Persian (Farsi)", "en": "English", "ar": "Arabic"}


class AIClient:
    @property
    def ready(self) -> bool:
        return bool(settings.openai_api_key.strip())

    async def analyze_post(
        self,
        *,
        metrics_text: str,
        lang: str,
        image_b64: str | None = None,
        image_mime: str = "image/jpeg",
    ) -> str:
        if not self.ready:
            raise ValueError("AI not configured")

        lang_name = _LANG_NAMES.get(lang, "Persian (Farsi)")
        system = (
            "You are an expert Instagram growth analyst. "
            f"Write the full analysis in {lang_name}. "
            "Use Telegram HTML only: <b> for section titles, no markdown. "
            "Be concrete and actionable. Keep total length under 3500 characters."
        )
        user_text = (
            "Analyze this Instagram post using the metrics below"
            + (" and the attached image/thumbnail." if image_b64 else ".")
            + "\n\n"
            "Include these sections with <b> titles:\n"
            "1) خلاصه محتوا / Content summary\n"
            "2) تحلیل بصری / Visual analysis (hook, composition, text on screen, vibe)\n"
            "3) تحلیل کپشن / Caption (tone, CTA, hashtags)\n"
            "4) مقایسه با میانگین پیج / vs page average\n"
            "5) پیشنهاد پست بعدی / Next post tip\n"
            "6) نمره / Score: X/10 — قوی|متوسط|ضعیف (or English/Arabic equivalents)\n\n"
            f"{metrics_text}"
        )

        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        if image_b64 and settings.ai_vision_enabled:
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
            "temperature": 0.6,
        }

        timeout = aiohttp.ClientTimeout(total=settings.ai_timeout_seconds)
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                body = await resp.json()
                if resp.status != 200:
                    err = body.get("error", {})
                    msg = err.get("message") if isinstance(err, dict) else str(body)
                    logger.error("OpenAI HTTP %s: %s", resp.status, msg)
                    raise ValueError(f"AI error ({resp.status})")
                choices = body.get("choices") or []
                if not choices:
                    raise ValueError("Empty AI response")
                text = (choices[0].get("message") or {}).get("content") or ""
                text = text.strip()
                if not text:
                    raise ValueError("Empty AI response")
                return text[:3900]


ai_client = AIClient()

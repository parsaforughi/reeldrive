"""HikerAPI (hikerapi.com) client — dedicated Instagram data API, no
login/session required. Used for /following instead of Apify's marketplace
actor, which charges a large per-result markup for the same data.
"""

import json
import logging

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.hikerapi.com"
_MAX_PAGES = 200  # safety cap against runaway pagination, not a real IG limit


class HikerApiClient:
    @property
    def ready(self) -> bool:
        return bool(settings.hikerapi_key)

    def _headers(self) -> dict:
        return {"x-access-key": settings.hikerapi_key, "accept": "application/json"}

    async def _get(self, session: aiohttp.ClientSession, path: str, params: dict) -> dict:
        async with session.get(f"{_BASE}{path}", params=params, headers=self._headers()) as resp:
            body = await resp.text()
            if resp.status == 401:
                raise ValueError("HikerAPI: کلید نامعتبر / invalid API key")
            if resp.status == 404:
                raise ValueError("کاربر پیدا نشد / User not found")
            if not (200 <= resp.status < 300):
                logger.error("HikerAPI HTTP %s on %s: %s", resp.status, path, body[:500])
                raise ValueError(f"HikerAPI خطا ({resp.status})")
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                raise ValueError("پاسخ HikerAPI نامعتبر بود.") from exc

    async def _resolve_user_id(self, session: aiohttp.ClientSession, username: str) -> str:
        handle = username.strip().lstrip("@").lower()
        data = await self._get(session, "/v2/user/by/username", {"username": handle})
        user = data.get("user") or {}
        user_id = user.get("pk") or user.get("id")
        if not user_id:
            raise ValueError("کاربر پیدا نشد / User not found")
        return str(user_id)

    async def fetch_following(self, username: str, limit: int) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            user_id = await self._resolve_user_id(session, username)

            users: list[dict] = []
            page_id: str | None = None
            for _ in range(_MAX_PAGES):
                params = {"user_id": user_id}
                if page_id:
                    params["page_id"] = page_id
                data = await self._get(session, "/v2/user/following", params)
                page_response = data.get("response") or {}
                page_users = page_response.get("users") or []
                users.extend(page_users)
                page_id = data.get("next_page_id")
                if not page_id or len(users) >= limit:
                    break

        return users[:limit]


hiker_client = HikerApiClient()

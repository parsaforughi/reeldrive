"""HikerAPI (hikerapi.com) client — primary provider for the following-list
feature (much cheaper per request than the Apify followings-scraper actor).
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
        async with session.get(
            f"{_BASE}{path}", params=params, headers=self._headers()
        ) as resp:
            body = await resp.text()
            if resp.status == 401:
                raise ValueError("HikerAPI: کلید نامعتبر / invalid API key")
            if resp.status == 404:
                raise ValueError("پیدا نشد / Not found")
            if not (200 <= resp.status < 300):
                logger.error("HikerAPI HTTP %s on %s: %s", resp.status, path, body[:500])
                exc_type = ""
                try:
                    exc_type = (json.loads(body) or {}).get("exc_type", "")
                except json.JSONDecodeError:
                    pass
                if exc_type == "PrivateAccount":
                    raise ValueError("اکانت خصوصی است / private account")
                raise ValueError(f"HikerAPI خطا ({resp.status})")
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                raise ValueError("پاسخ HikerAPI نامعتبر بود.") from exc

    async def _fetch_user(self, session: aiohttp.ClientSession, username: str) -> dict:
        handle = username.strip().lstrip("@").lower()
        data = await self._get(session, "/v2/user/by/username", {"username": handle})
        user = data.get("user") or {}
        if not user:
            raise ValueError("کاربر پیدا نشد / User not found")
        return user

    async def _resolve_user_id(self, session: aiohttp.ClientSession, username: str) -> str:
        user = await self._fetch_user(session, username)
        user_id = user.get("pk") or user.get("id")
        if not user_id:
            raise ValueError("کاربر پیدا نشد / User not found")
        return str(user_id)

    async def fetch_following_count(self, username: str) -> int:
        """Cheap follows-count lookup — a single /user/by/username call, used
        to price the followings-list feature before the much more expensive
        paginated /user/following fetch runs."""
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            user = await self._fetch_user(session, username)

        for key in ("following_count", "followingCount", "follows_count"):
            val = user.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue
        return 0

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

    async def fetch_profile(self, username: str) -> dict:
        """Full profile dict (bio, counts, profile pic, private/verified flags)."""
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            return await self._fetch_user(session, username)

    async def fetch_media_by_url(self, url: str) -> dict:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._get(session, "/v1/media/by/url", {"url": url})
        if not data:
            raise ValueError("پست پیدا نشد / Media not found")
        return data

    async def fetch_user_stories(self, username: str) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        handle = username.strip().lstrip("@").lower()
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._get(
                session, "/v1/user/stories/by/username", {"username": handle}
            )
        return data if isinstance(data, list) else []

    async def fetch_user_highlights(self, username: str) -> list[dict]:
        """Highlight dicts, each already including its `items` (Story list)."""
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        handle = username.strip().lstrip("@").lower()
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._get(
                session, "/v1/user/highlights/by/username", {"username": handle}
            )
        return data if isinstance(data, list) else []

    async def fetch_user_medias(self, username: str, limit: int) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            user_id = await self._resolve_user_id(session, username)

            items: list[dict] = []
            page_id: str | None = None
            for _ in range(_MAX_PAGES):
                params = {"user_id": user_id}
                if page_id:
                    params["page_id"] = page_id
                data = await self._get(session, "/v2/user/medias", params)
                page_response = data.get("response") or {}
                page_items = (
                    page_response.get("items") or page_response.get("medias") or []
                )
                items.extend(page_items)
                page_id = data.get("next_page_id")
                if not page_id or len(items) >= limit:
                    break

        return items[:limit]

    async def fetch_hashtag_medias(self, name: str, amount: int) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._get(
                session,
                "/v1/hashtag/medias/recent",
                {"name": name.lstrip("#"), "amount": amount},
            )
        return data if isinstance(data, list) else []


hiker_client = HikerApiClient()

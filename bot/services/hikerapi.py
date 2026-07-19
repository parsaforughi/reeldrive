"""HikerAPI client for public Instagram profile and following data."""

import json
import logging

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

_MAX_PAGES = 200  # safety cap against runaway pagination, not a real IG limit


class HikerApiClient:
    @property
    def ready(self) -> bool:
        return bool(settings.hikerapi_key)

    def _headers(self) -> dict:
        return {"x-access-key": settings.hikerapi_key, "accept": "application/json"}

    async def _get(
        self, session: aiohttp.ClientSession, path: str, params: dict
    ) -> dict:
        base = settings.hikerapi_base_url.rstrip("/")
        async with session.get(
            f"{base}{path}", params=params, headers=self._headers()
        ) as resp:
            body = await resp.text()
            payload: dict = {}
            try:
                decoded = json.loads(body) if body.strip() else {}
                if isinstance(decoded, dict):
                    payload = decoded
            except json.JSONDecodeError:
                decoded = None

            exc_type = str(payload.get("exc_type") or payload.get("error_type") or "")
            detail = str(payload.get("detail") or payload.get("message") or "")
            if exc_type == "PrivateAccount" or "private" in detail.lower():
                raise ValueError("اکانت خصوصی است / private account")
            if resp.status in (401, 403):
                raise ValueError("HikerAPI: کلید نامعتبر / invalid API key")
            if resp.status == 402:
                raise ValueError("HikerAPI: اعتبار حساب کافی نیست / insufficient credit")
            if resp.status == 404:
                raise ValueError("کاربر پیدا نشد / User not found")
            if resp.status == 429:
                raise ValueError("HikerAPI rate limit / درخواست بیش از حد")
            if not (200 <= resp.status < 300):
                logger.error("HikerAPI HTTP %s on %s: %s", resp.status, path, body[:500])
                raise ValueError(f"HikerAPI خطا ({resp.status})")
            if decoded is None:
                raise ValueError("پاسخ HikerAPI نامعتبر بود.")
            return payload

    @staticmethod
    def _user_from_response(data: dict) -> dict:
        user = data.get("user") if isinstance(data, dict) else None
        if isinstance(user, dict):
            return user
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _page_users(data: dict) -> list[dict]:
        candidates: list[object] = [data.get("users"), data.get("items")]
        response = data.get("response")
        if isinstance(response, dict):
            candidates.extend((response.get("users"), response.get("items")))
        elif isinstance(response, list):
            candidates.append(response)
        for value in candidates:
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _next_page_id(data: dict) -> str | None:
        for container in (data, data.get("response")):
            if not isinstance(container, dict):
                continue
            cursor = (
                container.get("next_page_id")
                or container.get("next_max_id")
                or container.get("max_id")
            )
            if cursor:
                return str(cursor)
        return None

    async def fetch_profile_item(self, username: str) -> dict:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")
        handle = username.strip().lstrip("@").lower()
        timeout = aiohttp.ClientTimeout(total=settings.hikerapi_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._get(
                session, "/v2/user/by/username", {"username": handle}
            )
        user = self._user_from_response(data)
        if not user:
            raise ValueError("کاربر پیدا نشد / User not found")
        return user

    @staticmethod
    def profile_biography(item: dict) -> str:
        return str(item.get("biography") or item.get("bio") or "")

    @staticmethod
    def profile_user_id(item: dict) -> str:
        value = item.get("pk") or item.get("id") or item.get("strong_id__")
        return str(value) if value is not None else ""

    async def _resolve_user_id(self, session: aiohttp.ClientSession, username: str) -> str:
        handle = username.strip().lstrip("@").lower()
        data = await self._get(session, "/v2/user/by/username", {"username": handle})
        user = self._user_from_response(data)
        user_id = user.get("pk") or user.get("id")
        if not user_id:
            raise ValueError("کاربر پیدا نشد / User not found")
        return str(user_id)

    async def fetch_following(self, username: str, limit: int) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        timeout = aiohttp.ClientTimeout(total=settings.hikerapi_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            user_id = await self._resolve_user_id(session, username)

            users: list[dict] = []
            page_id: str | None = None
            for _ in range(_MAX_PAGES):
                params = {"user_id": user_id}
                if page_id:
                    params["page_id"] = page_id
                data = await self._get(session, "/v2/user/following", params)
                page_users = self._page_users(data)
                users.extend(page_users)
                page_id = self._next_page_id(data)
                if not page_id or len(users) >= limit:
                    break

        return users[:limit]


hiker_client = HikerApiClient()

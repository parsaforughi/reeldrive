"""HikerAPI client for Instagram profile, media, and following data."""

import asyncio
import json
import logging
import re

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.hikerapi.com"
_MAX_PAGES = 200  # safety cap against runaway pagination, not a real IG limit
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._]{1,30}$")


class HikerApiError(ValueError):
    """Base error for a completed HikerAPI request."""


class HikerNotFoundError(HikerApiError):
    pass


class HikerPrivateAccountError(HikerApiError):
    pass


class HikerApiClient:
    @property
    def ready(self) -> bool:
        return bool(settings.hikerapi_key)

    def _headers(self) -> dict:
        return {"x-access-key": settings.hikerapi_key, "accept": "application/json"}

    @staticmethod
    def normalize_username(username: str) -> str:
        handle = username.strip().lstrip("@").lower()
        if not _USERNAME_RE.fullmatch(handle):
            raise ValueError("نام کاربری نامعتبر است / Invalid Instagram username")
        return handle

    def _timeout(self) -> aiohttp.ClientTimeout:
        return aiohttp.ClientTimeout(total=max(10, settings.hikerapi_timeout_seconds))

    async def _get(
        self, session: aiohttp.ClientSession, path: str, params: dict
    ) -> object:
        attempts = max(1, settings.hikerapi_max_retries + 1)
        for attempt in range(attempts):
            try:
                async with session.get(
                    f"{_BASE}{path}", params=params, headers=self._headers()
                ) as resp:
                    body = await resp.text()
                    if resp.status == 401:
                        raise HikerApiError(
                            "HikerAPI: کلید نامعتبر / invalid API key"
                        )
                    if resp.status == 404:
                        logger.warning(
                            "HikerAPI HTTP 404 on %s params=%s", path, params
                        )
                        raise HikerNotFoundError("پیدا نشد / Not found")
                    if resp.status == 429 or resp.status >= 500:
                        if attempt + 1 < attempts:
                            logger.warning(
                                "HikerAPI HTTP %s on %s; retrying (%s/%s)",
                                resp.status,
                                path,
                                attempt + 1,
                                attempts - 1,
                            )
                            await asyncio.sleep(0.5 * (2**attempt))
                            continue
                    if not (200 <= resp.status < 300):
                        logger.error(
                            "HikerAPI HTTP %s on %s params=%s: %s",
                            resp.status,
                            path,
                            params,
                            body[:500],
                        )
                        exc_type = ""
                        try:
                            payload = json.loads(body) or {}
                            if isinstance(payload, dict):
                                exc_type = str(payload.get("exc_type") or "")
                        except json.JSONDecodeError:
                            pass
                        if exc_type == "PrivateAccount":
                            raise HikerPrivateAccountError(
                                "اکانت خصوصی است / private account"
                            )
                        raise HikerApiError(f"HikerAPI خطا ({resp.status})")
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError as exc:
                        raise HikerApiError("پاسخ HikerAPI نامعتبر بود.") from exc
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt + 1 < attempts:
                    logger.warning(
                        "HikerAPI network error on %s; retrying (%s/%s): %s",
                        path,
                        attempt + 1,
                        attempts - 1,
                        exc,
                    )
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise HikerApiError(
                    "HikerAPI timeout / connection error"
                ) from exc
        raise HikerApiError("HikerAPI request failed")

    async def _fetch_user(self, session: aiohttp.ClientSession, username: str) -> dict:
        handle = self.normalize_username(username)
        data = await self._get(session, "/v2/user/by/username", {"username": handle})
        user = data.get("user") if isinstance(data, dict) else None
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

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
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

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            profile = await self._fetch_user(session, username)
            user_id = profile.get("pk") or profile.get("id")
            if not user_id:
                raise HikerNotFoundError("کاربر پیدا نشد / User not found")
            if any(
                bool(profile.get(key))
                for key in ("is_private", "isPrivate", "private")
            ):
                raise HikerPrivateAccountError(
                    "اکانت خصوصی است / private account"
                )
            user_id = str(user_id)
            handle = self.normalize_username(username)
            # Primary: g1 legacy public GraphQL — one request per page, works
            # for normal public accounts where the paginated v2/g2 endpoints
            # return an empty list, and it is the cheapest (1 request/call).
            users = await self._fetch_following_g1(session, user_id, limit)
            if not users:
                # g1 came back empty — fall back to the paginated g2 endpoint
                # before giving up, in case g1 is unavailable for this account.
                logger.info(
                    "HikerAPI g1 following empty for @%s; trying g2 fallback",
                    handle,
                )
                users = await self._fetch_following_g2(session, user_id, limit)
        return users[:limit]

    async def _fetch_following_g1(
        self, session: aiohttp.ClientSession, user_id: str, limit: int
    ) -> list[dict]:
        users: list[dict] = []
        cursor: str | None = None
        for _ in range(_MAX_PAGES):
            params: dict[str, object] = {"user_id": user_id}
            if cursor:
                params["end_cursor"] = cursor
            data = await self._get(session, "/g1/user/following", params)
            if not isinstance(data, list) or len(data) != 2:
                raise HikerApiError("پاسخ HikerAPI نامعتبر بود.")
            page_users = data[0] if isinstance(data[0], list) else []
            users.extend(item for item in page_users if isinstance(item, dict))
            cursor = str(data[1]) if data[1] else None
            if not cursor or len(users) >= limit:
                break
        return users[:limit]

    async def _fetch_following_g2(
        self, session: aiohttp.ClientSession, user_id: str, limit: int
    ) -> list[dict]:
        users: list[dict] = []
        page_id: str | None = None
        for _ in range(_MAX_PAGES):
            params = {"user_id": user_id}
            if page_id:
                params["page_id"] = page_id
            data = await self._get(session, "/g2/user/following", params)
            if not isinstance(data, dict):
                raise HikerApiError("پاسخ HikerAPI نامعتبر بود.")
            page_response = data.get("response") or {}
            page_users = (
                page_response.get("users") if isinstance(page_response, dict) else []
            ) or []
            users.extend(item for item in page_users if isinstance(item, dict))
            page_id = data.get("next_page_id")
            if not page_id or len(users) >= limit:
                break
        return users[:limit]

    async def fetch_profile(self, username: str) -> dict:
        """Full profile dict (bio, counts, profile pic, private/verified flags)."""
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            return await self._fetch_user(session, username)

    async def fetch_media_by_url(self, url: str) -> dict:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(session, "/v1/media/by/url", {"url": url})
        if not isinstance(data, dict) or not data:
            raise ValueError("پست پیدا نشد / Media not found")
        return data

    async def fetch_user_stories(self, username: str) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        handle = self.normalize_username(username)
        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(
                session, "/v1/user/stories/by/username", {"username": handle}
            )
        return data if isinstance(data, list) else []

    async def fetch_user_highlights(self, username: str) -> list[dict]:
        """Highlight dicts, each already including its `items` (Story list)."""
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        handle = self.normalize_username(username)
        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(
                session, "/v1/user/highlights/by/username", {"username": handle}
            )
        return data if isinstance(data, list) else []

    async def fetch_user_medias(self, username: str, limit: int) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            user_id = await self._resolve_user_id(session, username)

            items: list[dict] = []
            page_id: str | None = None
            for _ in range(_MAX_PAGES):
                params = {"user_id": user_id}
                if page_id:
                    params["page_id"] = page_id
                data = await self._get(session, "/v2/user/medias", params)
                if not isinstance(data, dict):
                    raise HikerApiError("پاسخ HikerAPI نامعتبر بود.")
                page_response = data.get("response") or {}
                page_items = (
                    page_response.get("items") or page_response.get("medias") or []
                    if isinstance(page_response, dict)
                    else []
                )
                items.extend(item for item in page_items if isinstance(item, dict))
                page_id = data.get("next_page_id")
                if not page_id or len(items) >= limit:
                    break

        return items[:limit]

    async def fetch_hashtag_medias(self, name: str, amount: int) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(
                session,
                "/v1/hashtag/medias/recent",
                {"name": name.lstrip("#"), "amount": amount},
            )
        return data if isinstance(data, list) else []


hiker_client = HikerApiClient()

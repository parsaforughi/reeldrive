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


class HikerEndpointDeprecatedError(HikerApiError):
    """HikerAPI returned HTTP 410 / EndpointDeprecated for this path."""


class HikerHiddenFollowListError(HikerPrivateAccountError):
    """Public profile whose follow graph is hidden from anonymous HikerAPI."""


def _looks_like_media(item: dict) -> bool:
    return any(
        key in item
        for key in (
            "media_type",
            "video_url",
            "image_versions2",
            "image_versions",
            "thumbnail_url",
        )
    )


def flatten_media_items(items: list[dict]) -> list[dict]:
    """Prefer nested `media` when a highlight/story wrapper has no CDN fields."""
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if _looks_like_media(item):
            result.append(item)
            continue
        media = item.get("media")
        if isinstance(media, dict) and _looks_like_media(media):
            result.append(media)
            continue
        result.append(item)
    return result


def extract_story_items(data: object) -> list[dict]:
    """Normalize Hiker story/highlight payloads into a list of media dicts."""
    if isinstance(data, list):
        return flatten_media_items([item for item in data if isinstance(item, dict)])
    if not isinstance(data, dict) or not data:
        return []
    if _looks_like_media(data):
        return [data]
    for key in ("reel", "response", "story"):
        inner = data.get(key)
        if isinstance(inner, list):
            return flatten_media_items(
                [item for item in inner if isinstance(item, dict)]
            )
        if isinstance(inner, dict):
            items = inner.get("items")
            if isinstance(items, list):
                return flatten_media_items(
                    [item for item in items if isinstance(item, dict)]
                )
            if _looks_like_media(inner):
                return [inner]
    items = data.get("items")
    if isinstance(items, list):
        return flatten_media_items([item for item in items if isinstance(item, dict)])
    return []


def extract_highlight_tray(data: object) -> list[dict]:
    """Normalize Hiker highlight-list payloads into tray highlight dicts."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict) or not data:
        return []
    for key in ("tray", "highlights"):
        val = data.get(key)
        if isinstance(val, list):
            return [item for item in val if isinstance(item, dict)]
    response = data.get("response")
    if response is not None and response is not data:
        return extract_highlight_tray(response)
    return []


def normalize_highlight_id(value: str) -> str:
    text = str(value or "").strip()
    if text.lower().startswith("highlight:"):
        return text.split(":", 1)[1].strip()
    return text


def _iter_search_users(data: object) -> list[dict]:
    """Normalize the /user/search/followers response into a list of user dicts,
    tolerating the list / {"users": [...]} / {"response": {"users": [...]}}
    shapes HikerAPI uses across endpoint variants."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("users", "response", "results"):
            val = data.get(key)
            if isinstance(val, dict):
                val = val.get("users")
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    return []


def _as_follow_user(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None
    if item.get("username") or item.get("user_name") or item.get("pk") or item.get("id"):
        return item
    inner = item.get("user") or item.get("node")
    if isinstance(inner, dict):
        return inner
    return item


def extract_follow_page(data: object) -> tuple[list[dict], str | None]:
    """Normalize Hiker follow-list pages into ``(users, next_cursor)``.

    Current HikerAPI variants return any of:

    * ``[users, cursor]`` (gql/v1 chunk)
    * ``{"response": {"users"|"items": [...]}, "next_page_id": ...}`` (g2/v2)
    * ``{"users": [...], "next_max_id": ...}`` (marketing v1 examples)
    """
    if isinstance(data, list) and len(data) == 2 and not (
        data and isinstance(data[0], dict) and (data[0].get("username") or data[0].get("pk"))
    ):
        raw_users = data[0] if isinstance(data[0], list) else []
        users = [user for item in raw_users if (user := _as_follow_user(item))]
        cursor = str(data[1]) if data[1] else None
        return users, cursor
    if isinstance(data, list):
        return [user for item in data if (user := _as_follow_user(item))], None
    if not isinstance(data, dict) or not data:
        return [], None

    payload = data.get("response") if isinstance(data.get("response"), dict) else data
    raw_users = payload.get("users") if isinstance(payload, dict) else None
    if not isinstance(raw_users, list):
        raw_users = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(raw_users, list):
        raw_users = []
    users = [user for item in raw_users if (user := _as_follow_user(item))]

    paging = payload.get("paging_info") if isinstance(payload, dict) else None
    cursor = (
        data.get("next_page_id")
        or (payload.get("next_page_id") if isinstance(payload, dict) else None)
        or (payload.get("next_max_id") if isinstance(payload, dict) else None)
        or (payload.get("max_id") if isinstance(payload, dict) else None)
        or (payload.get("end_cursor") if isinstance(payload, dict) else None)
        or (paging.get("max_id") if isinstance(paging, dict) else None)
    )
    more = True
    if isinstance(payload, dict) and payload.get("has_more") is False:
        more = False
    if isinstance(paging, dict) and paging.get("more_available") is False:
        more = False
    if not more or not cursor:
        return users, None
    return users, str(cursor)


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
                    if (resp.status == 429 or resp.status >= 500) and (
                        attempt + 1 < attempts
                    ):
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
                        exc_type = ""
                        detail = ""
                        try:
                            payload = json.loads(body) or {}
                            if isinstance(payload, dict):
                                exc_type = str(payload.get("exc_type") or "")
                                detail = str(payload.get("detail") or "")
                        except json.JSONDecodeError:
                            pass
                        if resp.status == 410 or exc_type == "EndpointDeprecated":
                            logger.info(
                                "HikerAPI deprecated %s (%s): %s",
                                path,
                                resp.status,
                                (detail or body)[:200],
                            )
                            raise HikerEndpointDeprecatedError(
                                f"HikerAPI endpoint deprecated ({path})"
                            )
                        logger.error(
                            "HikerAPI HTTP %s on %s params=%s: %s",
                            resp.status,
                            path,
                            params,
                            body[:500],
                        )
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
            users = await self._fetch_public_follow_list(
                session,
                user_id,
                limit,
                "following",
                handle,
                self._profile_follow_count(profile, "following"),
            )
        return users[:limit]

    async def fetch_followers(self, username: str, limit: int) -> list[dict]:
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
            users = await self._fetch_public_follow_list(
                session,
                user_id,
                limit,
                "followers",
                handle,
                self._profile_follow_count(profile, "followers"),
            )
        return users[:limit]

    @staticmethod
    def _profile_follow_count(profile: dict, kind: str) -> int:
        keys = (
            ("following_count", "followingCount", "follows_count")
            if kind == "following"
            else (
                "follower_count",
                "followerCount",
                "followers_count",
                "followersCount",
            )
        )
        for key in keys:
            try:
                return max(0, int(profile[key]))
            except (KeyError, TypeError, ValueError):
                continue
        return 0

    async def _fetch_public_follow_list(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        limit: int,
        kind: str,
        handle: str,
        expected_count: int,
    ) -> list[dict]:
        """Fetch a public follow list from currently supported HikerAPI paths.

        Instagram retired the public GraphQL surface behind ``/g1/user/{kind}``
        (HTTP 410 ``EndpointDeprecated``). Official HikerAPI docs now prefer
        ``/g2/user/{kind}``, then ``/v1/user/{kind}/chunk``. ``/v2`` can still
        answer ``PrivateAccount`` for a public profile that hid its follow
        graph — that is not treated as fatal until every current method fails.
        """
        fetchers = (
            ("g2", self._fetch_follow_g2),
            ("v1", self._fetch_follow_v1_chunk),
            ("gql", self._fetch_follow_gql),
            ("v2", self._fetch_follow_v2),
        )
        last_error: HikerApiError | None = None
        last_users: list[dict] = []
        hidden_graph = False
        for name, fetcher in fetchers:
            try:
                users = await fetcher(session, user_id, limit, kind)
            except HikerEndpointDeprecatedError as exc:
                last_error = exc
                logger.info(
                    "HikerAPI %s %s deprecated for @%s; trying next method",
                    name,
                    kind,
                    handle,
                )
                continue
            except HikerPrivateAccountError as exc:
                # Public profiles can still hide their follow graph on some
                # HikerAPI surfaces (seen as HTTP 403 PrivateAccount on /v2).
                # Keep trying the remaining current methods first.
                hidden_graph = True
                last_error = exc
                logger.warning(
                    "HikerAPI %s %s hid follow graph for @%s; trying next method",
                    name,
                    kind,
                    handle,
                )
                continue
            except HikerApiError as exc:
                last_error = exc
                logger.warning(
                    "HikerAPI %s %s failed for @%s (%s)",
                    name,
                    kind,
                    handle,
                    type(exc).__name__,
                )
                continue
            if users:
                logger.info(
                    "HikerAPI %s %s returned %d user(s) for @%s",
                    name,
                    kind,
                    len(users),
                    handle,
                )
                return users
            last_users = users
            logger.info("HikerAPI %s %s empty for @%s", name, kind, handle)

        if expected_count <= 0:
            return last_users
        if hidden_graph:
            raise HikerHiddenFollowListError(
                "Follow graph is privacy-blocked / inconclusive"
            )
        if last_error:
            raise last_error
        raise HikerHiddenFollowListError(
            f"HikerAPI returned an empty {kind} list for a non-empty profile"
        )

    async def followers_follow_back(
        self, user_id: str, candidates: list[str], *, concurrency: int = 8
    ) -> set[str]:
        """Return the subset of ``candidates`` (usernames) that follow
        ``user_id``, via /v1/user/search/followers — one request per candidate.

        This is the cheap, EXACT way to test reciprocity for a small following
        set against a very large follower list: instead of paginating hundreds
        of thousands of followers, we search each of the (few hundred) accounts
        the user follows inside their own followers. Requests are bounded by
        ``concurrency`` so a big following set doesn't burst the API.
        """
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")
        found: set[str] = set()
        semaphore = asyncio.Semaphore(max(1, concurrency))
        completed = 0
        nonempty = 0

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:

            async def check(name: str) -> None:
                nonlocal completed, nonempty
                target = name.lstrip("@").lower()
                async with semaphore:
                    try:
                        data = await self._get(
                            session,
                            "/v1/user/search/followers",
                            {
                                "user_id": user_id,
                                "query": target,
                                # Public profiles may still hide their follow
                                # graph. HikerAPI documents this flag for the
                                # search endpoint specifically; without it the
                                # endpoint can return an empty 200 response for
                                # every real follower.
                                "force": "true",
                            },
                        )
                    except HikerNotFoundError:
                        completed += 1
                        return
                users = _iter_search_users(data)
                completed += 1
                if users:
                    nonempty += 1
                for item in users:
                    handle = (
                        str(item.get("username") or item.get("user_name") or "")
                        .lstrip("@")
                        .lower()
                    )
                    if handle == target:
                        found.add(target)
                        return

            await asyncio.gather(*(check(n) for n in candidates))
        logger.info(
            "HikerAPI follower search: candidates=%d completed=%d "
            "nonempty=%d matched=%d",
            len(candidates),
            completed,
            nonempty,
            len(found),
        )
        if len(candidates) >= 20 and completed == len(candidates) and nonempty == 0:
            # A fully empty batch on a sizeable real following list is the
            # response HikerAPI gives when follower search is privacy-blocked.
            # It is not evidence that every candidate is a non-follower. Route
            # the report through the owner's authenticated session instead of
            # publishing a confidently wrong all-ghost result.
            logger.warning(
                "HikerAPI follower search was inconclusive: all %d responses empty",
                len(candidates),
            )
            raise HikerPrivateAccountError(
                "Follower search is privacy-blocked / inconclusive"
            )
        return found

    async def _paginate_follow_list(
        self,
        session: aiohttp.ClientSession,
        path: str,
        user_id: str,
        limit: int,
        cursor_param: str,
        extra_params: dict[str, object] | None = None,
    ) -> list[dict]:
        users: list[dict] = []
        cursor: str | None = None
        for _ in range(_MAX_PAGES):
            params: dict[str, object] = {"user_id": user_id}
            if extra_params:
                params.update(extra_params)
            if cursor:
                params[cursor_param] = cursor
            data = await self._get(session, path, params)
            page_users, cursor = extract_follow_page(data)
            users.extend(page_users)
            if not cursor or len(users) >= limit:
                break
        return users[:limit]

    async def _fetch_follow_g2(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        limit: int,
        kind: str = "following",
    ) -> list[dict]:
        return await self._paginate_follow_list(
            session, f"/g2/user/{kind}", user_id, limit, "page_id"
        )

    async def _fetch_follow_v1_chunk(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        limit: int,
        kind: str = "following",
    ) -> list[dict]:
        return await self._paginate_follow_list(
            session, f"/v1/user/{kind}/chunk", user_id, limit, "max_id"
        )

    async def _fetch_follow_gql(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        limit: int,
        kind: str = "following",
    ) -> list[dict]:
        return await self._paginate_follow_list(
            session,
            f"/gql/user/{kind}/chunk",
            user_id,
            limit,
            "end_cursor",
            {"force": "true"},
        )

    async def _fetch_follow_v2(
        self,
        session: aiohttp.ClientSession,
        user_id: str,
        limit: int,
        kind: str = "following",
    ) -> list[dict]:
        return await self._paginate_follow_list(
            session, f"/v2/user/{kind}", user_id, limit, "page_id"
        )

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
        return extract_story_items(data)

    async def fetch_story_by_url(self, url: str) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(session, "/v1/story/by/url", {"url": url})
        items = extract_story_items(data)
        if not items:
            raise HikerNotFoundError("استوری پیدا نشد / Story not found")
        return items

    async def fetch_story_by_id(self, story_id: str) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(session, "/v1/story/by/id", {"id": story_id})
        items = extract_story_items(data)
        if not items:
            raise HikerNotFoundError("استوری پیدا نشد / Story not found")
        return items

    async def fetch_share_by_url(self, url: str) -> dict:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(session, "/v1/share/by/url", {"url": url})
        if not isinstance(data, dict) or not data:
            raise HikerNotFoundError("لینک اشتراک پیدا نشد / Share link not found")
        return data

    async def fetch_highlight_by_id(self, highlight_id: str) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        hid = normalize_highlight_id(highlight_id)
        candidates = [hid]
        raw = str(highlight_id).strip()
        if raw and raw not in candidates:
            candidates.append(raw)

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            for candidate in candidates:
                try:
                    data = await self._get(
                        session, "/v1/highlight/by/id", {"id": candidate}
                    )
                except HikerNotFoundError:
                    data = None
                items = extract_story_items(data) if data is not None else []
                if items:
                    return items

            last_error: HikerNotFoundError | None = None
            for candidate in candidates:
                items: list[dict] = []
                page_id: str | None = None
                try:
                    for _ in range(_MAX_PAGES):
                        params = {"id": candidate}
                        if page_id:
                            params["page_id"] = page_id
                        data = await self._get(
                            session, "/v2/highlight/by/id", params
                        )
                        items.extend(extract_story_items(data))
                        page_id = (
                            data.get("next_page_id")
                            if isinstance(data, dict)
                            else None
                        )
                        if not page_id:
                            break
                except HikerNotFoundError as exc:
                    last_error = exc
                    continue
                if items:
                    return items
            if last_error is not None and not items:
                raise last_error
        return []

    async def fetch_highlight_by_url(self, url: str) -> list[dict]:
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(session, "/v1/highlight/by/url", {"url": url})
        return extract_story_items(data)

    async def fetch_user_highlights(self, username: str) -> list[dict]:
        """Highlight tray dicts. Media items are often missing until by-id."""
        if not self.ready:
            raise ValueError("HikerAPI تنظیم نشده / HikerAPI not configured")

        handle = self.normalize_username(username)
        async with aiohttp.ClientSession(timeout=self._timeout()) as session:
            data = await self._get(
                session, "/v1/user/highlights/by/username", {"username": handle}
            )
        return extract_highlight_tray(data)

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

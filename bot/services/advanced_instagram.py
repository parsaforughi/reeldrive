"""Encrypted, per-user Instagram sessions for explicitly authorized reads.

This service is intentionally separate from the shared service/bridge clients.
Public data continues to use HikerAPI. An advanced session is used only when a
private target requires the connected user's own Instagram permissions.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from urllib.parse import unquote
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    ClientError,
    ClientForbiddenError,
    ClientThrottledError,
    FeedbackRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    ProxyAddressIsBlocked,
    RateLimitError,
    SentryBlock,
)

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import ActivityLog, AdvancedInstagramSession
from bot.services.hikerapi import hiker_client
from bot.time_utils import utc_now

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _stable_session_settings(account_key: str) -> dict:
    """Build a repeatable device identity without including the session secret."""

    seed = hashlib.sha256(
        f"reeldrive-instagram-device:{account_key.lstrip('@').lower()}".encode()
    ).digest()

    def stable_uuid(label: str) -> str:
        digest = hashlib.sha256(seed + label.encode()).digest()
        return str(UUID(bytes=digest[:16], version=4))

    return {
        "uuids": {
            "phone_id": stable_uuid("phone_id"),
            "uuid": stable_uuid("uuid"),
            "client_session_id": stable_uuid("client_session_id"),
            "advertising_id": stable_uuid("advertising_id"),
            "android_device_id": "android-"
            + hashlib.sha256(seed + b"android_device_id").hexdigest()[:16],
            "request_id": stable_uuid("request_id"),
            "tray_session_id": stable_uuid("tray_session_id"),
        }
    }


def _normalize_sessionid(value: str) -> tuple[str, str]:
    """Return a safe decoded ``(sessionid, Instagram user id)`` pair."""

    raw = unquote((value or "").strip())
    if raw.lower().startswith("sessionid="):
        raw = raw.split("=", 1)[1].strip()
    if (
        not 10 <= len(raw) <= 512
        or any(char in raw for char in ("\r", "\n", ";"))
    ):
        raise AdvancedInvalidSession()
    match = re.fullmatch(r"(\d+):[^\s]+", raw)
    if not match:
        raise AdvancedInvalidSession()
    return raw, match.group(1)


class AdvancedInstagramError(ValueError):
    key = "advanced_connect_error"

    def __init__(self) -> None:
        super().__init__(self.key)


class AdvancedConnectRequired(AdvancedInstagramError):
    key = "advanced_connect_required"


class AdvancedSessionExpired(AdvancedInstagramError):
    key = "advanced_session_expired"


class AdvancedInvalidSession(AdvancedInstagramError):
    key = "advanced_invalid_session"


class AdvancedPrivateAccessDenied(AdvancedInstagramError):
    key = "advanced_private_access_denied"


class AdvancedChallengeRequired(AdvancedInstagramError):
    key = "advanced_challenge_required"


class AdvancedRateLimited(AdvancedInstagramError):
    key = "advanced_rate_limited"


class AdvancedProxyRequired(AdvancedInstagramError):
    key = "advanced_proxy_required"


class AdvancedFeatureDisabled(AdvancedInstagramError):
    key = "advanced_feature_disabled"


@dataclass(frozen=True)
class AdvancedSessionInfo:
    connected: bool
    username: str = ""
    status: str = "not_connected"
    connected_at: datetime | None = None


class AdvancedInstagramService:
    def __init__(self) -> None:
        self._clients: OrderedDict[int, Client] = OrderedDict()
        self._locks: dict[int, asyncio.Lock] = {}

    @property
    def ready(self) -> bool:
        return len(settings.instagram_session_encryption_key.strip()) >= 32

    @property
    def proxy(self) -> str:
        return (
            settings.advanced_instagram_proxy.strip()
            or settings.instagram_proxy.strip()
        )

    def _cipher(self) -> Fernet:
        secret = settings.instagram_session_encryption_key.strip()
        if len(secret) < 32:
            raise AdvancedFeatureDisabled()
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        return Fernet(key)

    def _encrypt_settings(self, payload: dict) -> str:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        return self._cipher().encrypt(raw).decode()

    def _decrypt_settings(self, token: str) -> dict:
        try:
            raw = self._cipher().decrypt(token.encode())
            payload = json.loads(raw)
        except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AdvancedSessionExpired() from exc
        if not isinstance(payload, dict):
            raise AdvancedSessionExpired()
        return payload

    def _lock(self, telegram_id: int) -> asyncio.Lock:
        return self._locks.setdefault(telegram_id, asyncio.Lock())

    def _cache_client(self, telegram_id: int, client: Client) -> None:
        self._clients.pop(telegram_id, None)
        self._clients[telegram_id] = client
        maximum = max(1, settings.advanced_instagram_client_cache_size)
        while len(self._clients) > maximum:
            self._clients.popitem(last=False)

    async def session_info(self, telegram_id: int) -> AdvancedSessionInfo:
        async with async_session() as session:
            row = await session.get(AdvancedInstagramSession, telegram_id)
        if not row:
            return AdvancedSessionInfo(connected=False)
        return AdvancedSessionInfo(
            connected=row.status == "connected",
            username=row.instagram_username,
            status=row.status,
            connected_at=row.connected_at,
        )

    async def has_session(self, telegram_id: int) -> bool:
        return self.ready and (await self.session_info(telegram_id)).connected

    def _new_client(
        self,
        stored_settings: dict | None = None,
        *,
        username: str = "",
    ) -> Client:
        initial_settings = stored_settings
        if initial_settings is None and username:
            initial_settings = _stable_session_settings(username)
        client = Client(
            settings=initial_settings or {},
            proxy=self.proxy or None,
            delay_range=[1, 3],
            request_timeout=10,
        )
        return client

    def _session_client_sync(self, sessionid: str) -> tuple[Client, str, str]:
        """Validate a user-supplied sessionid and resolve its owning account.

        The raw cookie is never logged. It only lives in the request, the
        in-memory client, and the encrypted settings blob persisted by
        ``connect_with_sessionid``.
        """
        sid, session_user_id = _normalize_sessionid(sessionid)
        client = self._new_client(username=session_user_id)
        try:
            client.settings["cookies"] = {"sessionid": sid}
            client.init()
            client.authorization_data = {
                "ds_user_id": session_user_id,
                "sessionid": sid,
                "should_use_header_over_cookies": True,
            }
            client.cookie_dict["ds_user_id"] = session_user_id
            account = client.account_info()
        except LoginRequired as exc:
            raise AdvancedInvalidSession() from exc
        except ChallengeRequired as exc:
            raise AdvancedChallengeRequired() from exc
        except (
            SentryBlock,
            ProxyAddressIsBlocked,
            ClientForbiddenError,
        ) as exc:
            logger.warning(
                "Advanced Instagram login blocked error_type=%s",
                type(exc).__name__,
            )
            raise AdvancedProxyRequired() from exc
        except (
            PleaseWaitFewMinutes,
            FeedbackRequired,
            RateLimitError,
            ClientThrottledError,
        ) as exc:
            raise AdvancedRateLimited() from exc
        except ClientError as exc:
            logger.warning(
                "Advanced Instagram session rejected error_type=%s",
                type(exc).__name__,
            )
            raise AdvancedInvalidSession() from exc

        account_username = str(account.username or "").lstrip("@").lower()
        account_id = str(account.pk or "")
        if not account_username or not account_id or account_id != session_user_id:
            raise AdvancedInvalidSession()
        client.username = account_username
        client.user_id = int(account_id)
        return client, account_username, account_id

    async def connect_with_sessionid(
        self, telegram_id: int, sessionid: str
    ) -> AdvancedSessionInfo:
        if not self.ready:
            raise AdvancedFeatureDisabled()

        async with self._lock(telegram_id):
            client, account_username, account_id = await asyncio.to_thread(
                self._session_client_sync,
                sessionid,
            )
            encrypted = self._encrypt_settings(client.get_settings())
            now = utc_now()
            async with async_session() as session:
                row = await session.get(AdvancedInstagramSession, telegram_id)
                if row:
                    row.instagram_username = account_username
                    row.instagram_user_id = account_id
                    row.encrypted_settings = encrypted
                    row.status = "connected"
                    row.connected_at = now
                    row.last_used_at = now
                else:
                    session.add(
                        AdvancedInstagramSession(
                            telegram_id=telegram_id,
                            instagram_username=account_username,
                            instagram_user_id=account_id,
                            encrypted_settings=encrypted,
                            status="connected",
                            connected_at=now,
                            last_used_at=now,
                        )
                    )
                session.add(
                    ActivityLog(
                        telegram_id=telegram_id,
                        event_type="advanced_connect",
                        detail=f"@{account_username}",
                    )
                )
                await session.commit()
            self._cache_client(telegram_id, client)
            logger.info(
                "Advanced Instagram session imported telegram=%s username=@%s",
                telegram_id,
                account_username,
            )
            return AdvancedSessionInfo(
                connected=True,
                username=account_username,
                status="connected",
                connected_at=now,
            )

    async def _session_row(self, telegram_id: int) -> AdvancedInstagramSession:
        async with async_session() as session:
            row = await session.get(AdvancedInstagramSession, telegram_id)
        if not row:
            raise AdvancedConnectRequired()
        if row.status != "connected":
            raise AdvancedSessionExpired()
        return row

    async def _client_for(
        self, telegram_id: int
    ) -> tuple[Client, AdvancedInstagramSession]:
        if not self.ready:
            raise AdvancedFeatureDisabled()
        row = await self._session_row(telegram_id)
        client = self._clients.get(telegram_id)
        if client:
            self._clients.move_to_end(telegram_id)
            return client, row
        stored = self._decrypt_settings(row.encrypted_settings)
        client = self._new_client(stored_settings=stored)
        client.username = row.instagram_username
        self._cache_client(telegram_id, client)
        return client, row

    async def _mark_expired(self, telegram_id: int) -> None:
        self._clients.pop(telegram_id, None)
        async with async_session() as session:
            row = await session.get(AdvancedInstagramSession, telegram_id)
            if row:
                row.status = "reconnect_required"
                await session.commit()

    async def _run(
        self,
        telegram_id: int,
        operation: Callable[[Client, AdvancedInstagramSession], T],
    ) -> T:
        async with self._lock(telegram_id):
            client, row = await self._client_for(telegram_id)
            try:
                result = await asyncio.to_thread(operation, client, row)
            except (LoginRequired, ChallengeRequired) as exc:
                await self._mark_expired(telegram_id)
                raise AdvancedSessionExpired() from exc
            except (PleaseWaitFewMinutes, FeedbackRequired) as exc:
                raise AdvancedRateLimited() from exc
            async with async_session() as session:
                stored = await session.get(AdvancedInstagramSession, telegram_id)
                if stored:
                    # Instagram may rotate authorization/cookie values while a
                    # session is in use. Persist the refreshed settings so a
                    # worker restart does not resurrect stale credentials.
                    stored.encrypted_settings = self._encrypt_settings(
                        client.get_settings()
                    )
                    stored.last_used_at = utc_now()
                    await session.commit()
            return result

    @staticmethod
    def _ensure_private_access(
        client: Client,
        row: AdvancedInstagramSession,
        target,
    ) -> None:
        if not bool(target.is_private):
            return
        if str(target.pk) == row.instagram_user_id:
            return
        relationship = client.user_friendship_v1(str(target.pk))
        if not relationship.following:
            raise AdvancedPrivateAccessDenied()

    async def fetch_following(
        self, telegram_id: int, username: str, limit: int
    ) -> list[dict]:
        handle = hiker_client.normalize_username(username)

        def operation(client: Client, row: AdvancedInstagramSession) -> list[dict]:
            target = client.user_info_by_username_v1(handle)
            self._ensure_private_access(client, row, target)
            users = client.user_following(
                str(target.pk), use_cache=False, amount=max(1, limit)
            )
            return [
                {
                    "username": str(user.username or ""),
                    "full_name": str(user.full_name or ""),
                    "is_private": bool(user.is_private),
                    "is_verified": bool(user.is_verified),
                }
                for user in users.values()
                if user.username
            ][:limit]

        return await self._run(telegram_id, operation)

    async def fetch_follow_sets(
        self, telegram_id: int, username: str, limit: int
    ) -> tuple[list[dict], list[dict]]:
        """Return (following, followers) visible to the connected session.

        The target may be the session owner or a private account that this
        session is allowed to view. Both lists are read in one session and
        private data is never placed in the shared HikerAPI cache.
        """
        handle = hiker_client.normalize_username(username)

        def to_items(users: dict) -> list[dict]:
            return [
                {
                    "username": str(user.username or ""),
                    "full_name": str(user.full_name or ""),
                    "is_private": bool(user.is_private),
                    "is_verified": bool(user.is_verified),
                }
                for user in users.values()
                if user.username
            ][:limit]

        def operation(
            client: Client, row: AdvancedInstagramSession
        ) -> tuple[list[dict], list[dict]]:
            target = client.user_info_by_username_v1(handle)
            self._ensure_private_access(client, row, target)
            uid = str(target.pk)
            following = client.user_following(uid, use_cache=False, amount=max(1, limit))
            followers = client.user_followers(uid, use_cache=False, amount=max(1, limit))
            return to_items(following), to_items(followers)

        return await self._run(telegram_id, operation)

    async def fetch_following_count(self, telegram_id: int, username: str) -> int:
        handle = hiker_client.normalize_username(username)

        def operation(client: Client, row: AdvancedInstagramSession) -> int:
            target = client.user_info_by_username_v1(handle)
            self._ensure_private_access(client, row, target)
            return int(target.following_count or 0)

        return await self._run(telegram_id, operation)

    async def fetch_stories(self, telegram_id: int, username: str) -> list[dict]:
        handle = hiker_client.normalize_username(username)

        def operation(client: Client, row: AdvancedInstagramSession) -> list[dict]:
            target = client.user_info_by_username_v1(handle)
            self._ensure_private_access(client, row, target)
            stories = client.user_stories(str(target.pk))
            items: list[dict] = []
            for story in stories:
                video_url = str(story.video_url or "")
                image_url = str(story.thumbnail_url or "")
                items.append(
                    {
                        "media_type": int(story.media_type or 1),
                        "video_url": video_url,
                        "image_versions2": {
                            "candidates": [{"url": image_url}] if image_url else []
                        },
                        "taken_at": story.taken_at.isoformat()
                        if story.taken_at
                        else "",
                    }
                )
            return items

        return await self._run(telegram_id, operation)

    async def disconnect(self, telegram_id: int) -> bool:
        async with self._lock(telegram_id):
            self._clients.pop(telegram_id, None)
            async with async_session() as session:
                row = await session.get(AdvancedInstagramSession, telegram_id)
                if not row:
                    return False
                username = row.instagram_username
                await session.delete(row)
                session.add(
                    ActivityLog(
                        telegram_id=telegram_id,
                        event_type="advanced_disconnect",
                        detail=f"@{username}",
                    )
                )
                await session.commit()
            # Remove only ReelDrive's encrypted copy. Calling Instagram logout
            # here would invalidate the browser sessionid the user deliberately
            # imported and could sign them out of their own device.
            return True


advanced_instagram = AdvancedInstagramService()

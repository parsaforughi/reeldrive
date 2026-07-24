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
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from instagrapi import Client
from instagrapi.exceptions import (
    BadCredentials,
    BadPassword,
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
    TwoFactorRequired,
    UnknownError,
)

from bot.config import settings
from bot.db.engine import async_session
from bot.db.models import ActivityLog, AdvancedInstagramSession
from bot.services.hikerapi import hiker_client
from bot.time_utils import utc_now

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _safe_provider_error_type(exc: ClientError) -> str:
    raw = str(getattr(exc, "error_type", "") or "").strip().lower()
    if not raw:
        return "missing"
    if len(raw) > 64 or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in raw
    ):
        return "other"
    return raw


def _provider_error_category(exc: ClientError) -> str:
    signal = " ".join(
        (
            str(getattr(exc, "error_type", "") or ""),
            str(getattr(exc, "message", "") or ""),
        )
    ).lower()
    if "two_factor" in signal or "verification_code" in signal:
        return "two_factor"
    if "challenge" in signal or "checkpoint" in signal:
        return "challenge"
    if "sentry" in signal or "proxy" in signal or "ip_address" in signal:
        return "proxy"
    if "rate" in signal or "wait" in signal or "throttl" in signal:
        return "rate_limited"
    if "invalid_user" in signal:
        return "invalid_user"
    if "password" in signal or "credential" in signal:
        return "bad_credentials"
    if "invalid parameter" in signal:
        return "invalid_parameters"
    return "unknown"


def _stable_login_settings(username: str) -> dict:
    """Build a repeatable pre-login device identity without storing secrets."""

    seed = hashlib.sha256(
        f"reeldrive-instagram-device:{username.lstrip('@').lower()}".encode()
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


class AdvancedInstagramError(ValueError):
    key = "advanced_connect_error"

    def __init__(self) -> None:
        super().__init__(self.key)


class AdvancedConnectRequired(AdvancedInstagramError):
    key = "advanced_connect_required"


class AdvancedSessionExpired(AdvancedInstagramError):
    key = "advanced_session_expired"


class AdvancedPrivateAccessDenied(AdvancedInstagramError):
    key = "advanced_private_access_denied"


class AdvancedTwoFactorRequired(AdvancedInstagramError):
    key = "advanced_two_factor_required"


class AdvancedChallengeRequired(AdvancedInstagramError):
    key = "advanced_challenge_required"


class AdvancedBadCredentials(AdvancedInstagramError):
    key = "advanced_bad_credentials"


class AdvancedInvalidUser(AdvancedInstagramError):
    key = "advanced_invalid_user"


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
            initial_settings = _stable_login_settings(username)
        client = Client(
            settings=initial_settings or {},
            proxy=self.proxy or None,
            delay_range=[1, 3],
            request_timeout=10,
        )
        return client

    def _login_sync(
        self, username: str, password: str, verification_code: str
    ) -> tuple[Client, str, str]:
        client = self._new_client(username=username)
        try:
            logged_in = client.login(
                username,
                password,
                verification_code=verification_code.strip(),
            )
            if not logged_in:
                raise AdvancedInstagramError()
        except TwoFactorRequired as exc:
            raise AdvancedTwoFactorRequired() from exc
        except BadPassword as exc:
            # Instagram also returns ``bad_password`` when the datacenter IP
            # is blacklisted. Log only the class; never log its response text.
            logger.warning("Advanced Instagram login rejected error_type=BadPassword")
            raise AdvancedBadCredentials() from exc
        except BadCredentials as exc:
            raise AdvancedBadCredentials() from exc
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
        except UnknownError as exc:
            category = _provider_error_category(exc)
            response = getattr(client, "last_response", None)
            logger.warning(
                "Advanced Instagram login rejected error_type=UnknownError "
                "provider_error_type=%s category=%s http_status=%s",
                _safe_provider_error_type(exc),
                category,
                getattr(response, "status_code", "unknown"),
            )
            if category == "two_factor":
                raise AdvancedTwoFactorRequired() from exc
            if category == "challenge":
                raise AdvancedChallengeRequired() from exc
            if category == "proxy":
                raise AdvancedProxyRequired() from exc
            if category == "rate_limited":
                raise AdvancedRateLimited() from exc
            if category == "bad_credentials":
                raise AdvancedBadCredentials() from exc
            if category == "invalid_user":
                raise AdvancedInvalidUser() from exc
            raise AdvancedInstagramError() from exc
        except ClientError as exc:
            # Log only the exception class. Instagram response messages may
            # contain account details and must not enter production logs.
            logger.warning(
                "Advanced Instagram login rejected error_type=%s",
                type(exc).__name__,
            )
            raise AdvancedInstagramError() from exc
        finally:
            # instagrapi keeps the supplied password on the Client instance;
            # it is never needed after login and must not enter the cache.
            client.password = None

        account_username = str(client.username or username).lstrip("@").lower()
        account_id = str(client.user_id or "")
        if not account_id:
            raise AdvancedInstagramError()
        return client, account_username, account_id

    async def connect(
        self,
        telegram_id: int,
        username: str,
        password: str,
        verification_code: str = "",
    ) -> AdvancedSessionInfo:
        if not self.ready:
            raise AdvancedFeatureDisabled()
        handle = hiker_client.normalize_username(username)

        async with self._lock(telegram_id):
            client, account_username, account_id = await asyncio.to_thread(
                self._login_sync,
                handle,
                password,
                verification_code,
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
                "Advanced Instagram session connected telegram=%s username=@%s",
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
        client = self._new_client(stored)
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
            client = self._clients.pop(telegram_id, None)
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
            if client:
                try:
                    await asyncio.to_thread(client.logout)
                except Exception:  # noqa: BLE001 - remote logout is best-effort
                    logger.info(
                        "Instagram logout failed after local session deletion telegram=%s",
                        telegram_id,
                    )
            return True


advanced_instagram = AdvancedInstagramService()

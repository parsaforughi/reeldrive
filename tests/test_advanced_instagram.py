import hashlib
import hmac
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from urllib.parse import urlencode

from instagrapi.exceptions import LoginRequired

from bot.config import settings
from bot.services import following
from bot.services.advanced_instagram import (
    AdvancedFeatureDisabled,
    AdvancedInstagramService,
    AdvancedInvalidSession,
    AdvancedPrivateAccessDenied,
    _normalize_sessionid,
    _stable_session_settings,
)
from bot.services.hikerapi import HikerNotFoundError, HikerPrivateAccountError
from bot.services.instagram import InstagramDownloader
from bot.webapp_auth import validate_init_data


class AdvancedSessionEncryptionTests(unittest.TestCase):
    def test_session_device_identity_is_stable_per_instagram_account(self):
        first = _stable_session_settings("12345")
        second = _stable_session_settings("12345")
        other = _stable_session_settings("67890")

        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertNotIn("12345", json.dumps(first))
        self.assertTrue(first["uuids"]["android_device_id"].startswith("android-"))

    def test_session_client_uses_proxy_friendly_timeout(self):
        service = AdvancedInstagramService()
        with patch.object(
            type(service), "proxy", new_callable=PropertyMock, return_value=""
        ):
            client = service._new_client(username="12345")

        self.assertEqual(client.request_timeout, 10)
        self.assertEqual(
            client.get_settings()["uuids"],
            _stable_session_settings("12345")["uuids"],
        )

    def test_sessionid_normalization_accepts_cookie_value_and_url_encoding(self):
        self.assertEqual(
            _normalize_sessionid("sessionid=12345%3Aabc_DEF-9"),
            ("12345:abc_DEF-9", "12345"),
        )

    def test_sessionid_normalization_rejects_cookie_injection(self):
        for value in ("", "not-a-session", "12345:abc; csrftoken=bad", "12345:abc\nX"):
            with self.subTest(value=value), self.assertRaises(AdvancedInvalidSession):
                _normalize_sessionid(value)

    def test_sessionid_resolves_account_without_username_or_password(self):
        service = AdvancedInstagramService()
        client = MagicMock()
        client.settings = {}
        client.cookie_dict = {}
        client.account_info.return_value = SimpleNamespace(
            username="Resolved_User", pk=12345
        )

        with patch.object(service, "_new_client", return_value=client):
            result_client, username, account_id = service._session_client_sync(
                "12345%3Asecret-token"
            )

        self.assertIs(result_client, client)
        self.assertEqual(username, "resolved_user")
        self.assertEqual(account_id, "12345")
        client.login.assert_not_called()
        client.init.assert_called_once()
        self.assertEqual(client.settings["cookies"]["sessionid"], "12345:secret-token")
        self.assertEqual(client.authorization_data["ds_user_id"], "12345")

    def test_expired_sessionid_is_rejected_without_exposing_cookie(self):
        service = AdvancedInstagramService()
        client = MagicMock()
        client.settings = {}
        client.cookie_dict = {}
        client.account_info.side_effect = LoginRequired("12345:secret-token")

        with (
            patch.object(service, "_new_client", return_value=client),
            self.assertRaises(AdvancedInvalidSession) as raised,
        ):
            service._session_client_sync("12345:secret-token")

        self.assertNotIn("secret-token", str(raised.exception))

    def test_short_encryption_key_keeps_feature_disabled(self):
        service = AdvancedInstagramService()
        with patch.object(settings, "instagram_session_encryption_key", "too-short"):
            self.assertFalse(service.ready)
            with self.assertRaises(AdvancedFeatureDisabled):
                service._cipher()

    def test_session_settings_round_trip_and_tamper_detection(self):
        service = AdvancedInstagramService()
        payload = {
            "authorization_data": {"sessionid": "secret-session"},
            "uuids": {"device_id": "device-1"},
        }
        with patch.object(
            settings,
            "instagram_session_encryption_key",
            "unit-test-key-with-at-least-32-characters",
        ):
            token = service._encrypt_settings(payload)
            self.assertNotIn("secret-session", token)
            self.assertEqual(service._decrypt_settings(token), payload)
            with self.assertRaises(ValueError):
                service._decrypt_settings(
                    token[:-1] + ("A" if token[-1] != "A" else "B")
                )

    def test_private_target_requires_accepted_follow(self):
        service = AdvancedInstagramService()
        client = MagicMock()
        client.user_friendship_v1.return_value = SimpleNamespace(following=False)
        row = SimpleNamespace(instagram_user_id="10")
        target = SimpleNamespace(pk="20", is_private=True)

        with self.assertRaises(AdvancedPrivateAccessDenied):
            service._ensure_private_access(client, row, target)

        client.user_friendship_v1.return_value = SimpleNamespace(following=True)
        service._ensure_private_access(client, row, target)


class AdvancedStoredSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_encrypted_settings_are_restored_after_worker_restart(self):
        service = AdvancedInstagramService()
        row = SimpleNamespace(
            instagram_username="owner", encrypted_settings="encrypted-token"
        )
        stored = {"cookies": {"sessionid": "12345:secret-token"}}
        restored_client = MagicMock()

        with (
            patch.object(
                type(service), "ready", new_callable=PropertyMock, return_value=True
            ),
            patch.object(service, "_session_row", new=AsyncMock(return_value=row)),
            patch.object(service, "_decrypt_settings", return_value=stored),
            patch.object(service, "_new_client", return_value=restored_client) as new_client,
        ):
            client, returned_row = await service._client_for(101)

        self.assertIs(client, restored_client)
        self.assertIs(returned_row, row)
        new_client.assert_called_once_with(stored_settings=stored)

    async def test_follow_sets_are_read_from_requested_private_target(self):
        service = AdvancedInstagramService()
        target = SimpleNamespace(pk=222, is_private=True)
        row = SimpleNamespace(instagram_user_id="111")
        client = MagicMock()
        client.user_info_by_username_v1.return_value = target
        client.user_friendship_v1.return_value = SimpleNamespace(following=True)
        client.user_following.return_value = {
            1: SimpleNamespace(
                username="following_one",
                full_name="",
                is_private=False,
                is_verified=False,
            )
        }
        client.user_followers.return_value = {
            2: SimpleNamespace(
                username="follower_one",
                full_name="",
                is_private=False,
                is_verified=False,
            )
        }

        async def run(_telegram_id, operation):
            return operation(client, row)

        with patch.object(service, "_run", side_effect=run):
            following_items, follower_items = await service.fetch_follow_sets(
                101, "private_target", 50
            )

        client.user_info_by_username_v1.assert_called_once_with("private_target")
        client.user_friendship_v1.assert_called_once_with("222")
        client.user_following.assert_called_once_with(
            "222", use_cache=False, amount=50
        )
        client.user_followers.assert_called_once_with(
            "222", use_cache=False, amount=50
        )
        self.assertEqual(following_items[0]["username"], "following_one")
        self.assertEqual(follower_items[0]["username"], "follower_one")


class PrivateFollowingFallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        following._cache.clear()
        following._inflight.clear()

    async def test_private_results_are_fetched_per_viewer_and_not_shared(self):
        with (
            patch.object(
                type(following.hiker_client),
                "ready",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(
                following.hiker_client,
                "fetch_following",
                new=AsyncMock(side_effect=HikerPrivateAccountError("private")),
            ),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.fetch_following",
                new=AsyncMock(
                    side_effect=[
                        [{"username": "viewer_one_result"}],
                        [{"username": "viewer_two_result"}],
                    ]
                ),
            ) as private_fetch,
        ):
            first = await following.fetch_following("private_target", telegram_id=101)
            second = await following.fetch_following("private_target", telegram_id=202)

        self.assertEqual([u.username for u in first], ["viewer_one_result"])
        self.assertEqual([u.username for u in second], ["viewer_two_result"])
        self.assertEqual(private_fetch.await_count, 2)
        self.assertNotIn(
            ("private_target", settings.max_following_list), following._cache
        )

    async def test_private_count_uses_requesting_users_session(self):
        with (
            patch.object(
                following.hiker_client,
                "fetch_profile",
                new=AsyncMock(
                    return_value={
                        "username": "private_target",
                        "is_private": True,
                        "following_count": 999,
                    }
                ),
            ),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.fetch_following_count",
                new=AsyncMock(return_value=321),
            ) as private_count,
        ):
            result = await following.fetch_following_count(
                "private_target", telegram_id=202
            )

        self.assertEqual(result, 321)
        private_count.assert_awaited_once_with(202, "private_target")


class PrivateStoryFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_story_uses_requesting_users_session(self):
        downloader = InstagramDownloader()
        private_items = [
            {"media_type": 1, "thumbnail_url": "https://example.test/a.jpg"}
        ]
        with (
            patch.object(
                downloader,
                "_download_story_items",
                new=AsyncMock(return_value=["downloaded"]),
            ) as download_items,
            patch(
                "bot.services.instagram.hiker_client.fetch_user_stories",
                new=AsyncMock(side_effect=HikerPrivateAccountError("private")),
            ),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.has_session",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.fetch_stories",
                new=AsyncMock(return_value=private_items),
            ) as private_fetch,
        ):
            result = await downloader.get_stories("private_target", telegram_id=303)

        self.assertEqual(result, ["downloaded"])
        private_fetch.assert_awaited_once_with(303, "private_target")
        download_items.assert_awaited_once_with(private_items)

    async def test_empty_public_stories_do_not_use_private_session(self):
        downloader = InstagramDownloader()
        with (
            patch(
                "bot.services.instagram.hiker_client.fetch_user_stories",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.has_session",
                new=AsyncMock(return_value=True),
            ) as has_session,
            patch(
                "bot.services.advanced_instagram.advanced_instagram.fetch_stories",
                new=AsyncMock(),
            ) as private_fetch,
        ):
            result = await downloader.get_stories("public_target", telegram_id=303)

        self.assertEqual(result, [])
        has_session.assert_not_awaited()
        private_fetch.assert_not_awaited()

    async def test_private_story_404_is_confirmed_by_profile_before_fallback(self):
        downloader = InstagramDownloader()
        private_items = [
            {"media_type": 1, "thumbnail_url": "https://example.test/b.jpg"}
        ]
        with (
            patch.object(
                downloader,
                "_download_story_items",
                new=AsyncMock(return_value=["downloaded"]),
            ),
            patch(
                "bot.services.instagram.hiker_client.fetch_user_stories",
                new=AsyncMock(side_effect=HikerNotFoundError("not found")),
            ),
            patch(
                "bot.services.instagram.hiker_client.fetch_profile",
                new=AsyncMock(return_value={"is_private": True}),
            ) as profile_fetch,
            patch(
                "bot.services.advanced_instagram.advanced_instagram.has_session",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.fetch_stories",
                new=AsyncMock(return_value=private_items),
            ) as private_fetch,
        ):
            result = await downloader.get_stories("private_target", telegram_id=404)

        self.assertEqual(result, ["downloaded"])
        profile_fetch.assert_awaited_once_with("private_target")
        private_fetch.assert_awaited_once_with(404, "private_target")


class WebAppAuthFreshnessTests(unittest.TestCase):
    @staticmethod
    def _signed_init_data(auth_date: int) -> str:
        pairs = {
            "auth_date": str(auth_date),
            "query_id": "test-query",
            "user": json.dumps({"id": 42, "username": "tester"}, separators=(",", ":")),
        }
        check = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
        secret = hmac.new(
            b"WebAppData",
            settings.telegram_bot_token.encode(),
            hashlib.sha256,
        ).digest()
        pairs["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        return urlencode(pairs)

    def test_fresh_init_data_is_accepted(self):
        data = self._signed_init_data(int(time.time()))
        self.assertEqual(validate_init_data(data, max_age_seconds=600)["id"], 42)

    def test_expired_init_data_is_rejected(self):
        data = self._signed_init_data(int(time.time()) - 601)
        self.assertIsNone(validate_init_data(data, max_age_seconds=600))


if __name__ == "__main__":
    unittest.main()

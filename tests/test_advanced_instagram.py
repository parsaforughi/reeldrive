import hashlib
import hmac
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from urllib.parse import urlencode

from instagrapi.exceptions import TwoFactorRequired

from bot.config import settings
from bot.services import following
from bot.services.advanced_instagram import (
    AdvancedFeatureDisabled,
    AdvancedInstagramService,
    AdvancedPrivateAccessDenied,
    AdvancedTwoFactorRequired,
)
from bot.services.hikerapi import HikerNotFoundError, HikerPrivateAccountError
from bot.services.instagram import InstagramDownloader
from bot.webapp_auth import validate_init_data


class AdvancedSessionEncryptionTests(unittest.TestCase):
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

    def test_password_is_removed_from_client_after_two_factor_prompt(self):
        service = AdvancedInstagramService()
        client = MagicMock()
        client.login.side_effect = TwoFactorRequired("2FA required")
        with (
            patch.object(service, "_new_client", return_value=client),
            self.assertRaises(AdvancedTwoFactorRequired),
        ):
            service._login_sync("user", "password", "")
        self.assertIsNone(client.password)


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

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from bot.services import following
from bot.services.hikerapi import (
    HikerApiClient,
    HikerNotFoundError,
    HikerPrivateAccountError,
)
from bot.utils import parse_command, parse_username


class StubHikerClient(HikerApiClient):
    def __init__(self, responses: list[object], *, private: bool = False) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []
        self.private = private

    @property
    def ready(self) -> bool:
        return True

    async def _fetch_user(self, session, username: str) -> dict:
        self.normalize_username(username)
        return {"pk": "42", "is_private": self.private}

    async def _get(self, session, path: str, params: dict) -> object:
        self.calls.append((path, params))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def text(self) -> str:
        return json.dumps(self.payload)


class FakeRequest:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome

    async def __aenter__(self):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeSession:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, *args, **kwargs) -> FakeRequest:
        self.calls += 1
        return FakeRequest(self.outcomes.pop(0))


class HikerFollowingTests(unittest.IsolatedAsyncioTestCase):
    async def test_g2_paginates_without_fallback(self) -> None:
        client = StubHikerClient(
            [
                {
                    "response": {"users": [{"username": "one"}]},
                    "next_page_id": "page-2",
                },
                {
                    "response": {"users": [{"username": "two"}]},
                    "next_page_id": None,
                },
            ]
        )

        users = await client.fetch_following("valid.user", 10)

        self.assertEqual([user["username"] for user in users], ["one", "two"])
        self.assertEqual(
            [path for path, _ in client.calls],
            ["/g2/user/following", "/g2/user/following"],
        )
        self.assertEqual(client.calls[1][1]["page_id"], "page-2")

    async def test_private_g2_uses_forced_graphql_fallback(self) -> None:
        client = StubHikerClient(
            [
                HikerPrivateAccountError("اکانت خصوصی است / private account"),
                [[{"username": "visible"}], None],
            ]
        )

        users = await client.fetch_following("valid.user", 10)

        self.assertEqual([user["username"] for user in users], ["visible"])
        self.assertEqual(client.calls[0][0], "/g2/user/following")
        self.assertEqual(client.calls[1][0], "/gql/user/following/chunk")
        self.assertIs(client.calls[1][1]["force"], True)

    async def test_known_private_profile_does_not_call_following_endpoint(self) -> None:
        client = StubHikerClient([], private=True)

        with self.assertRaises(HikerPrivateAccountError):
            await client.fetch_following("private.user", 10)

        self.assertEqual(client.calls, [])

    async def test_network_timeout_retries_once(self) -> None:
        client = HikerApiClient()
        session = FakeSession(
            [
                asyncio.TimeoutError(),
                FakeResponse(200, {"ok": True}),
            ]
        )

        with patch("bot.services.hikerapi.asyncio.sleep", new=AsyncMock()):
            response = await client._get(session, "/test", {"id": "1"})

        self.assertEqual(response, {"ok": True})
        self.assertEqual(session.calls, 2)

    async def test_not_found_is_not_retried(self) -> None:
        client = HikerApiClient()
        session = FakeSession([FakeResponse(404, {"detail": "not found"})])

        with self.assertRaises(HikerNotFoundError):
            await client._get(session, "/test", {"id": "1"})

        self.assertEqual(session.calls, 1)

    def test_invalid_username_is_rejected_before_request(self) -> None:
        for value in ("/subscribe", "bad username", "نامعتبر", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                HikerApiClient.normalize_username(value)


class FollowingCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        following._cache.clear()
        following._inflight.clear()

    async def test_success_is_cached(self) -> None:
        provider = AsyncMock(return_value=[{"username": "cached_user"}])
        with (
            patch.object(
                type(following.hiker_client),
                "ready",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(following.hiker_client, "fetch_following", provider),
        ):
            first = await following.fetch_following("cached.page", 100)
            second = await following.fetch_following("cached.page", 100)

        self.assertEqual(first, second)
        provider.assert_awaited_once_with("cached.page", 100)

    async def test_concurrent_requests_share_one_provider_call(self) -> None:
        async def delayed_provider(username: str, limit: int) -> list[dict]:
            await asyncio.sleep(0)
            return [{"username": "shared_user"}]

        provider = AsyncMock(side_effect=delayed_provider)
        with (
            patch.object(
                type(following.hiker_client),
                "ready",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(following.hiker_client, "fetch_following", provider),
        ):
            results = await asyncio.gather(
                following.fetch_following("same.page", 100),
                following.fetch_following("same.page", 100),
            )

        self.assertEqual(results[0], results[1])
        provider.assert_awaited_once_with("same.page", 100)

    async def test_empty_results_are_not_cached(self) -> None:
        provider = AsyncMock(return_value=[])
        with (
            patch.object(
                type(following.hiker_client),
                "ready",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(following.hiker_client, "fetch_following", provider),
        ):
            await following.fetch_following("empty.page", 100)
            await following.fetch_following("empty.page", 100)

        self.assertEqual(provider.await_count, 2)


class UsernameParsingTests(unittest.TestCase):
    def test_following_command_accepts_dotted_username(self) -> None:
        parsed = parse_command("following behzad.sadeghzadeh96")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.kind, "following")
        self.assertEqual(parsed.username, "behzad.sadeghzadeh96")

    def test_invalid_following_username_is_rejected(self) -> None:
        self.assertIsNone(parse_command("following نامعتبر"))
        self.assertIsNone(parse_username("/subscribe"))


if __name__ == "__main__":
    unittest.main()

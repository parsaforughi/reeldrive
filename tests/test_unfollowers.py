import unittest
from unittest.mock import AsyncMock, patch

from bot.services.hikerapi import HikerPrivateAccountError
from bot.services.instagram import FollowUser
from bot.services.unfollowers import build_report, followers_scan_limit


class UnfollowerReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_hidden_public_follow_graph_uses_owner_session(self) -> None:
        following = [
            FollowUser(
                username="ghost", full_name="", is_private=False, is_verified=False
            ),
            FollowUser(
                username="mutual", full_name="", is_private=False, is_verified=False
            ),
        ]
        followers = [
            FollowUser(
                username="mutual", full_name="", is_private=False, is_verified=False
            ),
        ]

        with (
            patch(
                "bot.services.unfollowers.hiker_client.fetch_following",
                new=AsyncMock(side_effect=HikerPrivateAccountError("hidden")),
            ),
            patch(
                "bot.services.unfollowers._fetch_via_session",
                new=AsyncMock(return_value=(following, followers, True)),
            ) as session_fetch,
        ):
            report = await build_report(
                123,
                "public.page",
                following_count=2,
                follower_count=200,
                is_private=False,
                user_id="42",
            )

        session_fetch.assert_awaited_once_with(
            123, "public.page", 200, followers_scan_limit()
        )
        self.assertEqual(report.mutual_count, 1)
        self.assertEqual(
            [user.username for user in report.not_following_back], ["ghost"]
        )
        self.assertTrue(report.not_back_exact)


if __name__ == "__main__":
    unittest.main()

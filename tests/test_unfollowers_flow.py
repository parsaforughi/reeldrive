import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bot.handlers.commands import cmd_unfollowers
from bot.states import FollowingStates


def _message(telegram_id: int = 123) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=telegram_id),
        answer=AsyncMock(),
    )


def _state() -> SimpleNamespace:
    return SimpleNamespace(set_state=AsyncMock())


async def _translated(_uid: int, key: str, **_kwargs) -> str:
    return key


class UnfollowersGateOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_user_is_sent_to_token_purchase_before_connect(self) -> None:
        message = _message()
        state = _state()

        with (
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch("bot.handlers.commands.following_ready", return_value=True),
            patch("bot.handlers.commands.get_connection", new=AsyncMock(return_value=None)),
            patch("bot.handlers.commands.tu", side_effect=_translated),
            patch(
                "bot.services.following_access.get_credit_balance",
                new=AsyncMock(return_value=0),
            ),
        ):
            await cmd_unfollowers(message, state)

        state.set_state.assert_awaited_once_with(FollowingStates.waiting_token_count)
        message.answer.assert_awaited_once_with("unfollowers_buy_tokens_first")

    async def test_user_with_tokens_is_sent_to_basic_connect(self) -> None:
        message = _message()
        state = _state()

        with (
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch("bot.handlers.commands.following_ready", return_value=True),
            patch("bot.handlers.commands.get_connection", new=AsyncMock(return_value=None)),
            patch("bot.handlers.commands.tu", side_effect=_translated),
            patch(
                "bot.services.following_access.get_credit_balance",
                new=AsyncMock(return_value=2),
            ),
        ):
            await cmd_unfollowers(message, state)

        state.set_state.assert_not_awaited()
        message.answer.assert_awaited_once_with("help_unfollowersunfollowers_need_connect")

    async def test_missing_tokens_are_requested_before_private_session(self) -> None:
        message = _message()
        state = _state()
        connection = SimpleNamespace(
            instagram_username="private.page", status="connected"
        )

        with (
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch("bot.handlers.commands.following_ready", return_value=True),
            patch(
                "bot.handlers.commands.get_connection",
                new=AsyncMock(return_value=connection),
            ),
            patch("bot.handlers.commands.require_user_lang", new=AsyncMock(return_value="fa")),
            patch("bot.handlers.commands.tu", side_effect=_translated),
            patch(
                "bot.services.following_access.get_credit_balance",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "bot.services.following_access.is_unlocked",
                new=AsyncMock(side_effect=[False, False]),
            ),
            patch(
                "bot.services.following_access.has_access",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "bot.services.following_access.tokens_required_for_count",
                return_value=3,
            ),
            patch(
                "bot.services.unfollowers.precheck_counts",
                new=AsyncMock(return_value=(500, 500, True, "42")),
            ),
            patch("bot.services.unfollowers.token_cost_units", return_value=1000),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.has_session",
                new=AsyncMock(return_value=False),
            ) as has_session,
        ):
            await cmd_unfollowers(message, state)

        state.set_state.assert_awaited_once_with(FollowingStates.waiting_token_count)
        message.answer.assert_awaited_once_with("unfollowers_need_tokens")
        has_session.assert_not_awaited()

    async def test_private_session_is_requested_after_token_access(self) -> None:
        message = _message()
        state = _state()
        connection = SimpleNamespace(
            instagram_username="private.page", status="connected"
        )

        with (
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch("bot.handlers.commands.following_ready", return_value=True),
            patch(
                "bot.handlers.commands.get_connection",
                new=AsyncMock(return_value=connection),
            ),
            patch("bot.handlers.commands.require_user_lang", new=AsyncMock(return_value="fa")),
            patch("bot.handlers.commands.tu", side_effect=_translated),
            patch(
                "bot.services.following_access.get_credit_balance",
                new=AsyncMock(return_value=3),
            ),
            patch(
                "bot.services.following_access.is_unlocked",
                new=AsyncMock(side_effect=[False, False]),
            ),
            patch(
                "bot.services.following_access.has_access",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "bot.services.following_access.tokens_required_for_count",
                return_value=3,
            ),
            patch(
                "bot.services.unfollowers.precheck_counts",
                new=AsyncMock(return_value=(500, 500, True, "42")),
            ),
            patch("bot.services.unfollowers.token_cost_units", return_value=1000),
            patch(
                "bot.services.advanced_instagram.advanced_instagram.has_session",
                new=AsyncMock(return_value=False),
            ) as has_session,
        ):
            await cmd_unfollowers(message, state)

        state.set_state.assert_not_awaited()
        message.answer.assert_awaited_once_with("unfollowers_private_needs_advanced")
        has_session.assert_awaited_once_with(123)


if __name__ == "__main__":
    unittest.main()

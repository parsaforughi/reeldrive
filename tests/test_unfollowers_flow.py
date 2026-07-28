import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.admin import approve_unfollowers_purchase
from bot.handlers.commands import (
    _start_unfollowers_payment,
    _unfollowers_price,
    cmd_unfollowers,
    receive_unfollowers_username,
    start_unfollowers_connect,
)
from bot.states import UnfollowersStates


def _message(telegram_id: int = 123, text: str = "") -> SimpleNamespace:
    bot = SimpleNamespace(send_message=AsyncMock())
    return SimpleNamespace(
        from_user=SimpleNamespace(id=telegram_id, username="telegram_user"),
        chat=SimpleNamespace(id=telegram_id),
        text=text,
        bot=bot,
        answer=AsyncMock(),
    )


def _state() -> SimpleNamespace:
    return SimpleNamespace(
        set_state=AsyncMock(),
        update_data=AsyncMock(),
        clear=AsyncMock(),
    )


async def _translated(_uid: int, key: str, **_kwargs) -> str:
    return key


class UnfollowersGateOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_user_gets_connect_button_before_payment(self) -> None:
        message = _message()
        state = _state()
        markup = MagicMock()

        with (
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch("bot.handlers.commands.following_ready", return_value=True),
            patch("bot.handlers.commands.get_connection", new=AsyncMock(return_value=None)),
            patch("bot.handlers.commands.require_user_lang", new=AsyncMock(return_value="fa")),
            patch("bot.handlers.commands.tu", side_effect=_translated),
            patch("bot.handlers.commands.unfollowers_connect_kb", return_value=markup),
        ):
            await cmd_unfollowers(message, state)

        state.clear.assert_awaited_once()
        message.answer.assert_awaited_once_with(
            "unfollowers_connect_intro", reply_markup=markup
        )

    async def test_connect_button_then_asks_for_instagram_id(self) -> None:
        state = _state()
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            message=SimpleNamespace(edit_text=AsyncMock()),
            answer=AsyncMock(),
        )

        with patch("bot.handlers.commands.tu", side_effect=_translated):
            await start_unfollowers_connect(callback, state)

        state.set_state.assert_awaited_once_with(UnfollowersStates.waiting_username)
        callback.message.edit_text.assert_awaited_once_with(
            "unfollowers_ask_username"
        )

    async def test_quote_is_based_on_double_following(self) -> None:
        with patch(
            "bot.services.unfollowers.precheck_counts",
            new=AsyncMock(return_value=(198, 10_000, False, "42")),
        ):
            following, followers, private, user_id, units, tokens = (
                await _unfollowers_price("target.page")
            )

        self.assertEqual((following, followers), (198, 10_000))
        self.assertFalse(private)
        self.assertEqual(user_id, "42")
        self.assertEqual(units, 396)
        self.assertEqual(tokens, 1)

    async def test_entered_id_starts_exact_unfollower_payment(self) -> None:
        message = _message(text="target.page")
        state = _state()

        with (
            patch("bot.handlers.commands.require_user_lang", new=AsyncMock(return_value="fa")),
            patch(
                "bot.handlers.commands._unfollowers_price",
                new=AsyncMock(return_value=(801, 50_000, False, "42", 1602, 5)),
            ),
            patch(
                "bot.services.following_access.has_paid_access",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "bot.handlers.commands._start_unfollowers_payment",
                new=AsyncMock(),
            ) as start_payment,
        ):
            await receive_unfollowers_username(message, state)

        start_payment.assert_awaited_once_with(
            message,
            state,
            username="target.page",
            tokens_needed=5,
        )

    async def test_existing_tokens_send_connection_code(self) -> None:
        message = _message(text="target.page")
        state = _state()

        with (
            patch("bot.handlers.commands.require_user_lang", new=AsyncMock(return_value="fa")),
            patch(
                "bot.handlers.commands._unfollowers_price",
                new=AsyncMock(return_value=(198, 1000, False, "42", 396, 1)),
            ),
            patch(
                "bot.services.following_access.has_paid_access",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "bot.handlers.commands.send_connection_code",
                new=AsyncMock(),
            ) as send_code,
        ):
            await receive_unfollowers_username(message, state)

        state.clear.assert_awaited_once()
        send_code.assert_awaited_once_with(
            message.bot, message.chat.id, 123, "target.page"
        )

    async def test_payment_buys_only_the_exact_token_shortage(self) -> None:
        message = _message()
        state = _state()
        markup = MagicMock()
        translate = AsyncMock(return_value="unfollowers_token_pay_prompt")

        with (
            patch(
                "bot.services.following_access.get_credit_balance",
                new=AsyncMock(return_value=2),
            ),
            patch(
                "bot.handlers.commands.current_support_card",
                new=AsyncMock(return_value="1234"),
            ),
            patch(
                "bot.handlers.commands.current_card_holder_name",
                new=AsyncMock(return_value="Holder"),
            ),
            patch("bot.handlers.commands.token_price", return_value=30_000),
            patch("bot.handlers.commands.require_user_lang", new=AsyncMock(return_value="fa")),
            patch("bot.handlers.commands.tu", translate),
            patch("bot.handlers.commands.following_token_pay_kb", return_value=markup),
        ):
            await _start_unfollowers_payment(
                message,
                state,
                username="target.page",
                tokens_needed=5,
            )

        state.set_state.assert_awaited_once_with(
            UnfollowersStates.waiting_receipt_photo
        )
        state.update_data.assert_awaited_once_with(
            unfollowers_username="target.page",
            unfollowers_purchase_count=3,
            unfollowers_token_amount=30_000,
            unfollowers_token_card="1234",
        )
        self.assertEqual(translate.await_args.kwargs["count"], 3)
        self.assertNotIn("following", translate.await_args.kwargs)
        self.assertNotIn("doubled", translate.await_args.kwargs)
        self.assertNotIn("total_tokens", translate.await_args.kwargs)
        message.answer.assert_awaited_once_with(
            "unfollowers_token_pay_prompt", reply_markup=markup
        )


class UnfollowersApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_payment_approval_activates_tokens_and_sends_connection_code(
        self,
    ) -> None:
        bot = SimpleNamespace(send_message=AsyncMock())
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=999),
            data="unfollowers:approve:123:2:target.page",
            message=SimpleNamespace(
                caption="receipt",
                edit_caption=AsyncMock(),
            ),
            bot=bot,
            answer=AsyncMock(),
        )

        with (
            patch("bot.handlers.admin.is_admin", return_value=True),
            patch("bot.handlers.admin.grant_credits", new=AsyncMock(return_value=2)),
            patch(
                "bot.services.verification.get_connection",
                new=AsyncMock(return_value=None),
            ),
            patch("bot.handlers.admin.tu", side_effect=_translated),
            patch(
                "bot.handlers.connect.send_connection_code",
                new=AsyncMock(),
            ) as send_code,
        ):
            await approve_unfollowers_purchase(callback)

        bot.send_message.assert_awaited_once_with(123, "unfollowers_payment_approved")
        send_code.assert_awaited_once_with(bot, 123, 123, "target.page")


if __name__ == "__main__":
    unittest.main()

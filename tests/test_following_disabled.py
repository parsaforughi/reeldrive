"""Following lookup and following-token purchases stay closed while the switch is on."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from bot.config import FOLLOWING_SERVICE_DISABLED, FOLLOWING_SERVICE_DISABLED_MESSAGE
from bot.handlers.admin import approve_token_purchase
from bot.handlers.commands import (
    cmd_following,
    cmd_unfollowers,
    copy_payment_value,
    receive_following_username,
    receive_token_count,
    receive_token_receipt,
    receive_token_receipt_invalid,
    recheck_following_join,
)
from bot.handlers.following_shared import start_following_lookup
from bot.handlers.messages import handle_text
from bot.states import FollowingStates, UnfollowersStates

EXPECTED_MESSAGE = (
    "کاربر گرامی\n"
    "سرویس فالویینگ فعلا به دلیل محدودیت‌های اعمال شده از سمت متا در دسترس نیست\n"
    "\n"
    "به محض برطرف شدن محدودیت‌ها سرویس مجددا فعال خواهد شد"
)


def _message(telegram_id: int = 123, text: str = "", *, photo: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=telegram_id, username="telegram_user"),
        chat=SimpleNamespace(id=telegram_id),
        text=text,
        photo=[SimpleNamespace(file_id="receipt")] if photo else None,
        bot=SimpleNamespace(send_message=AsyncMock()),
        answer=AsyncMock(),
    )


def _state(current: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        set_state=AsyncMock(),
        update_data=AsyncMock(),
        clear=AsyncMock(),
        get_state=AsyncMock(return_value=current),
        get_data=AsyncMock(return_value={}),
    )


def _callback(data: str, *, state_name: str | None = None) -> tuple[SimpleNamespace, SimpleNamespace]:
    callback = SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=123),
        bot=SimpleNamespace(),
        message=SimpleNamespace(answer=AsyncMock(), edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    return callback, _state(state_name)


class FollowingDisabledMessageTests(unittest.TestCase):
    def test_toggle_and_exact_message(self) -> None:
        self.assertTrue(FOLLOWING_SERVICE_DISABLED)
        self.assertEqual(FOLLOWING_SERVICE_DISABLED_MESSAGE, EXPECTED_MESSAGE)


class FollowingDisabledHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_following_command_replies_with_notice_and_does_not_start(self) -> None:
        message = _message(text="/following")
        state = _state()

        with patch(
            "bot.handlers.commands.guard_channels", new=AsyncMock(return_value=True)
        ) as guard:
            await cmd_following(message, state)

        guard.assert_not_awaited()
        state.set_state.assert_not_awaited()
        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_typed_username_does_not_run_lookup(self) -> None:
        message = _message(text="some.page")
        state = _state(FollowingStates.waiting_username.state)

        with patch(
            "bot.handlers.commands.start_following_lookup", new=AsyncMock()
        ) as lookup:
            await receive_following_username(message, state)

        lookup.assert_not_awaited()
        state.clear.assert_awaited()
        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_recheck_button_does_not_continue_lookup(self) -> None:
        callback, state = _callback("following:recheck")

        with patch(
            "bot.handlers.commands.missing_channels", new=AsyncMock(return_value=[])
        ) as missing:
            await recheck_following_join(callback, state)

        missing.assert_not_awaited()
        state.set_state.assert_not_awaited()
        callback.message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)
        callback.answer.assert_awaited_once_with()

    async def test_free_text_following_command_does_not_lookup(self) -> None:
        message = _message(text="following some.page")
        state = _state()

        with (
            patch(
                "bot.handlers.messages.require_user_lang",
                new=AsyncMock(return_value="fa"),
            ),
            patch(
                "bot.handlers.messages.guard_channels", new=AsyncMock(return_value=True)
            ) as guard,
            patch(
                "bot.handlers.messages.start_following_lookup", new=AsyncMock()
            ) as lookup,
        ):
            await handle_text(message, state)

        guard.assert_not_awaited()
        lookup.assert_not_awaited()
        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_persian_alias_is_blocked_too(self) -> None:
        message = _message(text="فالووینگ some.page")
        state = _state()

        with patch(
            "bot.handlers.messages.require_user_lang",
            new=AsyncMock(return_value="fa"),
        ):
            await handle_text(message, state)

        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_lookup_helper_does_not_fetch_or_quote_tokens(self) -> None:
        message = _message()
        state = _state()

        with (
            patch(
                "bot.handlers.following_shared.fetch_following", new=AsyncMock()
            ) as fetch_list,
            patch(
                "bot.handlers.following_shared.fetch_following_count", new=AsyncMock()
            ) as fetch_count,
            patch(
                "bot.handlers.following_shared.is_unlocked", new=AsyncMock()
            ) as unlocked,
        ):
            shown = await start_following_lookup(message, state, "some.page")

        self.assertFalse(shown)
        fetch_list.assert_not_awaited()
        fetch_count.assert_not_awaited()
        unlocked.assert_not_awaited()
        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_token_count_does_not_issue_a_card(self) -> None:
        message = _message(text="2")
        state = _state(FollowingStates.waiting_token_count.state)

        with patch(
            "bot.handlers.commands.current_support_card",
            new=AsyncMock(return_value="6219861462108209"),
        ) as card:
            await receive_token_count(message, state)

        card.assert_not_awaited()
        state.set_state.assert_not_awaited()
        state.update_data.assert_not_awaited()
        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)
        self.assertNotIn("6219861462108209", str(message.answer.await_args))

    async def test_receipt_photo_is_not_accepted(self) -> None:
        message = _message(photo=True)
        state = _state(FollowingStates.waiting_receipt_photo.state)

        with patch(
            "bot.handlers.commands.send_receipt_to_admins", new=AsyncMock()
        ) as send:
            await receive_token_receipt(message, state)

        send.assert_not_awaited()
        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_non_photo_receipt_step_shows_notice(self) -> None:
        message = _message(text="paid")
        state = _state(FollowingStates.waiting_receipt_photo.state)

        await receive_token_receipt_invalid(message, state)

        message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)

    async def test_following_copy_button_does_not_reveal_card(self) -> None:
        callback, state = _callback(
            "following:copy:card:6219861462108209",
            state_name=FollowingStates.waiting_receipt_photo.state,
        )

        await copy_payment_value(callback, state)

        callback.message.answer.assert_awaited_once_with(EXPECTED_MESSAGE)
        callback.answer.assert_awaited_once_with()
        self.assertNotIn("6219861462108209", str(callback.answer.await_args))

    async def test_switch_off_still_asks_for_a_username(self) -> None:
        message = _message(text="/following")
        state = _state()
        markup = MagicMock()

        with (
            patch("bot.config.FOLLOWING_SERVICE_DISABLED", False),
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "bot.handlers.commands.tu",
                new=AsyncMock(return_value="following_ask_username"),
            ),
            patch(
                "bot.handlers.commands.following_cancel_kb",
                new=AsyncMock(return_value=markup),
            ),
        ):
            await cmd_following(message, state)

        state.set_state.assert_awaited_once_with(FollowingStates.waiting_username)
        message.answer.assert_awaited_once_with(
            "following_ask_username", reply_markup=markup
        )

    async def test_switch_off_token_count_still_issues_card(self) -> None:
        message = _message(text="2")
        state = _state(FollowingStates.waiting_token_count.state)
        markup = MagicMock()

        with (
            patch("bot.config.FOLLOWING_SERVICE_DISABLED", False),
            patch(
                "bot.handlers.commands.require_user_lang",
                new=AsyncMock(return_value="fa"),
            ),
            patch(
                "bot.handlers.commands.current_support_card",
                new=AsyncMock(return_value="6219861462108209"),
            ) as card,
            patch(
                "bot.handlers.commands.current_card_holder_name",
                new=AsyncMock(return_value="Holder"),
            ),
            patch(
                "bot.handlers.commands.tu",
                new=AsyncMock(return_value="following_token_pay_prompt"),
            ),
            patch(
                "bot.handlers.commands.following_token_pay_kb", return_value=markup
            ),
        ):
            await receive_token_count(message, state)

        card.assert_awaited_once()
        state.set_state.assert_awaited_once_with(FollowingStates.waiting_receipt_photo)
        self.assertEqual(
            state.update_data.await_args.kwargs["following_token_card"],
            "6219861462108209",
        )
        message.answer.assert_awaited_once_with(
            "following_token_pay_prompt", reply_markup=markup
        )


class UnfollowersUnaffectedTests(unittest.IsolatedAsyncioTestCase):
    async def test_unfollowers_command_still_starts(self) -> None:
        message = _message()
        state = _state()
        markup = MagicMock()

        with (
            patch(
                "bot.handlers.commands.guard_channels",
                new=AsyncMock(return_value=True),
            ),
            patch("bot.handlers.commands.following_ready", return_value=True),
            patch(
                "bot.handlers.commands.get_connection",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "bot.handlers.commands.require_user_lang",
                new=AsyncMock(return_value="fa"),
            ),
            patch("bot.handlers.commands.tu", new=AsyncMock(return_value="unfollowers_connect_intro")),
            patch("bot.handlers.commands.unfollowers_connect_kb", return_value=markup),
        ):
            await cmd_unfollowers(message, state)

        state.clear.assert_awaited_once()
        message.answer.assert_awaited_once_with(
            "unfollowers_connect_intro", reply_markup=markup
        )
        self.assertNotEqual(message.answer.await_args.args[0], EXPECTED_MESSAGE)

    async def test_unfollowers_copy_button_still_shows_card(self) -> None:
        callback, state = _callback(
            "following:copy:card:6219861462108209",
            state_name=UnfollowersStates.waiting_receipt_photo.state,
        )

        await copy_payment_value(callback, state)

        callback.answer.assert_awaited_once_with(
            text="6219861462108209", show_alert=True
        )
        callback.message.answer.assert_not_awaited()
        state.clear.assert_not_awaited()

    async def test_other_text_commands_are_not_replaced_by_the_notice(self) -> None:
        message = _message(text="story some.page")
        state = _state()

        with (
            patch(
                "bot.handlers.messages.require_user_lang",
                new=AsyncMock(return_value="fa"),
            ),
            patch(
                "bot.services.hikerapi.HikerApiClient.ready",
                new_callable=PropertyMock,
                return_value=False,
            ),
            patch(
                "bot.handlers.messages.tu",
                new=AsyncMock(return_value="error_service_ig"),
            ),
        ):
            await handle_text(message, state)

        message.answer.assert_awaited_once_with("error_service_ig")

    async def test_pending_admin_approval_still_grants_tokens(self) -> None:
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=999),
            data="following:approve:123:2",
            message=SimpleNamespace(
                photo=[SimpleNamespace(file_id="receipt")],
                caption="receipt",
                edit_caption=AsyncMock(),
            ),
            bot=SimpleNamespace(send_message=AsyncMock()),
            answer=AsyncMock(),
        )

        with (
            patch("bot.handlers.admin.is_admin", return_value=True),
            patch(
                "bot.handlers.admin.grant_credits", new=AsyncMock(return_value=7)
            ) as grant,
            patch(
                "bot.handlers.admin.tu",
                new=AsyncMock(return_value="following_tokens_granted_notify"),
            ),
        ):
            await approve_token_purchase(callback)

        grant.assert_awaited_once_with(123, 2, granted_by=999)
        callback.answer.assert_awaited_once_with("تأیید شد")
        callback.message.edit_caption.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards import connect_cancel_kb
from bot.services.verification import disconnect, get_connection, start_verification
from bot.states import ConnectStates

router = Router()


@router.message(Command("connect"))
async def cmd_connect(message: Message, state: FSMContext) -> None:
    await state.set_state(ConnectStates.waiting_username)
    await message.answer(
        "یوزرنیم پیج اینستاگرامت را بفرست (مثلاً <code>myshop</code>):\n\n"
        "Send your Instagram page username:",
        reply_markup=connect_cancel_kb(),
    )


@router.callback_query(F.data == "connect:cancel")
async def cancel_connect(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("لغو شد. / Cancelled.")
    await callback.answer()


@router.message(StateFilter(ConnectStates.waiting_username))
async def receive_username(message: Message, state: FSMContext) -> None:
    username = (message.text or "").strip().lstrip("@").lower()
    if not username or " " in username or len(username) > 30:
        await message.answer("یوزرنیم نامعتبر است.")
        return

    code = await start_verification(message.from_user.id, username)
    bridge = settings.bridge_ig_handle
    ttl = settings.verification_code_ttl_minutes

    await state.clear()
    await message.answer(
        f"✅ پیج: <b>@{username}</b>\n\n"
        f"کد تأیید: <code>{code}</code>\n\n"
        f"این کد را در <b>دایرکت اینستاگرام</b> به {bridge} بفرست.\n"
        f"⏱ تا {ttl} دقیقه معتبر است.\n\n"
        f"بعد از چند دقیقه پیام «متصل شد» می‌گیری.",
    )


@router.message(Command("disconnect"))
async def cmd_disconnect(message: Message) -> None:
    ok = await disconnect(message.from_user.id)
    if ok:
        await message.answer("اتصال قطع شد.\nDisconnected.")
    else:
        await message.answer("پیجی متصل نبود.\nNo connection found.")

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.i18n import tu
from bot.keyboards import connect_cancel_kb
from bot.services.verification import disconnect, start_verification
from bot.states import ConnectStates

router = Router()


@router.message(Command("connect"))
async def cmd_connect(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    await state.set_state(ConnectStates.waiting_username)
    await message.answer(
        await tu(uid, "connect_ask_username"),
        reply_markup=await connect_cancel_kb(uid),
    )


@router.callback_query(F.data == "connect:cancel")
async def cancel_connect(callback: CallbackQuery, state: FSMContext) -> None:
    uid = callback.from_user.id
    await state.clear()
    await callback.message.edit_text(await tu(uid, "connect_cancel"))
    await callback.answer()


@router.message(StateFilter(ConnectStates.waiting_username))
async def receive_username(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    username = (message.text or "").strip().lstrip("@").lower()
    if not username or " " in username or len(username) > 30:
        await message.answer(await tu(uid, "connect_invalid_username"))
        return

    code = await start_verification(uid, username)
    bridge = settings.bridge_ig_handle
    ttl = settings.verification_code_ttl_minutes

    await state.clear()
    await message.answer(
        await tu(
            uid,
            "connect_code",
            username=username,
            code=code,
            bridge=bridge,
            ttl=ttl,
        )
    )


@router.message(Command("disconnect"))
async def cmd_disconnect(message: Message) -> None:
    uid = message.from_user.id
    ok = await disconnect(uid)
    if ok:
        await message.answer(await tu(uid, "connect_disconnected"))
    else:
        await message.answer(await tu(uid, "connect_not_found"))

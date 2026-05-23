from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.handlers.commands import (
    cmd_directdownload,
    cmd_help,
    cmd_myinstagram,
    cmd_start,
)
from bot.handlers.connect import cmd_connect
from bot.handlers.status_helpers import build_myinstagram_text
from bot.keyboards import myinstagram_kb
from bot.services.verification import disconnect

router = Router()


@router.callback_query(F.data == "menu:start")
async def cb_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cmd_start(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery) -> None:
    await cmd_help(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu:directdownload")
async def cb_directdownload(callback: CallbackQuery) -> None:
    await cmd_directdownload(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu:myinstagram")
async def cb_myinstagram(callback: CallbackQuery) -> None:
    await cmd_myinstagram(callback.message)
    await callback.answer()


@router.callback_query(F.data == "ig:connect")
async def cb_connect(callback: CallbackQuery, state: FSMContext) -> None:
    await cmd_connect(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "ig:disconnect")
async def cb_disconnect(callback: CallbackQuery) -> None:
    ok = await disconnect(callback.from_user.id)
    text = await build_myinstagram_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=myinstagram_kb(False))
    await callback.answer("قطع شد." if ok else "متصل نبود.")

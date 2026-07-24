from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.handlers.connect_hints import connected_usage_hint
from bot.i18n import require_user_lang, t, tu
from bot.keyboards import advanced_connect_kb, connect_cancel_kb
from bot.services.bio_verification import verify_pending_via_bio
from bot.services.client_pool import client_pool
from bot.services.verification import disconnect, get_connection, start_verification
from bot.states import ConnectStates
from bot.utils import parse_media_url, parse_username

router = Router()


@router.message(Command("advancedconnect"))
async def cmd_advanced_connect(message: Message) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    await message.answer(
        await tu(uid, "advanced_connect_intro"),
        reply_markup=advanced_connect_kb(lang),
    )


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


@router.message(StateFilter(ConnectStates.waiting_username), ~F.text.startswith("/"))
async def receive_username(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    text = (message.text or "").strip()
    if parse_media_url(text):
        await state.clear()
        from bot.handlers.messages import download_from_text

        await download_from_text(message, text, state)
        return

    username = parse_username(text)
    if not username:
        await message.answer(await tu(uid, "connect_invalid_username"))
        return

    code = await start_verification(uid, username)
    bridge = settings.bridge_ig_handle
    ttl = settings.verification_code_ttl_minutes

    extra = ""
    if not client_pool.bridge_ready:
        lang = await require_user_lang(uid)
        extra = "\n" + t("connect_bridge_offline", lang, bridge=bridge)

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
        + extra
    )


@router.message(Command("verify"))
async def cmd_verify(message: Message) -> None:
    uid = message.from_user.id
    lang = await require_user_lang(uid)
    conn = await get_connection(uid)

    ok, reason = await verify_pending_via_bio(uid)
    conn_after = await get_connection(uid)
    if ok and conn_after:
        await message.answer(
            t("verify_ok", lang, username=conn_after.instagram_username)
        )
        await message.answer(
            connected_usage_hint(lang, username=conn_after.instagram_username)
        )
        return

    if reason == "no_pending":
        await message.answer(t("verify_no_pending", lang))
        return
    if reason == "private":
        await message.answer(t("verify_private", lang))
        return
    if reason == "hikerapi":
        await message.answer(t("verify_hikerapi", lang))
        return
    if reason == "not_in_bio" and conn:
        await message.answer(
            t(
                "verify_not_in_bio",
                lang,
                code=conn.verification_code,
                username=conn.instagram_username,
            )
        )
        return

    await message.answer(t("verify_not_in_bio", lang, code="?", username="?"))


@router.message(Command("disconnect"))
async def cmd_disconnect(message: Message) -> None:
    uid = message.from_user.id
    ok = await disconnect(uid)
    if ok:
        await message.answer(await tu(uid, "connect_disconnected"))
    else:
        await message.answer(await tu(uid, "connect_not_found"))

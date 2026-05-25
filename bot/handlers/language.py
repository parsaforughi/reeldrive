from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.i18n import get_user_lang, set_user_lang, t, tu
from bot.keyboards import language_kb

router = Router()


@router.callback_query(F.data.startswith("lang:"))
async def pick_language(callback: CallbackQuery) -> None:
    code = (callback.data or "").split(":", 1)[-1]
    lang = await set_user_lang(callback.from_user.id, code)
    await callback.answer()
    confirm = t(f"lang_set_{lang}", lang)
    await callback.message.edit_text(
        f"{confirm}\n\n{t('start', lang)}",
        reply_markup=None,
    )


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    lang = await get_user_lang(message.from_user.id) or "fa"
    await message.answer(t("choose_language", lang), reply_markup=language_kb())

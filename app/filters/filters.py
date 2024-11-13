from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.lexicon.lexicon import LEXICON_COMMANDS


class IsDigitCallbackData(BaseFilter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        return isinstance(callback.data, str) and callback.data.isdigit()


class IsDelBookmarkCallbackData(BaseFilter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        return isinstance(callback.data, str) and 'del'         \
            in callback.data and callback.data[:-3].isdigit()


def menu_commands_filter(message: Message) -> bool:
    return message.text not in LEXICON_COMMANDS.keys()
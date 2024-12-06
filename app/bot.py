from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import settings
from app.handlers import other_handlers, done_handlers, forward_handlers

storage = MemoryStorage()  # Подключаем RedisStorage к боту

bot = Bot(token=settings.bot_token, parse_mode='HTML')
dp = Dispatcher(bot=bot, storage=storage)

# dp.update.middleware(ThrottlingMiddleware(rate_limit=2.0))

# Регистрируем обработчики

dp.include_router(done_handlers.router)
dp.include_router(forward_handlers.router)
dp.include_router(other_handlers.router)

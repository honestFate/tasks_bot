import uvicorn
from fastapi import FastAPI, Request
import logging
from aiogram import types
from app.bot import bot, dp
from app.config import settings, logger
from contextlib import asynccontextmanager
import sys


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Log uncaught exceptions and forward them to telegram handler."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = log_unhandled_exception

from app.keyboards.main_menu import set_main_menu
from app.database.database import close_http_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await set_main_menu(bot)
        await bot.set_webhook(settings.webhook_url, allowed_updates=["message", "callback_query"])
        logger.info("Webhook установлен успешно")
        yield
    except Exception as e:
        logger.exception("Ошибка при запуске приложения: %s", e)
        raise
    finally:
        try:
            await bot.delete_webhook()
            logger.info("Webhook удален")
        except Exception as e:
            logger.exception("Ошибка при удалении webhook: %s", e)
        
        try:
            await bot.session.close()
            logger.info("Bot session закрыт")
        except Exception as e:
            logger.exception("Ошибка при закрытии bot session: %s", e)
        
        try:
            await dp.storage.close()
            logger.info("Storage закрыт")
        except Exception as e:
            logger.exception("Ошибка при закрытии storage: %s", e)
        
        try:
            await close_http_client()
            logger.info("HTTP клиент закрыт")
        except Exception as e:
            logger.exception("Ошибка при закрытии HTTP клиента: %s", e)

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.post(settings.webhook_path)
async def webhook(request: Request):
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_webhook_update(bot=bot, update=update)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Ошибка при обработке webhook: %s", e)
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health_check():
    """Простая проверка состояния приложения"""
    return {"status": "healthy", "service": "telegram_bot"}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

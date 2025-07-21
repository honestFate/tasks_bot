import uvicorn
from fastapi import FastAPI, Request
from aiogram import types
from app.bot import bot, dp
from app.config import settings
from contextlib import asynccontextmanager

from app.keyboards.main_menu import set_main_menu
from app.database.database import close_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await set_main_menu(bot)
        await bot.set_webhook(settings.webhook_url, allowed_updates=["message", "callback_query"])
        print("Webhook установлен успешно")
        yield
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        raise
    finally:
        try:
            await bot.delete_webhook()
            print("Webhook удален")
        except Exception as e:
            print(f"Ошибка при удалении webhook: {e}")
        
        try:
            await bot.session.close()
            print("Bot session закрыт")
        except Exception as e:
            print(f"Ошибка при закрытии bot session: {e}")
        
        try:
            await dp.storage.close()
            print("Storage закрыт")
        except Exception as e:
            print(f"Ошибка при закрытии storage: {e}")
        
        try:
            await close_http_client()
            print("HTTP клиент закрыт")
        except Exception as e:
            print(f"Ошибка при закрытии HTTP клиента: {e}")

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.post(settings.webhook_path)
async def webhook(request: Request):
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_webhook_update(bot=bot, update=update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Ошибка при обработке webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health_check():
    """Простая проверка состояния приложения"""
    return {"status": "healthy", "service": "telegram_bot"}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
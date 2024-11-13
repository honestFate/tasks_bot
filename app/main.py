import uvicorn
from fastapi import FastAPI, Request
from aiogram import types
from app.bot import bot, dp
from app.config import settings
from contextlib import asynccontextmanager

from app.keyboards.main_menu import set_main_menu


# from app.services.queue import send_to_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код при старте приложения
    await set_main_menu(bot)
    await bot.set_webhook(settings.webhook_url, allowed_updates=["message", "callback_query"])
    yield
    # Код при завершении приложения
    await bot.delete_webhook()
    await bot.session.close()
    await dp.storage.close()

app = FastAPI(lifespan=lifespan)


@app.post(settings.webhook_path)
async def webhook(request: Request):
    update_data = await request.json()
    update = types.Update(**update_data)  # Преобразуем JSON в объект Update
    await dp.feed_webhook_update(bot=bot, update=update)
    return {"status": "ok"}


if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)

from aiogram import BaseMiddleware
from aiogram.types import Message
import asyncio

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        super().__init__()
        self.rate_limit = rate_limit
        self.rate_limit_dict = {}

    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user_id = event.from_user.id
            if user_id in self.rate_limit_dict:
                last_time = self.rate_limit_dict[user_id]
                if asyncio.get_event_loop().time() - last_time < self.rate_limit:
                    return  # Пропускаем сообщение, если лимит превышен
            self.rate_limit_dict[user_id] = asyncio.get_event_loop().time()
        return await handler(event, data)
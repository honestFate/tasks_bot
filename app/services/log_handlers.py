import logging
import asyncio
import httpx
from app.config import settings


class TelegramLogsHandler(logging.Handler):
    def emit(self, record):
        """Отправка логов в Telegram асинхронно"""
        try:
            update_id = settings.admin_id
            log_entry = self.format(record)
            
            if len(log_entry) > 4000:
                log_entry = log_entry[:4000] + "... (обрезано)"
            
            asyncio.create_task(self._send_log_async(update_id, log_entry))
        except Exception as e:
            print(f"Ошибка в TelegramLogsHandler: {e}")

    async def _send_log_async(self, chat_id: str, message: str):
        """Асинхронная отправка сообщения в Telegram"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f'https://api.telegram.org/bot{settings.logs_bot}/sendMessage'
                data = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                
                response = await client.post(url, data=data)
                
                if response.status_code != 200:
                    print(f"Ошибка отправки лога в Telegram: {response.status_code} - {response.text}")
                    
        except asyncio.TimeoutError:
            print("Таймаут при отправке лога в Telegram")
        except Exception as e:
            print(f"Неожиданная ошибка при отправке лога в Telegram: {e}")


class SafeTelegramLogsHandler(logging.Handler):
    """Безопасная версия обработчика логов для Telegram (синхронная)"""
    
    def emit(self, record):
        """Синхронная отправка логов с обработкой ошибок"""
        try:
            update_id = settings.admin_id
            log_entry = self.format(record)
            
            if len(log_entry) > 4000:
                log_entry = log_entry[:4000] + "... (обрезано)"
            
            with httpx.Client(timeout=5.0) as client:
                url = f'https://api.telegram.org/bot{settings.logs_bot}/sendMessage'
                data = {
                    'chat_id': update_id,
                    'text': log_entry,
                    'parse_mode': 'HTML'
                }
                
                response = client.post(url, data=data)
                
                if response.status_code != 200:
                    print(f"Ошибка отправки лога в Telegram: {response.status_code}")
                    
        except httpx.TimeoutException:
            print("Таймаут при отправке лога в Telegram")
        except Exception as e:
            print(f"Ошибка в TelegramLogsHandler: {e}")
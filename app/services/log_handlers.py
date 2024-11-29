import logging
import httpx
from app.config import settings


class TelegramLogsHandler(logging.Handler):
    def emit(self, record):
        update_id = settings.admin_id
        log_entry = self.format(record)
        url = (f'https://api.telegram.org/bot{settings.logs_bot}/sendMessage?chat_id={update_id}&text={str(log_entry).strip()}'
               f'&parse_mode=HTML')
        httpx.get(url)
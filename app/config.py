import os
from dotenv import load_dotenv
from pydantic import HttpUrl, BaseSettings
import logging
import logging.config

load_dotenv()


class Settings(BaseSettings):
    logs_bot_token: str
    api_token: str = os.getenv('API_TOKEN')
    bot_token: str = os.getenv('BOT_TOKEN')
    domain: HttpUrl = os.getenv('DOMAIN')
    api_base_url: str = os.getenv('API_BASE_URL')
    admin_id: str = os.getenv('ADMIN_ID')
    logs_bot: str = os.getenv('LOGS_BOT_TOKEN')
    webhook_url: str = f"{domain}/{bot_token}"
    webhook_path: str = f"/{bot_token}"
    redis_host: str = "localhost"
    redis_port: int = 6379
    soft_collection_user_code: str = "SoftCollect"
    constant_comment_id: int = 2
    delete_message_timer: int = 2

    class Config:
        env_file = ".env"


settings = Settings()

API_METHODS = {
    'tasks': "tasks/",
    'workers': "workers/",
    'workers_f': "worker_f/",
    'partner-worker_f': 'partner-worker_f/',
    'result-data_f': 'result-data_f/',
    'result': 'result/',
    'result-data': 'result-data/',
    'supervisors': 'supervisors/',
    'auth': 'token-auth/',
    'worker_detail': 'workers/',
    'supervisor_detail': 'supervisors/'
}

TASK_GROUP = {
    '000000001': 'Pазработка Контрагента',
    '000000002': 'Кредитный Контроль',
    '000000004': 'Сенсус',
}

CENSUS = '000000004'

DEBIT = '000000002'

if not os.path.exists('logs'):
    os.makedirs('logs')

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(filename)s:%(lineno)d #%(levelname)-8s '
                      '[%(asctime)s] - %(name)s - %(message)s'
        },
        'my_verbose': {
            'format': 'TASK_BOT - %(filename)s:%(lineno)d - <b>%(levelname)-8s</b> - '
                      '<i> [%(asctime)s]</i> - %(message)s'
        }
    },
    'handlers': {
        'stream_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'info_file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': 'logs/info.log'
        },
        'error_file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': 'logs/error.log',
            'level': logging.ERROR,
        },
        'telegram_warning': {
            'class': 'app.services.log_handlers.SafeTelegramLogsHandler',
            'formatter': 'my_verbose',
            'level': 'ERROR'
        },
    },
    'loggers': {
        '': {
            'handlers': ['stream_handler', 'info_file_handler', 'error_file_handler'],
            'level': 'INFO',
            'propagate': False
        },
        'handlers.done_handlers': {
            'handlers': ['stream_handler', 'info_file_handler', 'telegram_warning'],
            'level': 'INFO',
            'propagate': False
        },
        'handlers.forward_handlers': {
            'handlers': ['stream_handler', 'info_file_handler', 'telegram_warning'],
            'level': 'INFO',
            'propagate': False
        },
        'handlers.other_handlers': {
            'handlers': ['stream_handler', 'info_file_handler', 'telegram_warning'],
            'level': 'INFO',
            'propagate': False
        },
        'database.database': {
            'handlers': ['stream_handler', 'info_file_handler', 'telegram_warning'],
            'level': 'INFO',
            'propagate': False
        },
        'aiohttp.access': {
            'handlers': ['stream_handler', 'info_file_handler'],
            'level': 'WARNING',
            'propagate': False
        },
        'aiohttp.client': {
            'handlers': ['stream_handler', 'info_file_handler'],
            'level': 'WARNING',
            'propagate': False
        },
        'httpx': {
            'handlers': ['stream_handler', 'info_file_handler'],
            'level': 'WARNING',
            'propagate': False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot')
logger.info("Логгер успешно настроен!")
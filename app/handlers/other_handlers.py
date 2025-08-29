import asyncio
import logging
from time import sleep

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ContentType, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import settings, TASK_GROUP, CENSUS, DEBIT
from app.database.database import get_trades_tasks_list, put_register, get_worker_f_chat_id
from app.keyboards.trades_keyboards import create_trades_register_inline_kb, create_new_tasks_inline_kb, \
     create_new_tasks_inline_kb_census, create_full_census_inline_kb
from app.lexicon.lexicon import LEXICON
from app.services.utils import clear_date, del_ready_task, update_task_message_id, token_generator

logger = logging.getLogger(__name__)

router: Router = Router()


@router.message(CommandStart())
async def process_start_command(message: Message):
    logger.info(f"Поступила команда старт - {message.from_user.id} - {message.from_user.username}")
    await message.answer(LEXICON[message.text])


@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    logger.info(f"Поступила команда help - {message.from_user.id} - {message.from_user.username}")
    await message.answer(LEXICON[message.text])


@router.message(Command(commands='register'))
async def process_register_command(message: Message, ):
    logger.info(f"Поступила команда регистрации - {message.from_user.id} - {message.from_user.username}")
    await message.answer(
        text='Для регистрации необходимо нажать кнопку "Передать телефон"',
        reply_markup=create_trades_register_inline_kb())


@router.message(Command(commands='census_task'))
async def census_tasks_command(message: Message, state: FSMContext):

    await state.clear()
    logger.info(
        f"Поступила команда tasks - {message.from_user.id} - {message.from_user.username}. "
        f"Состояние очищено")

    tasks_list = await get_trades_tasks_list(message.from_user.id, CENSUS)

    # [del_ready_task(message.from_user.id, x['message_id']) for x in tasks_list['text']]  # Удаление плашек выгруженных задач
    if tasks_list['status']:
        if len(tasks_list['text']) > 0:

            for task in tasks_list['text']:
                date = clear_date(task['date'])
                deadline = clear_date(task['deadline'])
                author_comment = task['author_comment']['comment'].split('_')[0]

                text = f"Задача от " \
                       f"{date}\n\n" \
                       f"Сенсус по адресу: '{task['name']}'\n\n" \
                       f"<b>Исполнить до:</b>\n" \
                       f"{deadline}\n" \
                       f"<b>Автор:</b>\n" \
                       f"{task['author']['name']}\n" \
                       f"<b>Контрагент:</b>\n" \
                       f"{task['partner']['name']}\n" \
                       f"<b>Основание:</b>\n" \
                       f"{task['base']['name']}\n" \
                       f"<b>Комментарий автора:</b>\n" \
                       f"{author_comment}"

                await asyncio.sleep(2)
                await message.answer(
                    text=text,
                    reply_markup=create_new_tasks_inline_kb_census(task))
        else:
            await message.answer(text="У вас нет новых задач")
    else:
        await message.answer(text=tasks_list['text'])


@router.message(Command(commands='debit_task'))
async def debit_command(message: Message, state: FSMContext):

    await state.clear()
    logger.info(
        f"Поступила команда tasks - {message.from_user.id} - {message.from_user.username}. "
        f"Состояние очищено")

    tasks_list = await get_trades_tasks_list(message.from_user.id, DEBIT)

    if tasks_list['status']:
        if len(tasks_list['text']) > 0:

            for task in tasks_list['text']:

                group_name = task['base']['group']
                date = clear_date(task['date'])
                deadline = clear_date(task['deadline'])

                text = f"Задача от " \
                       f"{date}\n\n" \
                       f"'{TASK_GROUP[group_name]}'\n\n" \
                       f"<b>Исполнить до:</b>\n" \
                       f"{deadline}\n" \
                       f"<b>Автор:</b>\n" \
                       f"{task['author']['name']}\n" \
                       f"<b>Контрагент:</b>\n" \
                       f"{task['partner']['name']}\n" \
                       f"<b>Основание:</b>\n" \
                       f"{task['base']['name']}\n" \
                       f"<b>Комментарий автора:</b>\n" \
                       f"{task['author_comment']['comment']}"

                await asyncio.sleep(1)
                await message.answer(
                    text=text,
                    reply_markup=create_new_tasks_inline_kb(task))

        else:
            await message.answer(text="У вас нет новых задач")
    else:
        await message.answer(text=tasks_list['text'])


@router.callback_query()
async def unhandled_callback(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    logger.warning(
        f"Необработанный callback '{callback.data}' - {callback.from_user.id} - {callback.from_user.username} - "
        f"state={current_state}")
    try:
        await callback.answer()
    except Exception:
        pass



@router.message(F.content_type.in_({ContentType.CONTACT}))
async def get_contact(message: Message):

    phone = message.contact.phone_number
    chat_id = message.contact.user_id
    await message.delete()
    response = await put_register(phone=phone, chat_id=chat_id)
    logger.info(f"Передан номер телефона - {phone} - {message.from_user.id} - {message.from_user.username}")
    if response['status']:
        return await message.reply(text=response['message'], reply_markup=ReplyKeyboardRemove())
    else:
        return await message.reply(text=response['message'], reply_markup=ReplyKeyboardRemove())


# Этот хэндлер будет реагировать на любые сообщения пользователя,
# не предусмотренные логикой работы бота
# @router.message()
# async def send_echo(message: Message):
#     await message.answer(LEXICON['/help'])


@router.message(Command(commands='census'))
async def ful_census_command(message: Message):
    logger.info(f"Поступила команда заполнения Сенсуса - {message.from_user.id} - {message.from_user.username}")
    depart_res = await get_worker_f_chat_id(message.from_user.id)
    department = depart_res.json()[0]['department']
    token = token_generator(depart_res.json()[0])
    census_url = f"{settings.api_base_url[:-7]}census/census-template/?" \
                 f"depart={department}&" \
                 f"worker={message.from_user.id}&" \
                 f"token={token}"
    await message.answer(
        text="Чтобы заполнить сенсус нажмите кнопку",
        reply_markup=create_full_census_inline_kb(census_url)
    )

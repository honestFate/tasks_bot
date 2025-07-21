import asyncio
import logging

from aiogram import Router
from aiogram.filters import Text, StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext
from aiogram3_calendar import simple_cal_callback
from aiogram.exceptions import TelegramBadRequest

from app.filters.filters import menu_commands_filter
from app.keyboards.calendar import MySimpleCalendar

from app.database.database import get_task_detail, get_result_list, \
     get_result_data_detail, get_ready_result_task

from app.services.redis_data import redis_clear
from app.keyboards.trades_keyboards import create_types_done_inline_kb, create_result_types_done_inline_kb, \
     create_contact_person_done_inline_kb

from app.lexicon import lexicon
from app.forms.user_form import DoneTaskForm
from app.services.utils import clear_date
from app.config import settings

logger = logging.getLogger(__name__)

router: Router = Router()


@router.message(StateFilter(DoneTaskForm.worker_comment), menu_commands_filter)
async def add_ok_task_comment(message: Message, state: FSMContext):
    """Добавление комментария к выполненной задаче"""

    task = await state.get_data()
    await state.update_data(worker_comment=message.text)
    
    try:
        await message.delete()
        logger.info(f"Сообщение пользователя {message.from_user.id} удалено успешно")
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось удалить сообщение пользователя {message.from_user.id}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при удалении сообщения: {e}")

    logger.info(f"Комментарий к задаче {task['task_number']} - {message.from_user.id} - "
                f"{message.from_user.username}")
    task_data = await state.get_data()

    try:
        res = await get_ready_result_task(task_data)

        if res['status']:
            logger.info(f"{res['text']}- {message.from_user.id} - {message.from_user.username}")
            await state.clear()
            redis_clear(task['task_number'])
        else:
            logger.warning(f"{res['text']}- {message.from_user.id} - {message.from_user.username}")

        redis_clear(task['task_number'])
        await state.clear()
        logger.info(f"Cостояние очищено по задаче {task['task_number']} - "
                    f"{message.from_user.id} - {message.from_user.username}")
        await message.answer(text=res['text'])
    except Exception as e:
        logger.error(f"Ошибка при обработке задачи {task.get('task_number', 'unknown')}: {e}")
        await message.answer(text="Произошла ошибка при обработке задачи. Обратитесь в техподдержку.")


@router.callback_query(Text(startswith='ok'), StateFilter(default_state))
async def process_forward_press(callback: CallbackQuery, state: FSMContext):
    """При нажатии на кнопку 'Выполнено'"""
    task_number = callback.data.split("_")[1]
    logger.info(f"Получен положительный ответ к задаче {task_number} для {callback.from_user.username}-"
                f"{callback.from_user.id}")
    await state.update_data(task_number=task_number)
    await state.set_state(DoneTaskForm.task_number)
    logger.info(f"Записаны данные в state {await state.get_data()}")
    
    try:
        task = await get_task_detail(task_number)
        date = clear_date(task['date'])

        text = f"""
                     Укажите какое действие было сделано к задаче от {date}\n\n"{task['name']}"\n
                 """
        await callback.message.answer(text=text, reply_markup=create_types_done_inline_kb(1, lexicon.TYPES))
        
        try:
            await callback.message.delete()
            logger.info(f"Сообщение_ok по задаче {task['name']} удалено")
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось удалить callback сообщение: {e}")
            
        logger.info(f"Создана клавиатура c 'contacts'")
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'Выполнено' для задачи {task_number}: {e}")
        await callback.message.answer(text="Произошла ошибка. Попробуйте позже.")


@router.callback_query(Text(text=[f"contact_{x}" for x in lexicon.TYPES.keys()]))
async def process_contact_press(callback: CallbackQuery, state: FSMContext):
    """При нажатии на клавиатуру действий"""

    task_type = callback.data.split('_')[1]
    await state.update_data(task_type=task_type)
    await state.set_state(DoneTaskForm.task_type)
    task_number = await state.get_data()
    logger.info(f"Получены тип контакта - {task_type} - к задаче {task_number['task_number']}")
    logger.info(f"Записаны данные в state {await state.get_data()}")
    
    try:
        task = await get_task_detail(task_number['task_number'])

        text = f"""
                Выберите контактное лицо\n\n
                """
        partner_workers = task['partner']['workers']
        if len(partner_workers) <= 0:
            partner_workers = [{"name": "Нет контакта в 1С", "positions": "Нет контакта в 1С", "code": None}]
            await callback.message.answer(text=text,
                                          reply_markup=create_contact_person_done_inline_kb(1, partner_workers))
        else:
            await callback.message.answer(text=text,
                                          reply_markup=create_contact_person_done_inline_kb(1, partner_workers))

        await asyncio.sleep(settings.delete_message_timer)
        
        try:
            await callback.message.delete()
            logger.info(f"Сообщение_contact по задаче {task_number['task_number']} удалено")
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось удалить contact сообщение: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора контакта: {e}")


@router.callback_query(Text(startswith="person"))
async def process_person_press(callback: CallbackQuery, state: FSMContext):
    person_id = callback.data.split('_')[1]
    task_number = await state.get_data()
    
    try:
        task = await get_task_detail(task_number['task_number'])
        await state.update_data(contact_person=person_id)
        logger.info(f"Получены контактное лицо - {person_id} - к задаче {task['name']}")
        logger.info(f"Записаны данные в state {await state.get_data()}")
        date = clear_date(task['date'])

        text = f"""
                Выберите результат действия к задаче {task['name']} от {date}\n\n
                """

        await callback.message.answer(
            text=text,
            reply_markup=create_result_types_done_inline_kb(1, await get_result_list(task['base']['group']))
        )

        await asyncio.sleep(settings.delete_message_timer)
        
        try:
            await callback.message.delete()
            logger.info(f"Сообщение_person по задаче {task_number['task_number']} удалено")
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось удалить person сообщение: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора персоны: {e}")


@router.callback_query(Text(startswith="result"))
async def process_result_press(callback: CallbackQuery, state: FSMContext):
    result_id = callback.data.split('_')[1]
    
    try:
        result_data = await get_result_data_detail(result_id)
        await state.update_data(result=result_data['name'])
        task = await state.get_data()
        tasks_data = await get_task_detail(task['task_number'])
        logger.info(f"Получен результат - {result_data['name']} - к задаче {task['task_number']} - "
                    f"{callback.message.from_user.id} - "
                    f"{callback.message.from_user.username}")
        logger.info(f"Записаны данные в state {await state.get_data()} - "
                    f"{callback.message.from_user.id} - "
                    f"{callback.from_user.username}")

        if result_data['control_data']:
            text = """
                Установите контрольную дату:
            """

            await callback.message.answer(
                text=text,
                reply_markup=await MySimpleCalendar().start_calendar())
            logger.info(f"Открыта клавиатура для задачи {task['task_number']}")
            await asyncio.sleep(settings.delete_message_timer)
            
            try:
                await callback.message.delete()
                logger.info(f"Сообщение_result по задаче {task['task_number']} удалено")
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось удалить result сообщение: {e}")
        else:
            await callback.message.answer(text=f"Укажите комментарий к задаче {tasks_data['name']}")
            
            try:
                await callback.message.delete()
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось удалить callback сообщение: {e}")
                
            await state.set_state(DoneTaskForm.worker_comment)
            logger.info(f"Сообщение_result по задаче {task['task_number']} удалено")
    except Exception as e:
        logger.error(f"Ошибка при обработке результата: {e}")


@router.callback_query(simple_cal_callback.filter())
async def process_simple_calendar(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    try:
        selected, date = await MySimpleCalendar().my_process_selection(callback, callback_data)
        logger.info(f"Установлена дата {date}  - {callback.message.from_user.id} - "
                    f"{callback.message.from_user.username}")
        if selected:
            await state.update_data(control_date=date)
            task = await state.get_data()
            tasks_data = await get_task_detail(task['task_number'])
            await callback.message.answer(
                text=f"Укажите комментарий к задаче {tasks_data['name']}\n ⬇️⬇️⬇️"
            )
            await state.set_state(DoneTaskForm.worker_comment)
            await asyncio.sleep(settings.delete_message_timer)
            
            try:
                await callback.message.delete()
                logger.info(f"Календарь по задаче {task['task_number']} удален")
            except TelegramBadRequest as e:
                logger.warning(f"Не удалось удалить календарь: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке календаря: {e}")
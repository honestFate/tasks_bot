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


async def validate_task_state(state: FSMContext, required_fields: list = None) -> tuple[bool, dict]:
    """
    Валидация состояния FSM
    
    Args:
        state: Контекст состояния FSM
        required_fields: Список обязательных полей
    
    Returns:
        tuple: (is_valid, state_data)
    """
    if required_fields is None:
        required_fields = ['task_number']
    
    try:
        state_data = await state.get_data()
        is_valid = all(field in state_data and state_data[field] is not None for field in required_fields)
        return is_valid, state_data
    except Exception as e:
        logger.error(f"Ошибка при валидации состояния: {e}")
        return False, {}


async def safe_delete_message(message, context: str = ""):
    """
    Безопасное удаление сообщения с логированием
    
    Args:
        message: Сообщение для удаления
        context: Контекст для логирования
    """
    try:
        await message.delete()
        logger.info(f"Сообщение {context} удалено успешно")
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось удалить сообщение {context}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при удалении сообщения {context}: {e}")


@router.message(StateFilter(DoneTaskForm.worker_comment), menu_commands_filter)
async def add_ok_task_comment(message: Message, state: FSMContext):
    """Добавление комментария к выполненной задаче"""
    
    # Валидация состояния
    is_valid, task_data = await validate_task_state(state, ['task_number'])
    if not is_valid:
        logger.error(f"Некорректное состояние при добавлении комментария. "
                    f"Данные: {task_data}. Пользователь: {message.from_user.id}")
        await message.answer("Ошибка: данные задачи не найдены. Пожалуйста, начните процесс заново.")
        await state.clear()
        return

    await state.update_data(worker_comment=message.text)
    
    # Безопасное удаление сообщения пользователя
    await safe_delete_message(message, f"пользователя {message.from_user.id}")

    logger.info(f"Комментарий к задаче {task_data['task_number']} - {message.from_user.id} - "
                f"{message.from_user.username}")
    
    # Получаем обновленные данные после добавления комментария
    updated_task_data = await state.get_data()

    try:
        res = await get_ready_result_task(updated_task_data)

        if res['status']:
            logger.info(f"{res['text']} - {message.from_user.id} - {message.from_user.username}")
            await state.clear()
            redis_clear(task_data['task_number'])
            await message.answer(text=res['text'])
        else:
            logger.warning(f"{res['text']} - {message.from_user.id} - {message.from_user.username}")
            await message.answer(text=res['text'])
            # Очищаем состояние даже при неуспешном результате
            await state.clear()
            redis_clear(task_data['task_number'])

        logger.info(f"Состояние очищено по задаче {task_data['task_number']} - "
                    f"{message.from_user.id} - {message.from_user.username}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке задачи {task_data.get('task_number', 'unknown')}: {e}. "
                    f"Данные состояния: {updated_task_data}")
        await message.answer(text="Произошла ошибка при обработке задачи. Обратитесь в техподдержку.")
        # Очищаем состояние при ошибке
        await state.clear()
        if 'task_number' in task_data:
            redis_clear(task_data['task_number'])


@router.callback_query(Text(startswith='ok'), StateFilter(default_state))
async def process_forward_press(callback: CallbackQuery, state: FSMContext):
    """При нажатии на кнопку 'Выполнено'"""
    
    try:
        task_number = callback.data.split("_")[1]
        logger.info(f"Получен положительный ответ к задаче {task_number} для {callback.from_user.username} - "
                    f"{callback.from_user.id}")
        
        # Устанавливаем данные в состояние
        await state.update_data(task_number=task_number)
        await state.set_state(DoneTaskForm.task_number)
        
        # Логируем установленные данные
        state_data = await state.get_data()
        logger.info(f"Записаны данные в state: {state_data}")

        # Получаем детали задачи
        task = await get_task_detail(task_number)
        if not task:
            logger.error(f"Задача {task_number} не найдена в базе данных")
            await callback.message.answer("Ошибка: задача не найдена. Обратитесь в техподдержку.")
            await state.clear()
            return

        date = clear_date(task['date'])
        text = f"""Укажите какое действие было сделано к задаче от {date}

"{task['name']}"
"""
        await callback.message.answer(text=text, reply_markup=create_types_done_inline_kb(1, lexicon.TYPES))

        # Безопасное удаление callback сообщения
        await safe_delete_message(callback.message, f"ok по задаче {task['name']}")

        logger.info(f"Создана клавиатура с 'contacts' для задачи {task_number}")
        
    except IndexError:
        logger.error(f"Некорректный формат callback_data: {callback.data}")
        await callback.message.answer("Ошибка: некорректные данные. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'Выполнено' для задачи {callback.data}: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()


@router.callback_query(Text(text=[f"contact_{x}" for x in lexicon.TYPES.keys()]))
async def process_contact_press(callback: CallbackQuery, state: FSMContext):
    """При нажатии на клавиатуру действий"""

    try:
        task_type = callback.data.split('_')[1]
        await state.update_data(task_type=task_type)
        await state.set_state(DoneTaskForm.task_type)
        
        # Валидация состояния
        is_valid, task_data = await validate_task_state(state, ['task_number'])
        if not is_valid:
            logger.error(f"Некорректное состояние при обработке контакта. "
                        f"Данные: {task_data}. Пользователь: {callback.from_user.id}")
            await callback.message.answer("Ошибка: данные задачи не найдены. Начните процесс заново.")
            await state.clear()
            return

        logger.info(f"Получен тип контакта - {task_type} - к задаче {task_data['task_number']}")
        logger.info(f"Записаны данные в state: {await state.get_data()}")

        # Получаем детали задачи
        task = await get_task_detail(task_data['task_number'])
        if not task:
            logger.error(f"Задача {task_data['task_number']} не найдена при обработке контакта")
            await callback.message.answer("Ошибка: задача не найдена. Обратитесь в техподдержку.")
            await state.clear()
            return

        text = """Выберите контактное лицо

"""
        partner_workers = task.get('partner', {}).get('workers', [])
        
        if not partner_workers or len(partner_workers) <= 0:
            partner_workers = [{"name": "Нет контакта в 1С", "positions": "Нет контакта в 1С", "code": None}]

        await callback.message.answer(text=text,
                                      reply_markup=create_contact_person_done_inline_kb(1, partner_workers))

        await asyncio.sleep(settings.delete_message_timer)
        await safe_delete_message(callback.message, f"contact по задаче {task_data['task_number']}")
        
    except IndexError:
        logger.error(f"Некорректный формат callback_data при обработке контакта: {callback.data}")
        await callback.message.answer("Ошибка: некорректные данные контакта.")
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора контакта: {e}. "
                    f"Callback data: {callback.data}")
        await callback.message.answer("Произошла ошибка при выборе контакта. Попробуйте еще раз.")


@router.callback_query(Text(startswith="person"))
async def process_person_press(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора контактного лица"""
    
    try:
        person_id = callback.data.split('_')[1]
        
        # Валидация состояния
        is_valid, task_data = await validate_task_state(state, ['task_number'])
        if not is_valid:
            logger.error(f"Некорректное состояние при выборе персоны. "
                        f"Данные: {task_data}. Пользователь: {callback.from_user.id}")
            await callback.message.answer("Ошибка: данные задачи не найдены. Начните процесс заново.")
            await state.clear()
            return

        # Получаем детали задачи
        task = await get_task_detail(task_data['task_number'])
        if not task:
            logger.error(f"Задача {task_data['task_number']} не найдена при выборе персоны")
            await callback.message.answer("Ошибка: задача не найдена. Обратитесь в техподдержку.")
            await state.clear()
            return

        await state.update_data(contact_person=person_id)
        logger.info(f"Получено контактное лицо - {person_id} - к задаче {task['name']}")
        logger.info(f"Записаны данные в state: {await state.get_data()}")
        
        date = clear_date(task['date'])
        text = f"""Выберите результат действия к задаче {task['name']} от {date}

"""

        # Получаем список результатов
        group = task.get('base', {}).get('group')
        if not group:
            logger.error(f"Не найдена группа для задачи {task_data['task_number']}")
            await callback.message.answer("Ошибка: некорректные данные задачи.")
            return

        result_list = await get_result_list(group)
        if not result_list:
            logger.warning(f"Пустой список результатов для группы {group}")
            await callback.message.answer("Ошибка: не найдены доступные результаты для данной задачи.")
            return

        await callback.message.answer(
            text=text,
            reply_markup=create_result_types_done_inline_kb(1, result_list)
        )

        await asyncio.sleep(settings.delete_message_timer)
        await safe_delete_message(callback.message, f"person по задаче {task_data['task_number']}")
        
    except IndexError:
        logger.error(f"Некорректный формат callback_data при выборе персоны: {callback.data}")
        await callback.message.answer("Ошибка: некорректные данные персоны.")
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора персоны: {e}. "
                    f"Callback data: {callback.data}")
        await callback.message.answer("Произошла ошибка при выборе контактного лица. Попробуйте еще раз.")


@router.callback_query(Text(startswith="result"))
async def process_result_press(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора результата"""
    
    try:
        result_id = callback.data.split('_')[1]
        
        # Валидация состояния
        is_valid, task_data = await validate_task_state(state, ['task_number'])
        if not is_valid:
            logger.error(f"Некорректное состояние при обработке результата. "
                        f"Данные: {task_data}. Пользователь: {callback.from_user.id}")
            await callback.message.answer("Ошибка: данные задачи не найдены. Начните процесс заново.")
            await state.clear()
            return

        # Получаем данные результата
        result_data = await get_result_data_detail(result_id)
        if not result_data:
            logger.error(f"Результат {result_id} не найден")
            await callback.message.answer("Ошибка: выбранный результат не найден.")
            return

        await state.update_data(result=result_data['name'])
        
        # Получаем обновленные данные состояния
        updated_task_data = await state.get_data()
        
        # Получаем детали задачи
        tasks_data = await get_task_detail(task_data['task_number'])
        if not tasks_data:
            logger.error(f"Задача {task_data['task_number']} не найдена при обработке результата")
            await callback.message.answer("Ошибка: задача не найдена. Обратитесь в техподдержку.")
            await state.clear()
            return

        logger.info(f"Получен результат - {result_data['name']} - к задаче {task_data['task_number']} - "
                    f"{callback.from_user.id} - {callback.from_user.username}")
        logger.info(f"Записаны данные в state: {updated_task_data} - "
                    f"{callback.from_user.id} - {callback.from_user.username}")

        if result_data.get('control_data'):
            text = """Установите контрольную дату:
"""
            await callback.message.answer(
                text=text,
                reply_markup=await MySimpleCalendar().start_calendar())
            logger.info(f"Открыта клавиатура календаря для задачи {task_data['task_number']}")
            
            await asyncio.sleep(settings.delete_message_timer)
            await safe_delete_message(callback.message, f"result по задаче {task_data['task_number']}")
        else:
            await callback.message.answer(text=f"Укажите комментарий к задаче {tasks_data['name']}")
            await safe_delete_message(callback.message, f"result callback по задаче {task_data['task_number']}")
            await state.set_state(DoneTaskForm.worker_comment)
            logger.info(f"Переход к состоянию комментария для задачи {task_data['task_number']}")
            
    except IndexError:
        logger.error(f"Некорректный формат callback_data при обработке результата: {callback.data}")
        await callback.message.answer("Ошибка: некорректные данные результата.")
    except Exception as e:
        # Получаем данные состояния для подробного логирования
        try:
            state_data = await state.get_data()
        except:
            state_data = "Не удалось получить данные состояния"
            
        logger.error(f"Ошибка при обработке результата: {e}. "
                    f"Данные состояния: {state_data}. "
                    f"Callback data: {callback.data}")
        await callback.message.answer("Произошла ошибка при обработке результата. Попробуйте еще раз.")


@router.callback_query(simple_cal_callback.filter())
async def process_simple_calendar(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    """Обработка выбора даты в календаре"""
    
    try:
        # Валидация состояния
        is_valid, task_data = await validate_task_state(state, ['task_number'])
        if not is_valid:
            logger.error(f"Некорректное состояние при обработке календаря. "
                        f"Данные: {task_data}. Пользователь: {callback.from_user.id}")
            await callback.message.answer("Ошибка: данные задачи не найдены. Начните процесс заново.")
            await state.clear()
            return

        selected, date = await MySimpleCalendar().my_process_selection(callback, callback_data)
        logger.info(f"Обработка календаря - дата: {date} - {callback.from_user.id} - "
                    f"{callback.from_user.username}")
        
        if selected:
            await state.update_data(control_date=date)
            
            # Получаем обновленные данные состояния
            updated_task_data = await state.get_data()
            
            # Получаем детали задачи
            tasks_data = await get_task_detail(task_data['task_number'])
            if not tasks_data:
                logger.error(f"Задача {task_data['task_number']} не найдена при установке даты")
                await callback.message.answer("Ошибка: задача не найдена. Обратитесь в техподдержку.")
                await state.clear()
                return

            logger.info(f"Установлена контрольная дата {date} для задачи {task_data['task_number']} - "
                       f"{callback.from_user.id} - {callback.from_user.username}")

            await callback.message.answer(
                text=f"Укажите комментарий к задаче {tasks_data['name']}\n"
            )
            await state.set_state(DoneTaskForm.worker_comment)
            
            await asyncio.sleep(settings.delete_message_timer)
            await safe_delete_message(callback.message, f"календарь по задаче {task_data['task_number']}")
            
    except Exception as e:
        # Получаем данные состояния для подробного логирования
        try:
            state_data = await state.get_data()
        except:
            state_data = "Не удалось получить данные состояния"
            
        logger.error(f"Ошибка при обработке календаря: {e}. "
                    f"Данные состояния: {state_data}. "
                    f"Callback data: {callback_data}")
        await callback.message.answer("Произошла ошибка при выборе даты. Попробуйте еще раз.")

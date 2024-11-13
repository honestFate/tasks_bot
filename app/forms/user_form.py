from aiogram.filters.state import State, StatesGroup


class Form(StatesGroup):
    comment = State()
    task = State()
    comment_id = State()


class ForwardTaskForm(StatesGroup):
    comment = State()
    task_number = State()
    next_user_id = State()


class DoneTaskForm(StatesGroup):
    task_type = State()
    result = State()
    contact_person = State()
    worker_comment = State()
    task_number = State()
    control_date = State()

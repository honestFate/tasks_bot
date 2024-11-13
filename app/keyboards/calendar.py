from aiogram3_calendar import SimpleCalendar
from aiogram3_calendar.calendar_types import SimpleCalendarCallback, SimpleCalendarAction, WEEKDAYS
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta


class MySimpleCalendar(SimpleCalendar):
    async def my_process_selection(self, query: CallbackQuery, data: [CallbackData, SimpleCalendarCallback]) -> tuple:

        return_data = (False, None)
        temp_date = datetime(int(data.year), int(data.month), 1)
        # processing empty buttons, answering with no action
        if data.act == SimpleCalendarAction.IGNORE:
            await query.answer(cache_time=60)
        # user picked a day button, return date
        if data.act == SimpleCalendarAction.DAY:
            await query.message.delete_reply_markup()  # removing inline keyboard
            return_data = True, datetime(int(data.year), int(data.month), int(data.day))
        # user navigates to previous year, editing message with new calendar
        if data.act == SimpleCalendarAction.PREV_YEAR:
            prev_date = datetime(int(data.year) - 1, int(data.month), 1)
            await query.message.edit_reply_markup(query.inline_message_id,
                                                  await self.start_calendar(int(prev_date.year), int(prev_date.month)))
        # user navigates to next year, editing message with new calendar
        if data.act == SimpleCalendarAction.NEXT_YEAR:
            next_date = datetime(int(data.year) + 1, int(data.month), 1)
            await query.message.edit_reply_markup(query.inline_message_id,
                                                  await self.start_calendar(int(next_date.year), int(next_date.month)))
        # user navigates to previous month, editing message with new calendar
        if data.act == SimpleCalendarAction.PREV_MONTH:
            prev_date = temp_date - timedelta(days=1)
            await query.message.edit_reply_markup(query.inline_message_id,
                                                  await self.start_calendar(int(prev_date.year), int(prev_date.month)))
        # user navigates to next month, editing message with new calendar
        if data.act == SimpleCalendarAction.NEXT_MONTH:
            next_date = temp_date + timedelta(days=31)
            await query.message.edit_reply_markup(query.inline_message_id,
                                                  await self.start_calendar(int(next_date.year), int(next_date.month)))
        # at some point user clicks DAY button, returning date
        return return_data

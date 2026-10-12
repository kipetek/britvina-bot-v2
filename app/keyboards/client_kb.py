"""
Inline-кнопки для клиента.

InlineKeyboardButton — кнопка, привязанная к сообщению.
CallbackData — «невидимые» данные, которые бот получает,
когда кнопка нажата (чтобы понять, какую именно нажали).
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Callback-данные: строки-идентификаторы действий.
# Лучше вынести в константы, чтобы не опечататься.
CB_FILE_SENT = "file_sent"
CB_PAID = "paid"
CB_CHECK_STATUS = "check_status"


def get_client_status_keyboard(
    file_sent: bool,
    paid: bool,
) -> InlineKeyboardMarkup | None:
    """
    Собирает клавиатуру в зависимости от того, что уже сделано.

    file_sent / paid: True, если действие уже выполнено.
    Возвращает None, если делать нечего (всё готово) — тогда
    сообщение покажем без кнопок.
    """
    builder = InlineKeyboardBuilder()

    if not file_sent:
        builder.button(
            text="📄 Отправил выписку",
            callback_data=CB_FILE_SENT,
        )

    if not paid:
        builder.button(
            text="💳 Оплатил",
            callback_data=CB_PAID,
        )

    builder.button(
        text="🔄 Обновить статус",
        callback_data=CB_CHECK_STATUS,
    )

    # Все кнопки — в один столбец
    builder.adjust(1)

    # Если делать нечего — не показываем клавиатуру
    if not file_sent or not paid:
        return builder.as_markup()
    return None
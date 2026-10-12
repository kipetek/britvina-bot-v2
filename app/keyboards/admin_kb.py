"""
Клавиатуры для админских команд.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Callback-данные для выбора типа имени
CB_SET_COMPANY = "set_company"
CB_SET_PERSON = "set_person"
CB_CANCEL = "cancel_name"


def get_name_type_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура «Что задаём?» — компания или ФИО.

    В callback_data кладём client_id, чтобы знать, кому задаём.
    Формат: "set_company:<client_id>".
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏢 Компания",
        callback_data=f"{CB_SET_COMPANY}:{client_id}",
    )
    builder.button(
        text="👤 ФИО",
        callback_data=f"{CB_SET_PERSON}:{client_id}",
    )
    builder.button(
        text="❌ Отмена",
        callback_data=CB_CANCEL,
    )

    builder.adjust(2, 1)  # две кнопки в ряд, потом отмена
    return builder.as_markup()

# Callback для кнопки в уведомлении о новом клиенте
CB_ADMIN_SET_NAME = "admin_set_name"


def get_new_client_keyboard(client_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура под уведомлением о новом клиенте.
    Одна кнопка — «Задать имя». В callback_data кладём ID клиента.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Задать имя",
        callback_data=f"{CB_ADMIN_SET_NAME}:{client_id}",
    )
    return builder.as_markup()

def get_reset_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения сброса статусов.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, начать новый период",
        callback_data="reset_confirm",
    )
    builder.button(
        text="❌ Отмена",
        callback_data="reset_cancel",
    )
    builder.adjust(1)
    return builder.as_markup()

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения рассылки.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Отправить",
        callback_data="broadcast_confirm",
    )
    builder.button(
        text="❌ Отмена",
        callback_data="broadcast_cancel",
    )
    builder.adjust(1)
    return builder.as_markup()
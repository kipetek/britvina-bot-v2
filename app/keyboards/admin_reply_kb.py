"""
Reply-клавиатура для админов.

Это обычные кнопки внизу экрана Telegram (не inline).
Они отправляют боту текст — мы ловим его и вызываем нужную логику.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


# Тексты кнопок. Храним в константах, чтобы не опечататься.
BTN_LIST = "📋 Список клиентов"
BTN_DEBTORS = "👥 Должники"
BTN_STATS = "📊 Статистика"
BTN_PERIODS = "📅 Периоды"
BTN_RESET = "🔄 Сброс статусов"
BTN_HELP = "❓ Помощь"
BTN_REMIND = "📬 Напомнить"
BTN_BROADCAST = "📢 Написать всем"

def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Собирает reply-клавиатуру для админа.
    """
    keyboard = [
        [KeyboardButton(text=BTN_LIST), KeyboardButton(text=BTN_DEBTORS)],
        [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_PERIODS)],
        [KeyboardButton(text=BTN_REMIND), KeyboardButton(text=BTN_BROADCAST)],
        [KeyboardButton(text=BTN_RESET), KeyboardButton(text=BTN_HELP)],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие…",
    )
"""
FSM-состояния для админских диалогов.
"""

from aiogram.fsm.state import State, StatesGroup


class SetNameStates(StatesGroup):
    """
    Диалог «Задать имя клиенту».

    Шаги:
    1. choosing_type — админ выбирает: компания или ФИО.
    2. entering_text  — админ вводит текст.
    """

    choosing_type = State()
    entering_text = State()

class BroadcastStates(StatesGroup):
    """
    Диалог рассылки сообщения всем клиентам.

    Шаги:
    1. entering_text    — админ вводит текст сообщения.
    2. confirming       — бот показывает превью и ждёт подтверждения.
    """

    entering_text = State()
    confirming = State()
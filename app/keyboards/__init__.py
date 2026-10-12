"""
Пакет с клавиатурами.
"""

from app.keyboards.client_kb import get_client_status_keyboard
from app.keyboards.admin_kb import (
    get_name_type_keyboard,
    get_new_client_keyboard,
    get_reset_confirm_keyboard,
    get_broadcast_confirm_keyboard,
)
from app.keyboards.admin_reply_kb import get_admin_reply_keyboard

__all__ = [
    "get_client_status_keyboard",
    "get_name_type_keyboard",
    "get_new_client_keyboard",
    "get_reset_confirm_keyboard",
    "get_broadcast_confirm_keyboard",
    "get_admin_reply_keyboard",
]
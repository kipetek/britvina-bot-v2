"""
Пакет с обработчиками (хендлерами).

Мы разделяем их на три группы:
• common — команды, доступные всем (/start, /help, /menu, /id, /version)
• client — логика для клиентов (кнопки, /status, отправка файлов)
• admin  — логика для администраторов (/list, /delete, /name и т.д.)

Экспортируем роутеры, чтобы main.py мог их подключить.
"""

from app.handlers.common import router as common_router
from app.handlers.client import router as client_router
from app.handlers.admin import router as admin_router

__all__ = ["common_router", "client_router", "admin_router"]
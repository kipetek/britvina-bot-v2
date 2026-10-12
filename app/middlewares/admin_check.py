"""
Middleware для проверки прав администратора.

Пропускает в админский роутер только тех, чей ID есть в ADMIN_IDS.
Всех остальных отправляет вежливое «⛔ нет доступа» и не пускает дальше.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app import texts
from app.config import settings


logger = logging.getLogger(__name__)


class AdminCheckMiddleware(BaseMiddleware):
    """
    Проверяет, что отправитель — админ.

    Подключается ТОЛЬКО к админскому роутеру.
    Остальные роутеры работают без него.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Достаём пользователя из события
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            # На всякий случай: событие без пользователя — пропускаем
            return await handler(event, data)

        if user.id not in settings.admins:
            logger.warning(
                f"Не-админ {user.id} ({user.full_name}) пытался "
                f"выполнить админское действие"
            )
            # Отвечаем в зависимости от типа события
            if isinstance(event, Message):
                await event.answer(texts.ADMIN_ONLY)
            elif isinstance(event, CallbackQuery):
                await event.answer(texts.ADMIN_ONLY, show_alert=True)
            return None  # не передаём дальше

        # Всё ок — пропускаем
        return await handler(event, data)
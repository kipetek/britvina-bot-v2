"""
Middleware для логирования входящих сообщений.

Зачем: удобно видеть в логе, кто что написал — не заходя
в диспетчер aiogram. Особенно полезно при отладке.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Логирует каждое входящее событие: сообщение или нажатие кнопки.

    Наследуемся от BaseMiddleware и переопределяем __call__ —
    он вызывается aiogram для каждого апдейта.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Формируем строку для лога в зависимости от типа события
        if isinstance(event, Message):
            user = event.from_user
            text = event.text or event.caption or "<не текст>"
            logger.info(f"[MSG] {user.id} ({user.full_name}): {text[:80]}")
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            logger.info(f"[CB]  {user.id} ({user.full_name}): {event.data}")

        # Передаём управление дальше — следующему middleware или хендлеру
        return await handler(event, data)
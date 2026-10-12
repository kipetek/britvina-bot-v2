"""
Middleware для работы с сессией БД.

Для каждого входящего события (сообщение, кнопка) aiogram
создаёт новую сессию БД, кладёт её в data['session'] и после
обработки автоматически закрывает.

В хендлерах мы получаем сессию так:
    async def my_handler(message: Message, session: AsyncSession):
        ...
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.engine import async_session_maker


logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """
    Создаёт AsyncSession для каждого апдейта.

    После завершения хендлера сессия закрывается — даже если
    произошла ошибка (благодаря try/finally).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                # Здесь можно сделать commit, если нужно.
                # Пока — flush внутри репозитория, commit вручную в хендлерах.
                return result
            except Exception:
                await session.rollback()
                raise
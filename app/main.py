"""
Точка входа. Запускает бота.
"""

import asyncio
import logging

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from app import __version__
from app.config import settings
from app.db import init_db
from app.handlers import common_router, client_router, admin_router
from app.middlewares import (
    LoggingMiddleware,
    AdminCheckMiddleware,
    DbSessionMiddleware,
)
from app.utils.logger import setup_logger


setup_logger()
logger = logging.getLogger(__name__)


# Прокси для локальной разработки.
# TODO: удалить при деплое на сервер.
PROXY_URL = "http://127.0.0.1:10809"


async def main() -> None:
    logger.info(f"Запуск бота «Бритвина» версии {__version__}...")

    # 0. Инициализируем БД (создаём таблицы)
    await init_db()

    # 1. Сессия с прокси
    session = AiohttpSession(proxy=PROXY_URL)
    logger.info(f"Использую прокси: {PROXY_URL}")

    # 2. Бот и диспетчер (с FSM-хранилищем)
    bot = Bot(token=settings.bot_token, session=session)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 3. Middleware для логирования — ко всем событиям
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # 4. Middleware для сессии БД — ко всем событиям
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # 5. Роутеры
    dp.include_router(common_router)
    dp.include_router(client_router)

    # Админский — с проверкой прав
    admin_router.message.middleware(AdminCheckMiddleware())
    admin_router.callback_query.middleware(AdminCheckMiddleware())
    dp.include_router(admin_router)

    logger.info(f"Администраторы: {settings.admins}")
    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
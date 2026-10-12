"""
Асинхронный движок SQLAlchemy и фабрика сессий.

Движок — это «подключение» к базе. Сессия — единица работы:
открыли, сделали запросы, сохранили, закрыли.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.db.base import Base


logger = logging.getLogger(__name__)


# Путь к БД из настроек. Для SQLite нужен префикс "sqlite+aiosqlite:///".
# settings.db_path = "data/bot.db", значит URL = "sqlite+aiosqlite:///data/bot.db"
DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_path}"


# Движок. echo=False — не выводить SQL в консоль.
# Если понадобится отладка — поставь echo=True.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)


# Фабрика сессий. expire_on_commit=False — после commit объекты
# остаются доступными (не «просрочиваются»).
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Создаёт таблицы, если их ещё нет.

    Вызывается один раз при старте бота.
    На Этапе 6 заменим на Alembic-миграции.
    """
    logger.info(f"Инициализация БД: {DATABASE_URL}")

    # Создаём папку для БД, если её нет
    from pathlib import Path
    db_file = Path(settings.db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        # run_sync выполняет синхронную функцию create_all в асинхронном контексте
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Таблицы БД готовы.")
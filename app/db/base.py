"""
Базовый класс для всех моделей SQLAlchemy.

Все модели (Client, Period, Status) наследуются от этого Base.
Именно через Base.metadata SQLAlchemy знает, какие таблицы создавать.

AsyncAttrs добавляет удобный доступ к ленивым relationship-ам
в асинхронном режиме: await obj.awaitable_attrs.some_relation.
"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """
    Базовый класс. Наследники автоматически регистрируются
    в метаданных, по которым создаются таблицы.
    """
    pass
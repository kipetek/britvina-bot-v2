"""
Репозиторий (DAO) — функции для работы с БД.

Все запросы к базе — здесь. Хендлеры не работают с SQLAlchemy напрямую,
а вызывают эти функции. Так проще поддерживать и тестировать.
"""

import logging
from sqlalchemy import select, func, or_
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Client, Period, Status


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Clients
# ─────────────────────────────────────────────────────────────

async def get_client(session: AsyncSession, client_id: int) -> Optional[Client]:
    """Найти клиента по Telegram ID."""
    result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    return result.scalar_one_or_none()


async def create_client(
    session: AsyncSession,
    client_id: int,
    full_name: Optional[str] = None,
) -> Client:
    """Создать нового клиента."""
    client = Client(id=client_id, full_name=full_name)
    session.add(client)
    await session.flush()  # чтобы получить client.id
    return client


async def update_client(
    session: AsyncSession,
    client: Client,
    company_name: Optional[str] = None,
    person_name: Optional[str] = None,
) -> Client:
    """Обновить данные клиента (компания/ФИО)."""
    if company_name is not None:
        client.company_name = company_name
    if person_name is not None:
        client.person_name = person_name
    await session.flush()
    return client


# ─────────────────────────────────────────────────────────────
# Periods
# ─────────────────────────────────────────────────────────────

async def get_active_period(session: AsyncSession) -> Optional[Period]:
    """Найти активный (не закрытый) период."""
    result = await session.execute(
        select(Period).where(Period.closed_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_period(
    session: AsyncSession,
    year: int,
    month: int,
) -> Period:
    """Создать новый период."""
    period = Period(year=year, month=month)
    session.add(period)
    await session.flush()
    return period


async def close_period(session: AsyncSession, period: Period) -> None:
    """Закрыть период (поставить closed_at = сейчас)."""
    period.closed_at = datetime.now(timezone.utc)
    await session.flush()


# ─────────────────────────────────────────────────────────────
# Statuses
# ─────────────────────────────────────────────────────────────

async def get_status(
    session: AsyncSession,
    client_id: int,
    period_id: int,
) -> Optional[Status]:
    """Найти статус клиента за период."""
    result = await session.execute(
        select(Status).where(
            Status.client_id == client_id,
            Status.period_id == period_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_status(
    session: AsyncSession,
    client_id: int,
    period_id: int,
) -> Status:
    """Найти статус или создать, если его нет."""
    status = await get_status(session, client_id, period_id)
    if status is None:
        status = Status(
            client_id=client_id,
            period_id=period_id,
            file_sent="NO",
            paid="NO",
        )
        session.add(status)
        await session.flush()
    return status


async def mark_file_sent(session: AsyncSession, status: Status) -> None:
    """Отметить, что выписка отправлена."""
    status.file_sent = "YES"
    status.file_sent_at = datetime.now(timezone.utc)
    await session.flush()


async def mark_paid(session: AsyncSession, status: Status) -> None:
    """Отметить, что счёт оплачен."""
    status.paid = "YES"
    status.paid_at = datetime.now(timezone.utc)
    await session.flush()


# ─────────────────────────────────────────────────────────────
# Админские выборки
# ─────────────────────────────────────────────────────────────

async def get_all_clients(session: AsyncSession) -> list[Client]:
    """Все клиенты."""
    result = await session.execute(select(Client).order_by(Client.id))
    return list(result.scalars().all())


async def get_debtors(session: AsyncSession, period_id: int) -> list[tuple[Client, Status]]:
    """
    Клиенты, которые ещё не выполнили всё за период.
    Возвращает пары (Client, Status).

    Учитываем NULL как «не сделано» — на случай старых записей в БД.
    Админов исключаем.
    """
    from app.config import settings

    result = await session.execute(
        select(Client, Status)
        .join(Status, Status.client_id == Client.id)
        .where(
            Status.period_id == period_id,
            Client.id.notin_(settings.admins),
            or_(
                Status.file_sent.is_(None),
                Status.file_sent != "YES",
                Status.paid.is_(None),
                Status.paid != "YES",
            ),
        )
    )
    return list(result.all())

async def ensure_active_period(session: AsyncSession) -> Period:
    """
    Возвращает активный период. Если его нет — создаёт
    на основе текущей даты (год/месяц) и возвращает.
    """
    period = await get_active_period(session)
    if period is not None:
        return period

    now = datetime.now()
    period = await create_period(session, year=now.year, month=now.month)
    logger.info(f"Создан активный период: {period}")
    return period

# ─────────────────────────────────────────────────────────────
# Админские выборки (расширение)
# ─────────────────────────────────────────────────────────────

async def get_clients_page(
    session: AsyncSession,
    offset: int,
    limit: int,
) -> tuple[list[Client], int]:
    """
    Возвращает страницу клиентов и общее количество.

    offset — сколько пропустить, limit — сколько взять.
    """
    total_result = await session.execute(select(func.count(Client.id)))
    total = total_result.scalar_one()

    result = await session.execute(
        select(Client).order_by(Client.id).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


async def delete_client(session: AsyncSession, client_id: int) -> bool:
    """
    Удаляет клиента по ID. Возвращает True, если клиент был найден.
    """
    client = await get_client(session, client_id)
    if client is None:
        return False
    await session.delete(client)
    await session.flush()
    return True


async def get_period_stats(
    session: AsyncSession,
    period_id: int,
) -> dict:
    """
    Собирает статистику по периоду.

    Клиенты без записи в statuses считаются «ничего не сделали»
    и автоматически попадают в «ждём» и «должники».
    """
    from app.config import settings

    # Всего клиентов (не админов)
    total_result = await session.execute(
        select(func.count(Client.id)).where(Client.id.notin_(settings.admins))
    )
    total = total_result.scalar_one()

    # Статусы за период (без админов)
    stmt = (
        select(Status)
        .join(Client, Client.id == Status.client_id)
        .where(
            Status.period_id == period_id,
            Client.id.notin_(settings.admins),
        )
    )
    result = await session.execute(stmt)
    statuses = list(result.scalars().all())

    # Клиенты без статуса — автоматически «ничего не сделали»
    clients_without_status = total - len(statuses)

    done = sum(
        1 for s in statuses
        if s.file_sent == "YES" and s.paid == "YES"
    )
    waiting_file = sum(
        1 for s in statuses if s.file_sent != "YES"
    ) + clients_without_status
    waiting_paid = sum(
        1 for s in statuses if s.paid != "YES"
    ) + clients_without_status

    # Должники = все, кто не done
    debtors = total - done

    return {
        "total": total,
        "done": done,
        "waiting_file": waiting_file,
        "waiting_paid": waiting_paid,
        "debtors": debtors,
    }

# ─────────────────────────────────────────────────────────────
# Периоды — расширение
# ─────────────────────────────────────────────────────────────

async def get_all_periods(session: AsyncSession) -> list[Period]:
    """Все периоды, новые сверху."""
    result = await session.execute(
        select(Period).order_by(Period.year.desc(), Period.month.desc())
    )
    return list(result.scalars().all())


async def get_statuses_for_period(
    session: AsyncSession,
    period_id: int,
) -> list[Status]:
    """Все статусы за период."""
    result = await session.execute(
        select(Status).where(Status.period_id == period_id)
    )
    return list(result.scalars().all())


async def get_client_history(
    session: AsyncSession,
    client_id: int,
) -> list[tuple[Period, Status | None]]:
    """
    История клиента: для каждого периода — его статус
    (или None, если клиент в этом периоде не участвовал).
    """
    periods = await get_all_periods(session)
    result = []
    for period in periods:
        status = await get_status(session, client_id, period.id)
        result.append((period, status))
    return result

async def get_clients_for_notification(session: AsyncSession) -> list[Client]:
    """
    Все клиенты, кроме админов — для рассылки уведомлений.
    """
    from app.config import settings
    result = await session.execute(
        select(Client).where(Client.id.notin_(settings.admins))
    )
    return list(result.scalars().all())

async def get_debtors_with_statuses(
    session: AsyncSession,
    period_id: int,
) -> list[tuple[Client, Status]]:
    """
    Все клиенты (кроме админов), у которых не всё сделано за период.
    Возвращает пары (Client, Status).

    Если у клиента вообще нет записи в statuses — тоже считаем должником,
    но Status будет None. Обрабатываем это в вызывающем коде.
    """
    from app.config import settings

    # Сначала берём всех клиентов, кроме админов
    clients_result = await session.execute(
        select(Client).where(Client.id.notin_(settings.admins))
    )
    clients = list(clients_result.scalars().all())

    # Затем для каждого — его статус за период
    result = []
    for client in clients:
        status = await get_status(session, client.id, period_id)
        # Если статуса нет — считаем, что должник (ничего не сделал)
        if status is None:
            result.append((client, None))
        elif status.file_sent != "YES" or status.paid != "YES":
            result.append((client, status))

    return result
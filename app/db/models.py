"""
Модели таблиц.

Три сущности:
• Client — клиент (ООО/ИП или физлицо)
• Period — расчётный период (месяц)
• Status — статус клиента за период (выписка + оплата)

Такая структура позволяет хранить историю по месяцам.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    """
    Клиент бота.

    id — это Telegram ID пользователя (совпадает с message.from_user.id).
    Не autoincrement, потому что Telegram ID уже уникален.
    """
    __tablename__ = "clients"

    # Telegram ID — первичный ключ, autoincrement НЕ нужен
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)

    # Имя из Telegram (на случай, если ФИО не указано)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Название компании (для ООО/ИП)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ФИО (для физлиц)
    person_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Служебные поля
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Связи
    statuses: Mapped[list["Status"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )

    def display_name(self) -> str:
        """
        Как показывать клиента админу.
        Приоритет: company_name → person_name → full_name → ID.
        """
        return (
            self.company_name
            or self.person_name
            or self.full_name
            or f"ID {self.id}"
        )

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.display_name()}>"


class Period(Base):
    """
    Расчётный период (месяц).

    Один период = один месяц. Активный период — тот, у которого
    closed_at = NULL. Когда админ сбрасывает статусы, мы закрываем
    текущий период и создаём новый.
    """
    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Связи
    statuses: Mapped[list["Status"]] = relationship(
        back_populates="period",
        cascade="all, delete-orphan",
    )

    # Один год+месяц должен быть уникален
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_period_year_month"),
    )

    def __repr__(self) -> str:
        return f"<Period {self.year}-{self.month:02d}>"


class Status(Base):
    """
    Статус клиента за период.

    Хранит: отправлена ли выписка и оплачен ли счёт.
    Одна запись = один клиент в одном периоде.
    """
    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("periods.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "YES" или "NO". NOT NULL + дефолт "NO" — чтобы не было NULL в БД.
    file_sent: Mapped[str] = mapped_column(
        String(10), nullable=False, default="NO", server_default="NO"
    )
    paid: Mapped[str] = mapped_column(
        String(10), nullable=False, default="NO", server_default="NO"
    )

    # Когда именно выполнил действие
    file_sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Связи
    client: Mapped["Client"] = relationship(back_populates="statuses")
    period: Mapped["Period"] = relationship(back_populates="statuses")

    # Один клиент + один период = одна запись
    __table_args__ = (
        UniqueConstraint("client_id", "period_id", name="uq_status_client_period"),
    )

    def __repr__(self) -> str:
        return f"<Status client={self.client_id} period={self.period_id}>"
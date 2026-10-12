"""
Обработчики для клиентов:
• /status — что от клиента ждут
• callback-и на inline-кнопки
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app import texts
from app.config import settings
from app.db.repository import (
    ensure_active_period,
    get_client,
    get_or_create_status,
    mark_file_sent,
    mark_paid,
)
from app.keyboards.client_kb import (
    CB_CHECK_STATUS,
    CB_FILE_SENT,
    CB_PAID,
    get_client_status_keyboard,
)


logger = logging.getLogger(__name__)

router = Router(name="client")


# ─────────────────────────────────────────────────────────────
# Вспомогательная функция — собрать текст статуса
# ─────────────────────────────────────────────────────────────

def _build_status_text(file_sent: bool, paid: bool) -> str:
    """
    Собирает текст со статусом клиента.

    Показывает, что уже сделано, а что нет, и что делать дальше.
    """
    lines = [texts.STATUS_HEADER]

    if file_sent:
        lines.append(texts.STATUS_FILE_SENT_OK)
    else:
        lines.append(texts.STATUS_FILE_SENT_WAIT)

    if paid:
        lines.append(texts.STATUS_PAID_OK)
    else:
        lines.append(texts.STATUS_PAID_WAIT)

    if file_sent and paid:
        lines.append(texts.STATUS_FOOTER_DONE)
    else:
        lines.append(texts.STATUS_FOOTER_WAIT)

    return "".join(lines)


async def _send_status(
    message: Message,
    session: AsyncSession,
) -> None:
    """
    Отправляет новое сообщение со статусом клиента.
    Используется из /status и /start.
    """
    user_id = message.from_user.id

    client = await get_client(session, user_id)
    if client is None:
        # На случай, если пользователь как-то попал сюда без /start
        await message.answer(texts.UNKNOWN_COMMAND)
        return

    period = await ensure_active_period(session)
    status = await get_or_create_status(session, user_id, period.id)
    await session.commit()

    file_sent = status.file_sent == "YES"
    paid = status.paid == "YES"

    text = _build_status_text(file_sent, paid)
    keyboard = get_client_status_keyboard(file_sent, paid)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _edit_status_message(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обновляет уже отправленное сообщение со статусом
    (после нажатия кнопки — чтобы не плодить новые сообщения).
    """
    user_id = callback.from_user.id

    period = await ensure_active_period(session)
    status = await get_or_create_status(session, user_id, period.id)
    await session.commit()

    file_sent = status.file_sent == "YES"
    paid = status.paid == "YES"

    text = _build_status_text(file_sent, paid)
    keyboard = get_client_status_keyboard(file_sent, paid)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        # Может случиться, если сообщение не изменилось (Telegram не любит).
        # Просто логируем — это не критично.
        logger.debug(f"Не удалось отредактировать сообщение: {e}")


# ─────────────────────────────────────────────────────────────
# /status
# ─────────────────────────────────────────────────────────────

@router.message(Command("status"))
async def cmd_status(message: Message, session: AsyncSession) -> None:
    """
    Показывает клиенту его статус за текущий период.
    """
    logger.info(f"/status от {message.from_user.id}")
    await _send_status(message, session)


# ─────────────────────────────────────────────────────────────
# Callback-и на кнопки
# ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == CB_FILE_SENT)
async def cb_file_sent(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Клиент нажал «📄 Отправил выписку».
    """
    user_id = callback.from_user.id
    logger.info(f"[CB] file_sent от {user_id}")

    period = await ensure_active_period(session)
    status = await get_or_create_status(session, user_id, period.id)

    if status.file_sent == "YES":
        # Уже отмечено — ничего не делаем
        await callback.answer(texts.CLIENT_ALREADY_DONE)
        return

    await mark_file_sent(session, status)
    await session.commit()

    # Уведомляем админов
    client = await get_client(session, user_id)
    display_name = client.display_name() if client else f"ID {user_id}"
    notification = texts.CLIENT_FILE_SENT_NOTIFICATION.format(
        display_name=display_name,
        user_id=user_id,
    )
    for admin_id in settings.admins:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=notification,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")

    await callback.answer(texts.CLIENT_FILE_SENT_ANSWER)
    await _edit_status_message(callback, session)


@router.callback_query(F.data == CB_PAID)
async def cb_paid(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Клиент нажал «💳 Оплатил».
    """
    user_id = callback.from_user.id
    logger.info(f"[CB] paid от {user_id}")

    period = await ensure_active_period(session)
    status = await get_or_create_status(session, user_id, period.id)

    if status.paid == "YES":
        await callback.answer(texts.CLIENT_ALREADY_DONE)
        return

    await mark_paid(session, status)
    await session.commit()

    client = await get_client(session, user_id)
    display_name = client.display_name() if client else f"ID {user_id}"
    notification = texts.CLIENT_PAID_NOTIFICATION.format(
        display_name=display_name,
        user_id=user_id,
    )
    for admin_id in settings.admins:
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=notification,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")

    await callback.answer(texts.CLIENT_PAID_ANSWER)
    await _edit_status_message(callback, session)


@router.callback_query(F.data == CB_CHECK_STATUS)
async def cb_check_status(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Клиент нажал «🔄 Обновить статус».
    """
    user_id = callback.from_user.id
    logger.info(f"[CB] check_status от {user_id}")

    await callback.answer("Обновляю...")
    await _edit_status_message(callback, session)
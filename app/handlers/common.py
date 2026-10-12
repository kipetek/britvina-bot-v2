"""
Общие команды, доступные всем пользователям:
/start, /help, /menu, /id, /version.
"""

import logging

from app.keyboards.admin_kb import get_new_client_keyboard

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import ReplyKeyboardRemove
from app.keyboards import get_admin_reply_keyboard
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__, texts
from app.config import settings
from app.db.repository import create_client, get_client


# Логгер для этого модуля
logger = logging.getLogger(__name__)

# Роутер — контейнер для обработчиков.
# В main.py мы его подключим к диспетчеру.
router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """
    Обработчик /start.

    • Новый клиент — создаём и уведомляем админов.
    • Админ — показываем reply-клавиатуру.
    • Обычный клиент — приветствие без клавиатуры.
    """
    user = message.from_user
    logger.info(f"/start от {user.id} ({user.full_name})")

    client = await get_client(session, user.id)

    # Админов в БД не создаём — они не клиенты
    if user.id in settings.admins:
        logger.info(f"Админ {user.id} вызвал /start")
        await message.answer(
            texts.START_MESSAGE,
            reply_markup=get_admin_reply_keyboard(),
            parse_mode="HTML",
        )
        return

    client = await get_client(session, user.id)

    if client is None:
        await create_client(session, user.id, full_name=user.full_name)
        await session.commit()
        logger.info(f"Создан новый клиент: {user.id} ({user.full_name})")

        notification = texts.NEW_CLIENT_NOTIFICATION.format(
            user_id=user.id,
            full_name=user.full_name,
        )
        keyboard = get_new_client_keyboard(user.id)
        for admin_id in settings.admins:
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=notification,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")

    # Админам — reply-клавиатура, клиентам — без неё
    if user.id in settings.admins:
        await message.answer(
            texts.START_MESSAGE,
            reply_markup=get_admin_reply_keyboard(),
            parse_mode="HTML",
        )
    else:
        # Убираем возможную старую reply-клавиатуру (если осталась)
        await message.answer(
            texts.START_MESSAGE,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Справка по командам. Для админов — расширенная."""
    user_id = message.from_user.id
    logger.info(f"/help от {user_id}")

    text = texts.HELP_MESSAGE
    if user_id in settings.admins:
        text += texts.HELP_ADMIN_EXTRA

    await message.answer(text, parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    """
    Показать меню.

    Админам — reply-клавиатуру с кнопками.
    Клиентам — inline-кнопки придут в /status.
    """
    user_id = message.from_user.id
    logger.info(f"/menu от {user_id}")

    if user_id in settings.admins:
        await message.answer(
            texts.MENU_MESSAGE,
            reply_markup=get_admin_reply_keyboard(),
        )
    else:
        await message.answer(texts.MENU_MESSAGE)


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    """
    Показать пользователю его Telegram ID.

    Зачем: админ должен знать ID клиента, чтобы привязать
    к нему компанию или ФИО командой /name.
    """
    user_id = message.from_user.id
    logger.info(f"/id от {user_id}")
    await message.answer(
        texts.ID_TEMPLATE.format(user_id=user_id),
        parse_mode="HTML",
    )


@router.message(Command("version"))
async def cmd_version(message: Message) -> None:
    """Показать версию бота. Полезно при отладке."""
    logger.info(f"/version от {message.from_user.id}")
    await message.answer(
        texts.VERSION_TEMPLATE.format(version=__version__),
        parse_mode="HTML",
    )
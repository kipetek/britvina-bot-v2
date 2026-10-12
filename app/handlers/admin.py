"""
Админские команды:
• /list — список клиентов с пагинацией
• /name — задать компанию или ФИО
• /delete — удалить клиента
• /stats — статистика
• /debtors — список должников
"""

import logging
import math

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app import texts
from app.config import settings
from app.db.repository import (
    delete_client,
    ensure_active_period,
    get_client,
    get_clients_page,
    get_debtors,
    get_period_stats,
    get_or_create_status,
    update_client,
    close_period,
    create_period,
    get_active_period,
    get_all_periods,
    get_client_history,
    get_statuses_for_period,
    get_clients_for_notification,
    get_debtors_with_statuses,
    get_clients_for_notification,
)
from app.keyboards.admin_kb import (
    CB_ADMIN_SET_NAME,
    CB_CANCEL,
    CB_SET_COMPANY,
    CB_SET_PERSON,
    get_name_type_keyboard,
    get_reset_confirm_keyboard,
    get_broadcast_confirm_keyboard,
)
from app.keyboards.admin_reply_kb import (
    BTN_DEBTORS,
    BTN_HELP,
    BTN_LIST,
    BTN_PERIODS,
    BTN_RESET,
    BTN_STATS,
    BTN_REMIND,
    BTN_BROADCAST,
)
from app.states import SetNameStates, BroadcastStates


logger = logging.getLogger(__name__)

router = Router(name="admin")


PAGE_SIZE = 10  # сколько клиентов показывать на странице


# ─────────────────────────────────────────────────────────────
# /list — список клиентов с пагинацией
# ─────────────────────────────────────────────────────────────

async def _render_list_page(
    session: AsyncSession,
    page: int,
) -> tuple[str, "InlineKeyboardMarkup | None"]:
    """
    Готовит текст и клавиатуру для страницы списка.

    Возвращает (текст, клавиатура_или_None).
    """
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from app.texts import CB_PAGE_PREFIX

    offset = (page - 1) * PAGE_SIZE
    clients, total = await get_clients_page(session, offset, PAGE_SIZE)

    if total == 0:
        return texts.ADMIN_LIST_EMPTY, None

    total_pages = math.ceil(total / PAGE_SIZE)

    text = texts.ADMIN_LIST_HEADER
    for client in clients:
        text += texts.ADMIN_LIST_ITEM.format(
            client_id=client.id,
            display_name=client.display_name(),
        )
    text += texts.ADMIN_PAGE_FOOTER.format(
        page=page, total_pages=total_pages,
    )

    # Клавиатура пагинации
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"{CB_PAGE_PREFIX}:{page - 1}")
    if page < total_pages:
        builder.button(text="Вперёд ➡️", callback_data=f"{CB_PAGE_PREFIX}:{page + 1}")

    # Если кнопок нет — вернём None
    kb = builder.as_markup() if (page > 1 or page < total_pages) else None

    return text, kb


@router.message(Command("list"))
async def cmd_list(message: Message, session: AsyncSession) -> None:
    """Показать первую страницу списка клиентов."""
    logger.info(f"/list от {message.from_user.id}")
    text, kb = await _render_list_page(session, page=1)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith(texts.CB_PAGE_PREFIX))
async def cb_page(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключение страниц списка."""
    page = int(callback.data.split(":")[1])
    text, kb = await _render_list_page(session, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Не удалось обновить сообщение: {e}")
    await callback.answer()


# ─────────────────────────────────────────────────────────────
# /name — задать компанию или ФИО
# ─────────────────────────────────────────────────────────────

@router.message(Command("name"))
async def cmd_name(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """
    Начало диалога /name <ID>.

    Проверяем клиента, сохраняем ID в FSM, показываем выбор типа.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(texts.ADMIN_NAME_USAGE, parse_mode="HTML")
        return

    client_id = int(args[1].strip())
    client = await get_client(session, client_id)

    if client is None:
        await message.answer(
            texts.ADMIN_NAME_CLIENT_NOT_FOUND.format(client_id=client_id),
            parse_mode="HTML",
        )
        return

    # Сохраняем ID в FSM, чтобы знать, кому задаём имя
    await state.update_data(client_id=client_id)
    await state.set_state(SetNameStates.choosing_type)

    await message.answer(
        texts.ADMIN_NAME_CHOOSE_TYPE.format(
            display_name=client.display_name(),
            client_id=client_id,
        ),
        reply_markup=get_name_type_keyboard(client_id),
        parse_mode="HTML",
    )

@router.callback_query(F.data.startswith(CB_ADMIN_SET_NAME))
async def cb_admin_set_name_from_notification(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """
    Админ нажал «Задать имя» в уведомлении о новом клиенте.

    Логика та же, что у /name <ID>, но ID берём из callback_data.
    """
    from app.keyboards.admin_kb import CB_ADMIN_SET_NAME

    client_id = int(callback.data.split(":")[1])
    client = await get_client(session, client_id)

    if client is None:
        await callback.answer(
            f"Клиент с ID {client_id} не найден в базе.",
            show_alert=True,
        )
        return

    # Сохраняем ID в FSM и показываем выбор типа
    await state.update_data(client_id=client_id)
    await state.set_state(SetNameStates.choosing_type)

    await callback.message.edit_text(
        texts.ADMIN_NAME_CHOOSE_TYPE.format(
            display_name=client.display_name(),
            client_id=client_id,
        ),
        reply_markup=get_name_type_keyboard(client_id),
        parse_mode="HTML",
    )
    await callback.answer()

@router.callback_query(
    StateFilter(SetNameStates.choosing_type),
    F.data.startswith(CB_SET_COMPANY),
)
async def cb_set_company(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Админ выбрал «Компания»."""
    client_id = int(callback.data.split(":")[1])
    client = await get_client(session, client_id)
    display = client.display_name() if client else f"ID {client_id}"

    await state.update_data(client_id=client_id, name_type="company")
    await state.set_state(SetNameStates.entering_text)

    await callback.message.edit_text(
        texts.ADMIN_NAME_ENTER_COMPANY.format(
            display_name=display,
            client_id=client_id,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(
    StateFilter(SetNameStates.choosing_type),
    F.data.startswith(CB_SET_PERSON),
)
async def cb_set_person(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Админ выбрал «ФИО»."""
    client_id = int(callback.data.split(":")[1])
    client = await get_client(session, client_id)
    display = client.display_name() if client else f"ID {client_id}"

    await state.update_data(client_id=client_id, name_type="person")
    await state.set_state(SetNameStates.entering_text)

    await callback.message.edit_text(
        texts.ADMIN_NAME_ENTER_PERSON.format(
            display_name=display,
            client_id=client_id,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == CB_CANCEL)
async def cb_cancel_name(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Админ нажал «Отмена»."""
    await state.clear()
    await callback.message.edit_text(texts.ADMIN_NAME_CANCELLED)
    await callback.answer()


@router.message(StateFilter(SetNameStates.entering_text), F.text, ~F.text.startswith("/"))
async def process_name_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """
    Админ ввёл текст — сохраняем его в нужное поле.
    """
    data = await state.get_data()
    client_id = data.get("client_id")
    name_type = data.get("name_type")
    text_value = message.text.strip()

    if not client_id or not name_type:
        # Что-то потерялось — просто выходим
        await state.clear()
        await message.answer("❌ Что-то пошло не так. Попробуйте снова /name")
        return

    client = await get_client(session, client_id)
    if client is None:
        await state.clear()
        await message.answer(
            texts.ADMIN_NAME_CLIENT_NOT_FOUND.format(client_id=client_id),
            parse_mode="HTML",
        )
        return

    if name_type == "company":
        await update_client(session, client, company_name=text_value)
        await session.commit()
        await message.answer(
            texts.ADMIN_NAME_SAVED_COMPANY.format(
                client_id=client_id,
                company_name=text_value,
            ),
            parse_mode="HTML",
        )
    else:
        await update_client(session, client, person_name=text_value)
        await session.commit()
        await message.answer(
            texts.ADMIN_NAME_SAVED_PERSON.format(
                client_id=client_id,
                person_name=text_value,
            ),
            parse_mode="HTML",
        )

    await state.clear()


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
) -> None:
    """Отмена любого FSM-диалога."""
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer(texts.ADMIN_NAME_CANCELLED)


# ─────────────────────────────────────────────────────────────
# /delete — удалить клиента
# ─────────────────────────────────────────────────────────────

@router.message(Command("delete"))
async def cmd_delete(message: Message, session: AsyncSession) -> None:
    """Удалить клиента по ID."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(texts.ADMIN_DELETE_USAGE, parse_mode="HTML")
        return

    client_id = int(args[1].strip())
    client = await get_client(session, client_id)

    if client is None:
        await message.answer(
            texts.ADMIN_DELETE_NOT_FOUND.format(client_id=client_id),
            parse_mode="HTML",
        )
        return

    display = client.display_name()
    await delete_client(session, client_id)
    await session.commit()

    await message.answer(
        texts.ADMIN_DELETE_DONE.format(
            display_name=display,
            client_id=client_id,
        ),
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────────────────────
# /stats — статистика
# ─────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Показать статистику по текущему периоду."""
    period = await ensure_active_period(session)
    await session.commit()

    stats = await get_period_stats(session, period.id)

    await message.answer(
        texts.ADMIN_STATS_TEMPLATE.format(
            period=f"{period.year}-{period.month:02d}",
            total=stats["total"],
            done=stats["done"],
            waiting_file=stats["waiting_file"],
            waiting_paid=stats["waiting_paid"],
            debtors=stats["debtors"],
        ),
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────────────────────
# /debtors — список должников
# ─────────────────────────────────────────────────────────────

@router.message(Command("debtors"))
async def cmd_debtors(message: Message, session: AsyncSession) -> None:
    """Показать клиентов, которые ещё не всё сделали."""
    period = await ensure_active_period(session)
    await session.commit()

    rows = await get_debtors(session, period.id)

    if not rows:
        await message.answer(texts.ADMIN_DEBTORS_EMPTY, parse_mode="HTML")
        return

    text = texts.ADMIN_DEBTORS_HEADER
    for client, status in rows:
        needs = []
        if status.file_sent != "YES":
            needs.append(texts.DEBTOR_NEEDS_FILE)
        if status.paid != "YES":
            needs.append(texts.DEBTOR_NEEDS_PAID)
        needs_str = (
            texts.DEBTOR_NEEDS_BOTH
            if len(needs) == 2
            else needs[0]
        )
        text += texts.ADMIN_DEBTORS_ITEM.format(
            display_name=client.display_name(),
            client_id=client.id,
            needs=needs_str,
        )

    await message.answer(text, parse_mode="HTML")

# ─────────────────────────────────────────────────────────────
# /reset_status — начать новый период
# ─────────────────────────────────────────────────────────────

@router.message(Command("reset_status"))
async def cmd_reset_status(message: Message, session: AsyncSession) -> None:
    """
    Начать новый период.

    Показываем подтверждение с кнопками, потому что операция
    необратимая и затрагивает всех клиентов.
    """
    period = await get_active_period(session)
    if period is None:
        await message.answer(texts.ADMIN_NO_ACTIVE_PERIOD)
        return

    # Вычисляем следующий месяц
    if period.month == 12:
        next_year, next_month = period.year + 1, 1
    else:
        next_year, next_month = period.year, period.month + 1

    await message.answer(
        texts.ADMIN_RESET_CONFIRM.format(
            next_period=f"{next_year}-{next_month:02d}",
        ),
        reply_markup=get_reset_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == texts.CB_RESET_CONFIRM)
async def cb_reset_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Админ подтвердил сброс. Закрываем период, создаём новый,
    рассылаем уведомления.
    """
    period = await get_active_period(session)
    if period is None:
        await callback.answer("Нет активного периода.", show_alert=True)
        return

    old_label = f"{period.year}-{period.month:02d}"

    # Вычисляем следующий месяц
    if period.month == 12:
        next_year, next_month = period.year + 1, 1
    else:
        next_year, next_month = period.year, period.month + 1
    next_label = f"{next_year}-{next_month:02d}"

    # Закрываем старый, создаём новый
    await close_period(session, period)
    await create_period(session, year=next_year, month=next_month)
    await session.commit()

    logger.info(f"Период {old_label} закрыт, открыт {next_label}")

    # Рассылаем уведомления клиентам
    clients = await get_clients_for_notification(session)
    notified = 0
    errors = 0

    for client in clients:
        try:
            await callback.bot.send_message(
                chat_id=client.id,
                text=texts.CLIENT_NEW_PERIOD_NOTIFICATION,
                parse_mode="HTML",
            )
            notified += 1
        except Exception as e:
            errors += 1
            logger.error(f"Не удалось уведомить клиента {client.id}: {e}")

    await callback.message.edit_text(
        texts.ADMIN_RESET_DONE.format(
            old_period=old_label,
            new_period=next_label,
            notified=notified,
            errors=errors,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == texts.CB_RESET_CANCEL)
async def cb_reset_cancel(callback: CallbackQuery) -> None:
    """Админ отменил сброс."""
    await callback.message.edit_text(texts.ADMIN_RESET_CANCELLED)
    await callback.answer()


# ─────────────────────────────────────────────────────────────
# /periods — список всех периодов
# ─────────────────────────────────────────────────────────────

@router.message(Command("periods"))
async def cmd_periods(message: Message, session: AsyncSession) -> None:
    """Показать все периоды с краткой статистикой."""
    periods = await get_all_periods(session)

    if not periods:
        await message.answer(texts.ADMIN_PERIODS_EMPTY, parse_mode="HTML")
        return

    text = texts.ADMIN_PERIODS_HEADER
    for period in periods:
        statuses = await get_statuses_for_period(session, period.id)
        done = sum(
            1 for s in statuses
            if s.file_sent == "YES" and s.paid == "YES"
        )

        started = period.started_at.strftime("%d.%m.%Y")
        if period.closed_at is None:
            status_line = texts.ADMIN_PERIODS_ACTIVE
        else:
            status_line = texts.ADMIN_PERIODS_CLOSED.format(
                closed=period.closed_at.strftime("%d.%m.%Y")
            )

        text += texts.ADMIN_PERIODS_ITEM.format(
            period=f"{period.year}-{period.month:02d}",
            started=started,
            status_line=status_line,
            total=len(statuses),
            done=done,
        )

    await message.answer(text, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────
# /history <ID> — история клиента по периодам
# ─────────────────────────────────────────────────────────────

@router.message(Command("history"))
async def cmd_history(message: Message, session: AsyncSession) -> None:
    """Показать историю клиента по всем периодам."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer(
            "✏️ Использование: <code>/history &lt;ID&gt;</code>",
            parse_mode="HTML",
        )
        return

    client_id = int(args[1].strip())
    client = await get_client(session, client_id)

    if client is None:
        await message.answer(
            texts.ADMIN_NAME_CLIENT_NOT_FOUND.format(client_id=client_id),
            parse_mode="HTML",
        )
        return

    history = await get_client_history(session, client_id)

    # Фильтруем периоды, где клиент не участвовал
    history = [(p, s) for p, s in history if s is not None]

    if not history:
        await message.answer(
            texts.ADMIN_HISTORY_HEADER.format(
                display_name=client.display_name(),
                client_id=client_id,
            ) + texts.ADMIN_HISTORY_EMPTY,
            parse_mode="HTML",
        )
        return

    text = texts.ADMIN_HISTORY_HEADER.format(
        display_name=client.display_name(),
        client_id=client_id,
    )

    for period, status in history:
        if status.file_sent == "YES":
            file_str = texts.HISTORY_YES.format(
                when=status.file_sent_at.strftime("%d.%m.%Y")
                if status.file_sent_at else ""
            )
        else:
            file_str = texts.HISTORY_NO

        if status.paid == "YES":
            paid_str = texts.HISTORY_YES.format(
                when=status.paid_at.strftime("%d.%m.%Y")
                if status.paid_at else ""
            )
        else:
            paid_str = texts.HISTORY_NO

        text += texts.ADMIN_HISTORY_ITEM.format(
            period=f"{period.year}-{period.month:02d}",
            file_sent=file_str,
            paid=paid_str,
        )

    await message.answer(text, parse_mode="HTML")

# ─────────────────────────────────────────────────────────────
# Обработчики reply-кнопок (дублируют команды)
# ─────────────────────────────────────────────────────────────

@router.message(F.text == BTN_LIST)
async def btn_list(message: Message, session: AsyncSession) -> None:
    """Кнопка «📋 Список клиентов» → то же, что /list."""
    await cmd_list(message, session)


@router.message(F.text == BTN_DEBTORS)
async def btn_debtors(message: Message, session: AsyncSession) -> None:
    """Кнопка «👥 Должники» → то же, что /debtors."""
    await cmd_debtors(message, session)


@router.message(F.text == BTN_STATS)
async def btn_stats(message: Message, session: AsyncSession) -> None:
    """Кнопка «📊 Статистика» → то же, что /stats."""
    await cmd_stats(message, session)


@router.message(F.text == BTN_PERIODS)
async def btn_periods(message: Message, session: AsyncSession) -> None:
    """Кнопка «📅 Периоды» → то же, что /periods."""
    await cmd_periods(message, session)


@router.message(F.text == BTN_RESET)
async def btn_reset(message: Message, session: AsyncSession) -> None:
    """Кнопка «🔄 Сброс статусов» → то же, что /reset_status."""
    await cmd_reset_status(message, session)


@router.message(F.text == BTN_HELP)
async def btn_help(message: Message) -> None:
    """Кнопка «❓ Помощь» → то же, что /help, но с админским расширением."""
    text = texts.HELP_MESSAGE + texts.HELP_ADMIN_EXTRA
    await message.answer(text, parse_mode="HTML")

# ─────────────────────────────────────────────────────────────
# /remind — напомнить должникам
# ─────────────────────────────────────────────────────────────

async def _do_remind(message: Message, session: AsyncSession) -> None:
    """
    Общая логика для /remind и кнопки «📬 Напомнить».
    """
    period = await ensure_active_period(session)
    await session.commit()

    debtors = await get_debtors_with_statuses(session, period.id)

    if not debtors:
        await message.answer(texts.REMIND_NO_DEBTORS)
        return

    sent = 0
    errors = 0

    for client, status in debtors:
        # Определяем, чего не хватает
        if status is None:
            # Нет статуса — ничего не сделал
            text = texts.REMIND_BOTH
        else:
            file_ok = status.file_sent == "YES"
            paid_ok = status.paid == "YES"
            if not file_ok and not paid_ok:
                text = texts.REMIND_BOTH
            elif not file_ok:
                text = texts.REMIND_FILE_ONLY
            elif not paid_ok:
                text = texts.REMIND_PAID_ONLY
            else:
                continue  # всё сделал — не напоминаем

        try:
            await message.bot.send_message(
                chat_id=client.id,
                text=text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            errors += 1
            logger.error(f"Не удалось напомнить клиенту {client.id}: {e}")

    await message.answer(
        texts.REMIND_RESULT.format(
            total=len(debtors),
            debtors=len(debtors),
            sent=sent,
            errors=errors,
        ),
        parse_mode="HTML",
    )


@router.message(Command("remind"))
async def cmd_remind(message: Message, session: AsyncSession) -> None:
    """Напомнить всем должникам."""
    logger.info(f"/remind от {message.from_user.id}")
    await _do_remind(message, session)


@router.message(F.text == BTN_REMIND)
async def btn_remind(message: Message, session: AsyncSession) -> None:
    """Кнопка «📬 Напомнить»."""
    logger.info(f"Кнопка Напомнить от {message.from_user.id}")
    await _do_remind(message, session)

# ─────────────────────────────────────────────────────────────
# /broadcast — написать всем клиентам
# ─────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    """Начать рассылку всем клиентам."""
    logger.info(f"/broadcast от {message.from_user.id}")
    await state.set_state(BroadcastStates.entering_text)
    await message.answer(texts.BROADCAST_ENTER_TEXT, parse_mode="HTML")


@router.message(F.text == BTN_BROADCAST)
async def btn_broadcast(message: Message, state: FSMContext) -> None:
    """Кнопка «📢 Написать всем»."""
    logger.info(f"Кнопка Написать всем от {message.from_user.id}")
    await state.set_state(BroadcastStates.entering_text)
    await message.answer(texts.BROADCAST_ENTER_TEXT, parse_mode="HTML")


@router.message(
    StateFilter(BroadcastStates.entering_text),
    F.text,
    ~F.text.startswith("/"),
)
async def process_broadcast_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Админ ввёл текст рассылки. Показываем превью и подтверждение.
    """
    text = message.text.strip()

    # Считаем получателей
    clients = await get_clients_for_notification(session)
    total = len(clients)

    if total == 0:
        await state.clear()
        await message.answer("📭 В базе нет клиентов — некого оповещать.")
        return

    # Сохраняем текст в FSM
    await state.update_data(broadcast_text=text)
    await state.set_state(BroadcastStates.confirming)

    await message.answer(
        texts.BROADCAST_PREVIEW.format(total=total, text=text),
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == texts.CB_BROADCAST_CONFIRM)
async def cb_broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Админ подтвердил рассылку — отправляем."""
    data = await state.get_data()
    text = data.get("broadcast_text")

    if not text:
        await callback.answer("Что-то пошло не так.", show_alert=True)
        await state.clear()
        return

    clients = await get_clients_for_notification(session)

    sent = 0
    errors = 0

    for client in clients:
        try:
            await callback.bot.send_message(
                chat_id=client.id,
                text=text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            errors += 1
            logger.error(f"Не удалось отправить клиенту {client.id}: {e}")

    await state.clear()

    await callback.message.edit_text(
        texts.BROADCAST_RESULT.format(sent=sent, errors=errors),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == texts.CB_BROADCAST_CANCEL)
async def cb_broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Админ отменил рассылку."""
    await state.clear()
    await callback.message.edit_text(texts.BROADCAST_CANCELLED)
    await callback.answer()


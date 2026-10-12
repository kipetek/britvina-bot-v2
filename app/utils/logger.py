"""
Настройка логирования.
Логи пишутся и в консоль, и в файл logs/bot.log (с ротацией).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings, BASE_DIR


def setup_logger() -> logging.Logger:
    """
    Настраивает корневой логгер.
    Вызывается один раз при запуске бота.
    """
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)  # создаём папку logs, если её нет

    log_file = log_dir / "bot.log"

    # Формат сообщений: время - имя логгера - уровень - текст
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 1. Вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 2. Вывод в файл с ротацией:
    #    максимум 5 МБ на файл, храним 3 старых копии
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()          # убираем старые обработчики, если были
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    return logging.getLogger(__name__)
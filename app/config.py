"""
Конфигурация бота.
Читает переменные из файла .env и делает их доступными в коде.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Корень проекта — папка, где лежит .env
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Класс настроек. Pydantic автоматически прочитает .env
    и подставит значения в поля ниже.
    """

    bot_token: str                    # токен бота (обязательное поле)
    admin_ids: str                    # ID админов через запятую (строка)
    log_level: str = "INFO"           # уровень логов, по умолчанию INFO
    db_path: str = "data/bot.db"      # путь к базе данных
    proxy_url: str = ""  # ← НОВОЕ. Пусто = без прокси.

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",   # откуда читать
        env_file_encoding="utf-8",
        extra="ignore",               # игнорировать лишние переменные в .env
    )

    @property
    def admins(self) -> list[int]:
        """
        Превращает строку "123,456" в список чисел [123, 456].
        Удобно использовать в коде: settings.admins
        """
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


# Единственный экземпляр настроек на весь проект.
# Импортируй его в других файлах: from app.config import settings
settings = Settings()
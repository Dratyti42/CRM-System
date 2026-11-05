"""Управление подключением к базе данных и фабрика сессий."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..configs.settings import settings

# Создаем движок SQLAlchemy для работы с PostgreSQL через драйвер psycopg
engine = create_engine(
    settings.database_url,
    echo=False,  # Поставьте True, если захотите видеть сырые SQL-запросы в консоли
    pool_pre_ping=True,  # Проверяет живое ли соединение перед отправкой запроса
)

# Фабрика сессий для создания транзакций
SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session() -> Generator[Session, None, None]:
    """Генератор контекста сессии БД."""
    with SessionFactory() as session:
        yield session

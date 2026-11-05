import os

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://crm_user:crm_password@localhost:5432/crm_db"
)


class Settings:
    """Настройки приложения, читаемые из переменных окружения."""

    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


settings = Settings()

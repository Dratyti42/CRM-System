"""Настройки приложения на базе Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Параметры конфигурации CRM-системы из переменных окружения."""

    database_url: str = (
        "postgresql+psycopg://crm_user:crm_password@localhost:5432/crm_db"
    )
    classifier_strategy: str = "keyword"
    confidence_threshold: float = 0.6
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_title: str = "CRM-система с интеллектуальной приоритизацией"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

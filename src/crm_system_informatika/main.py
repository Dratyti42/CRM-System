"""Точка входа приложения: инициализация зависимостей с подключением к PostgreSQL."""

from .classifier import KeywordAIAgent
from .cli import ConsoleUI
from .database.session import SessionFactory
from .repository import SQLAlchemyTicketRepository
from .service import CRMService


def main() -> None:
    """Точка входа: сборка зависимостей и запуск приложения."""
    # Используем репозиторий базы данных PostgreSQL
    repo = SQLAlchemyTicketRepository(session_factory=SessionFactory)
    ai_agent = KeywordAIAgent()
    crm_service = CRMService(repo=repo, classifier=ai_agent)

    app = ConsoleUI(service=crm_service)
    app.run()


if __name__ == "__main__":
    main()

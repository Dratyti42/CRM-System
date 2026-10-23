from .classifier import KeywordAIAgent
from .cli import ConsoleUI
from .repository import TicketRepository
from .service import CRMService


def main() -> None:
    """Точка входа: сборка зависимостей и запуск приложения."""
    repo = TicketRepository()
    ai_agent = KeywordAIAgent()
    crm_service = CRMService(repo=repo, classifier=ai_agent)

    app = ConsoleUI(service=crm_service)
    app.run()


if __name__ == "__main__":
    main()
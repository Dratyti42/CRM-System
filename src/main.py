from src.classifier import KeywordAIAgent
from src.cli import ConsoleUI
from src.repository import TicketRepository
from src.service import CRMService


def main():
    repo = TicketRepository()
    ai_agent = KeywordAIAgent()
    crm_service = CRMService(repo=repo, classifier=ai_agent)

    app = ConsoleUI(service=crm_service)
    app.run()


if __name__ == "__main__":
    main()
from typing import List, Optional
from src.classifier import BasePriorityClassifier
from src.models import Priority, Status, Ticket
from src.repository import TicketRepository


class CRMService:
    def __init__(self, repo: TicketRepository, classifier: BasePriorityClassifier):
        self.repo = repo
        self.classifier = classifier

    def create_ticket(self, title: str, description: str, client_name: str) -> Ticket:
        # Вызов ИИ для определения приоритета
        priority, confidence = self.classifier.predict(title, description)

        return self.repo.add(
            {
                "title": title,
                "description": description,
                "client_name": client_name,
                "priority": priority,
                "confidence_score": confidence,
            }
        )

    def get_tickets_for_operator(self) -> List[Ticket]:
        # Сортировка по критичности
        order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        return sorted(self.repo.get_all(), key=lambda t: order[t.priority])

    def take_ticket_to_work(self, ticket_id: int, operator_name: str) -> Optional[Ticket]:
        ticket = self.repo.get_by_id(ticket_id)
        if ticket:
            ticket.status = Status.IN_PROGRESS
            ticket.operator_name = operator_name
        return ticket

    def override_priority(self, ticket_id: int, new_priority: Priority) -> Optional[Ticket]:
        ticket = self.repo.get_by_id(ticket_id)
        if ticket:
            ticket.priority = new_priority
            ticket.manual_priority_override = True
        return ticket

    def change_status(self, ticket_id: int, new_status: Status) -> Optional[Ticket]:
        ticket = self.repo.get_by_id(ticket_id)
        if ticket:
            ticket.status = new_status
        return ticket
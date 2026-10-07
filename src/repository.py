from typing import List, Optional
from src.models import Ticket


class TicketRepository:
    def __init__(self):
        self._tickets: List[Ticket] = []
        self._counter: int = 1

    def add(self, ticket_data: dict) -> Ticket:
        ticket = Ticket(id=self._counter, **ticket_data)
        self._tickets.append(ticket)
        self._counter += 1
        return ticket

    def get_all(self) -> List[Ticket]:
        return list(self._tickets)

    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        for ticket in self._tickets:
            if ticket.id == ticket_id:
                return ticket
        return None
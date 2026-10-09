from abc import ABC, abstractmethod

from src.models import Ticket


class BaseTicketRepository(ABC):
    """Абстрактный репозиторий для работы с хранилищем заявок."""

    @abstractmethod
    def add(self, ticket_data: dict) -> Ticket:
        """Сохранить новую заявку в хранилище."""

    @abstractmethod
    def get_all(self) -> list[Ticket]:
        """Получить полный перечень заявок."""

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по первичному ключу."""


class TicketRepository(BaseTicketRepository):
    """In-memory реализация репозитория заявок."""

    def __init__(self) -> None:
        """Инициализировать локальное хранилище и счетчик идентификаторов."""
        self._tickets: list[Ticket] = []
        self._counter: int = 1

    def add(self, ticket_data: dict) -> Ticket:
        """Добавить заявку в локальный список."""
        ticket = Ticket(id=self._counter, **ticket_data)
        self._tickets.append(ticket)
        self._counter += 1
        return ticket

    def get_all(self) -> list[Ticket]:
        """Вернуть копию списка всех сохраненных заявок."""
        return list(self._tickets)

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по ID в текущем списке."""
        for ticket in self._tickets:
            if ticket.id == ticket_id:
                return ticket
        return None

from abc import ABC, abstractmethod
from dataclasses import asdict

from .models import Ticket, TicketDraft


class BaseTicketRepository(ABC):
    """Абстрактный репозиторий для управления хранилищем заявок."""

    @abstractmethod
    def add(self, draft: TicketDraft) -> Ticket:
        """Сохранить новую заявку из черновика."""

    @abstractmethod
    def get_all(self) -> list[Ticket]:
        """Получить полный перечень заявок."""

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Найти заявку по первичному ключу."""

    @abstractmethod
    def update(self, ticket: Ticket) -> Ticket:
        """Явно сохранить обновленное состояние сущности в хранилище."""


class TicketRepository(BaseTicketRepository):
    """In-memory реализация репозитория заявок."""

    def __init__(self) -> None:
        """Инициализировать локальное хранилище и счетчик идентификаторов."""
        self._tickets: list[Ticket] = []
        self._counter: int = 1

    def add(self, draft: TicketDraft) -> Ticket:
        """Добавить заявку в локальный список без риска дублирования аргументов."""
        ticket = Ticket(id=self._counter, **asdict(draft))
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

    def update(self, ticket: Ticket) -> Ticket:
        """Обновить существующую запись в списке."""
        for i, existing in enumerate(self._tickets):
            if existing.id == ticket.id:
                self._tickets[i] = ticket
                return ticket
        raise ValueError(f"Заявка с ID {ticket.id} не найдена в репозитории.")
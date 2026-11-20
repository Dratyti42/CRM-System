"""Слой прикладной бизнес-логики (Service Layer) управления заявками."""

import re

from .classifier import BasePriorityClassifier
from .database.uow import BaseUnitOfWork
from .exceptions import (
    DomainValidationError,
    InvalidStatusTransitionError,
    TicketNotFoundError,
)
from .models import Priority, Status, Ticket, TicketAuditLog, TicketDraft
from .observers import TicketEvent, TicketEventPublisher, TicketEventType

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

PRIORITY_WEIGHTS: dict[Priority, int] = {
    Priority.CRITICAL: 0,
    Priority.HIGH: 1,
    Priority.MEDIUM: 2,
    Priority.LOW: 3,
}

ALLOWED_STATUS_TRANSITIONS: dict[Status, set[Status]] = {
    Status.NEW: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.WAITING_CLIENT, Status.RESOLVED},
    Status.WAITING_CLIENT: {Status.IN_PROGRESS, Status.RESOLVED},
    Status.RESOLVED: {Status.CLOSED, Status.IN_PROGRESS},
    Status.CLOSED: set(),
}


class CRMService:
    """Сервис бизнес-логики, оркестрирующий Unit of Work, классификатор и события."""

    def __init__(
        self,
        uow: BaseUnitOfWork,
        classifier: BasePriorityClassifier,
        publisher: TicketEventPublisher | None = None,
    ) -> None:
        """Инициализировать сервис ссылками на абстракции."""
        self._uow = uow
        self._classifier = classifier
        self._publisher = publisher or TicketEventPublisher()

    def _validate_ticket(
        self,
        title: str,
        description: str,
        client_name: str,
        client_email: str,
    ) -> None:
        """Проверить обязательные поля новой заявки."""
        if not title.strip():
            raise DomainValidationError("Тема обращения не может быть пустой.")
        if not description.strip():
            raise DomainValidationError("Описание проблемы не может быть пустым.")
        if not client_name.strip():
            raise DomainValidationError("Имя клиента не может быть пустым.")
        if not EMAIL_REGEX.match(client_email.strip()):
            raise DomainValidationError("Указан некорректный формат email.")

    def get_allowed_transitions(self, status: Status) -> list[Status]:
        """Вернуть допустимые следующие статусы для указанного состояния."""
        return sorted(
            ALLOWED_STATUS_TRANSITIONS.get(status, set()),
            key=lambda s: list(Status).index(s),
        )

    def create_ticket(
        self,
        title: str,
        description: str,
        client_name: str,
        client_email: str,
    ) -> Ticket:
        """Создать заявку через валидацию, расчет приоритета ИИ и фиксацию в UoW."""
        self._validate_ticket(title, description, client_name, client_email)
        priority, confidence = self._classifier.predict(title, description)

        draft = TicketDraft(
            title=title.strip(),
            description=description.strip(),
            client_name=client_name.strip(),
            client_email=client_email.strip().lower(),
            priority=priority,
            confidence_score=confidence,
        )

        with self._uow:
            ticket = self._uow.tickets.add(draft)
            self._uow.commit()

        self._publisher.notify(
            TicketEvent(
                event_type=TicketEventType.CREATED,
                ticket=ticket,
                details=f"Создана клиентом {ticket.client_name}",
            )
        )
        return ticket

    def get_tickets_for_operator(
        self,
        priority: Priority | None = None,
        status: Status | None = None,
    ) -> list[Ticket]:
        """Получить заявки, отсортированные по уровню критичности."""
        with self._uow:
            tickets = self._uow.tickets.get_all(priority=priority, status=status)
        return sorted(tickets, key=lambda t: (PRIORITY_WEIGHTS[t.priority], t.id))

    def get_ticket_by_id(self, ticket_id: int) -> Ticket:
        """Получить заявку по идентификатору или выбросить TicketNotFoundError."""
        with self._uow:
            ticket = self._uow.tickets.get_by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)
        return ticket

    def get_ticket_audit_logs(self, ticket_id: int) -> list[TicketAuditLog]:
        """Получить историю ручных корректировок приоритета по заявке."""
        with self._uow:
            ticket = self._uow.tickets.get_by_id(ticket_id)
            if ticket is None:
                raise TicketNotFoundError(ticket_id)
            return self._uow.tickets.get_audit_logs(ticket_id)

    def take_ticket_to_work(
        self,
        ticket_id: int,
        operator_name: str,
        operator_email: str | None = None,
    ) -> Ticket:
        """Назначить оператора и перевести заявку в статус «В работе»."""
        if not operator_name.strip():
            raise DomainValidationError("Имя оператора не может быть пустым.")

        with self._uow:
            ticket = self._uow.tickets.get_by_id(ticket_id)
            if ticket is None:
                raise TicketNotFoundError(ticket_id)

            if Status.IN_PROGRESS not in ALLOWED_STATUS_TRANSITIONS.get(
                ticket.status, set()
            ):
                raise InvalidStatusTransitionError(
                    f"Невозможно взять в работу заявку в статусе '{ticket.status.value}'."
                )

            ticket.status = Status.IN_PROGRESS
            ticket.operator_name = operator_name.strip()
            updated = self._uow.tickets.update(ticket, operator_email=operator_email)
            self._uow.commit()

        self._publisher.notify(
            TicketEvent(
                event_type=TicketEventType.ASSIGNED,
                ticket=updated,
                details=f"Назначен оператор {updated.operator_name}",
            )
        )
        return updated

    def override_priority(
        self,
        ticket_id: int,
        new_priority: Priority,
        operator_name: str | None = None,
        reason: str | None = None,
    ) -> Ticket:
        """Вручную переопределить приоритет и атомарно записать событие в аудит-лог."""
        with self._uow:
            ticket = self._uow.tickets.get_by_id(ticket_id)
            if ticket is None:
                raise TicketNotFoundError(ticket_id)

            old_priority = ticket.priority
            actor_name = (
                operator_name.strip()
                if operator_name and operator_name.strip()
                else (ticket.operator_name or "Оператор поддержки")
            )
            audit_reason = (
                reason.strip()
                if reason and reason.strip()
                else "Ручная корректировка оператором"
            )

            ticket.priority = new_priority
            ticket.manual_priority_override = True
            updated = self._uow.tickets.update(ticket)

            if old_priority != new_priority:
                self._uow.tickets.add_audit_log(
                    ticket_id=updated.id,
                    actor_name=actor_name,
                    old_priority=old_priority,
                    new_priority=new_priority,
                    reason=audit_reason,
                )

            self._uow.commit()

        self._publisher.notify(
            TicketEvent(
                event_type=TicketEventType.PRIORITY_OVERRIDDEN,
                ticket=updated,
                details=(
                    f"Приоритет изменен: {old_priority.value} -> {new_priority.value}"
                ),
            )
        )
        return updated

    def change_status(self, ticket_id: int, new_status: Status) -> Ticket:
        """Обновить статус заявки с проверкой графа допустимых переходов."""
        with self._uow:
            ticket = self._uow.tickets.get_by_id(ticket_id)
            if ticket is None:
                raise TicketNotFoundError(ticket_id)

            allowed_transitions = ALLOWED_STATUS_TRANSITIONS.get(ticket.status, set())
            if new_status not in allowed_transitions:
                raise InvalidStatusTransitionError(
                    f"Недопустимый переход из статуса '{ticket.status.value}' "
                    f"в '{new_status.value}'."
                )

            old_status = ticket.status
            ticket.status = new_status
            updated = self._uow.tickets.update(ticket)
            self._uow.commit()

        self._publisher.notify(
            TicketEvent(
                event_type=TicketEventType.STATUS_CHANGED,
                ticket=updated,
                details=f"Статус изменен: {old_status.value} -> {new_status.value}",
            )
        )
        return updated


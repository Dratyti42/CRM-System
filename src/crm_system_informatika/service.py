from .classifier import BasePriorityClassifier
from .models import Priority, Status, Ticket, TicketDraft
from .repository import BaseTicketRepository

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
    """Сервис бизнес-логики управления заявками."""

    def __init__(
        self,
        repo: BaseTicketRepository,
        classifier: BasePriorityClassifier,
    ) -> None:
        """Инициализировать сервис через защищенные ссылки на абстракции."""
        self._repo = repo
        self._classifier = classifier

    def _validate_ticket(
        self, title: str, description: str, client_name: str
    ) -> None:
        """Проверить обязательные поля заявки на отсутствие пустых строк."""
        if not title.strip():
            raise ValueError("Тема обращения не может быть пустой.")
        if not description.strip():
            raise ValueError("Описание проблемы не может быть пустым.")
        if not client_name.strip():
            raise ValueError("Имя клиента не может быть пустым.")

    def create_ticket(self, title: str, description: str, client_name: str) -> Ticket:
        """Создать заявку через валидацию, расчет ИИ и сохранение черновика."""
        self._validate_ticket(title, description, client_name)
        priority, confidence = self._classifier.predict(title, description)

        draft = TicketDraft(
            title=title.strip(),
            description=description.strip(),
            client_name=client_name.strip(),
            priority=priority,
            confidence_score=confidence,
        )
        return self._repo.add(draft)

    def get_tickets_for_operator(self) -> list[Ticket]:
        """Получить заявки, отсортированные по уровню критичности."""
        return sorted(
            self._repo.get_all(), key=lambda t: PRIORITY_WEIGHTS[t.priority]
        )

    def take_ticket_to_work(self, ticket_id: int, operator_name: str) -> Ticket | None:
        """Назначить оператора и перевести заявку в работу через метод обновления."""
        ticket = self._repo.get_by_id(ticket_id)
        if ticket is None:
            return None

        if Status.IN_PROGRESS not in ALLOWED_STATUS_TRANSITIONS.get(
            ticket.status, set()
        ):
            raise ValueError(
                f"Невозможно взять в работу заявку в статусе '{ticket.status.value}'."
            )

        ticket.status = Status.IN_PROGRESS
        ticket.operator_name = operator_name.strip()
        return self._repo.update(ticket)

    def override_priority(
        self, ticket_id: int, new_priority: Priority
    ) -> Ticket | None:
        """Вручную изменить приоритет заявки и зафиксировать обновление в репозитории."""
        ticket = self._repo.get_by_id(ticket_id)
        if ticket is None:
            return None

        ticket.priority = new_priority
        ticket.manual_priority_override = True
        return self._repo.update(ticket)

    def change_status(self, ticket_id: int, new_status: Status) -> Ticket | None:
        """Обновить статус жизненного цикла с валидацией допустимых переходов."""
        ticket = self._repo.get_by_id(ticket_id)
        if ticket is None:
            return None

        allowed_transitions = ALLOWED_STATUS_TRANSITIONS.get(
            ticket.status, set()
        )
        if new_status not in allowed_transitions:
            raise ValueError(
                f"Недопустимый переход из статуса '{ticket.status.value}' в '{new_status.value}'."
            )

        ticket.status = new_status
        return self._repo.update(ticket)
"""Доменные исключения прикладной логики CRM."""


class CRMError(Exception):
    """Базовое исключение CRM-системы."""


class DomainValidationError(CRMError, ValueError):
    """Ошибка валидации входных данных предметной области."""


class TicketNotFoundError(CRMError):
    """Исключение при отсутствии заявки с указанным идентификатором."""

    def __init__(self, ticket_id: int) -> None:
        """Сформировать сообщение с идентификатором ненайденной заявки."""
        self.ticket_id = ticket_id
        super().__init__(f"Заявка #{ticket_id} не найдена.")


class InvalidStatusTransitionError(CRMError, ValueError):
    """Исключение при недопустимом переходе статуса заявки."""
